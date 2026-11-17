"""Web pages and a small JSON API. Business logic lives in service modules."""

import csv
import io
import json
import math
from datetime import date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import login_required
from .body_metrics import ACTIVITY_FACTORS, calculate
from .chat import answer_question
from .db import get_db
from .nutrition import CATALOGUE, FOODS, estimate_nutrition
from .recognition import FoodRecognizer, ModelUnavailable, validate_image
from .repository import get_meals, logging_streak, summarize, user_today, week_series

web = Blueprint("web", __name__)
MEAL_TYPES = ("Breakfast", "Lunch", "Dinner", "Snack")


def recognizer():
    if "recognizer" not in current_app.extensions:
        current_app.extensions["recognizer"] = FoodRecognizer(
            current_app.config["MODEL_PATH"], current_app.config["MODEL_LABELS_PATH"]
        )
    return current_app.extensions["recognizer"]


def parse_date(value):
    try:
        result = date.fromisoformat(value)
    except (ValueError, TypeError):
        abort(400, description="Use a valid date in YYYY-MM-DD format.")
    if result < date(1900, 1, 1) or result > user_today(g.user):
        abort(400, description="Log a date between 1900-01-01 and today.")
    return result


def diary_period():
    today = user_today(g.user)
    start = parse_date(request.args.get("start", str(today - timedelta(days=29))))
    end = parse_date(request.args.get("end", str(today)))
    if start > end:
        abort(400, description="The start date must come before the end date.")
    return start, end


@web.get("/")
@login_required
def dashboard():
    today = user_today(g.user)
    totals = summarize(g.user["id"], today, today)
    return render_template(
        "dashboard.html",
        active="dashboard",
        today=today,
        totals=totals,
        recent=get_meals(g.user["id"])[:4],
        series=week_series(g.user["id"], today),
        streak=logging_streak(g.user["id"], today),
        progress=min(round(totals["calories"] / g.user["calorie_goal"] * 100), 100),
    )


@web.get("/analyze")
@login_required
def analyze():
    return render_template(
        "analyze.html",
        active="analyze",
        foods=CATALOGUE,
        meal_types=MEAL_TYPES,
        today=user_today(g.user),
        model_present=recognizer().artifacts_present,
    )


@web.post("/api/predict")
@login_required
def predict():
    uploaded = request.files.get("image")
    if uploaded is None:
        abort(400, description="Please choose an image.")
    try:
        image = validate_image(uploaded.read())
        predictions = recognizer().predict(image)
    except ValueError as error:
        abort(400, description=str(error))
    except ModelUnavailable as error:
        abort(503, description=str(error))
    for prediction in predictions:
        prediction["supported"] = prediction["label"] in FOODS
    session["predicted_labels"] = [prediction["label"] for prediction in predictions]
    threshold = recognizer().confidence_threshold
    return jsonify(
        predictions=predictions,
        needs_confirmation=True,
        uncertain=not predictions or predictions[0]["confidence"] < threshold,
        confidence_threshold=threshold,
    )


@web.post("/meals")
@login_required
def add_meal():
    food_key = request.form.get("food_key", "")
    if food_key not in FOODS:
        abort(400, description="Select a food from the nutrition catalogue.")
    try:
        grams = float(request.form.get("grams", ""))
    except (TypeError, ValueError):
        abort(400, description="Enter the portion weight in grams.")
    if not math.isfinite(grams) or not 1 <= grams <= 5000:
        abort(400, description="Portion weight must be between 1 and 5,000 grams.")
    meal_type = request.form.get("meal_type", "")
    if meal_type not in MEAL_TYPES:
        abort(400, description="Select a valid meal type.")
    eaten_on = parse_date(request.form.get("eaten_on"))
    note = request.form.get("note", "").strip()
    if len(note) > 500:
        abort(400, description="Keep meal notes under 500 characters.")
    food = FOODS[food_key]
    nutrition = estimate_nutrition(food_key, grams)
    method = "confirmed_prediction" if food_key in session.pop("predicted_labels", []) else "manual"
    connection = get_db()
    with connection:
        connection.execute(
            """INSERT INTO meals
               (user_id, food_key, food_name, grams, calories, protein, carbs, fat,
                meal_type, eaten_on, note, entry_method, nutrition_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                g.user["id"],
                food_key,
                food["name"],
                grams,
                nutrition["calories"],
                nutrition["protein"],
                nutrition["carbs"],
                nutrition["fat"],
                meal_type,
                str(eaten_on),
                note,
                method,
                food["source"],
            ),
        )
    flash("Meal saved. Your dashboard and assistant now include this record.", "success")
    return redirect(url_for("web.diary", start=eaten_on, end=eaten_on))


@web.get("/diary")
@login_required
def diary():
    start, end = diary_period()
    return render_template(
        "diary.html",
        active="diary",
        start=start,
        end=end,
        today=user_today(g.user),
        meals=get_meals(g.user["id"], start, end),
        totals=summarize(g.user["id"], start, end),
    )


@web.post("/meals/<int:meal_id>/delete")
@login_required
def delete_meal(meal_id):
    connection = get_db()
    with connection:
        cursor = connection.execute(
            "DELETE FROM meals WHERE id = ? AND user_id = ?", (meal_id, g.user["id"])
        )
        if cursor.rowcount == 0:
            abort(404)
        # Saved answers may quote a deleted meal: remove stale evidence snapshots too.
        connection.execute("DELETE FROM chat_turns WHERE user_id = ?", (g.user["id"],))
    flash("Meal removed. Chat history was cleared to remove stale answers.", "success")
    return redirect(url_for("web.diary"))


@web.get("/export.csv")
@login_required
def export_csv():
    start, end = diary_period()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    fields = [
        "eaten_on",
        "meal_type",
        "food_name",
        "grams",
        "calories",
        "protein",
        "carbs",
        "fat",
        "note",
        "nutrition_source",
    ]
    writer.writerow(fields)
    for meal in get_meals(g.user["id"], start, end):
        values = []
        for field in fields:
            value = meal[field]
            # Prevent spreadsheet formula execution from user-written notes.
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return Response(
        stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="mealboy-{start}-{end}.csv"'},
    )


@web.get("/chat")
@login_required
def chat_page():
    rows = (
        get_db()
        .execute(
            "SELECT * FROM chat_turns WHERE user_id = ? ORDER BY id DESC LIMIT 30", (g.user["id"],)
        )
        .fetchall()
    )
    history = [{**dict(row), "sources": json.loads(row["sources_json"])} for row in reversed(rows)]
    return render_template(
        "chat.html", active="chat", history=history, provider=current_app.config["CHAT_PROVIDER"]
    )


@web.post("/api/chat")
@login_required
def chat_message():
    payload = request.get_json(silent=True)
    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= 1000:
        abort(400, description="Ask a question between 3 and 1,000 characters.")
    try:
        response = answer_question(g.user, question.strip())
    except ValueError as error:
        abort(400, description=str(error))
    connection = get_db()
    with connection:
        connection.execute(
            """INSERT INTO chat_turns (user_id, question, answer, mode, sources_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                g.user["id"],
                question.strip(),
                response["answer"],
                response["mode"],
                json.dumps(response["sources"]),
            ),
        )
    return jsonify(response)


@web.post("/chat/clear")
@login_required
def clear_chat():
    connection = get_db()
    with connection:
        connection.execute("DELETE FROM chat_turns WHERE user_id = ?", (g.user["id"],))
    return redirect(url_for("web.chat_page"))


@web.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        preferences = request.form.get("preferences", "").strip()
        timezone = request.form.get("timezone", "").strip()
        try:
            goal = int(request.form.get("calorie_goal", ""))
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError):
            abort(400, description="Enter a whole-number calorie goal and a valid time zone.")
        if not 2 <= len(name) <= 80 or not 500 <= goal <= 10000 or len(preferences) > 1000:
            abort(
                400, description="Check your name, goal (500–10,000) and preferences (1,000 max)."
            )
        connection = get_db()
        with connection:
            connection.execute(
                "UPDATE users SET name=?, calorie_goal=?, preferences=?, timezone=? WHERE id=?",
                (name, goal, preferences, timezone, g.user["id"]),
            )
            connection.execute("DELETE FROM chat_turns WHERE user_id=?", (g.user["id"],))
        flash(
            "Profile saved. Chat history was cleared so future answers use your updated profile.",
            "success",
        )
        return redirect(url_for("web.settings"))
    measurements = (
        get_db().execute("SELECT * FROM body_profiles WHERE user_id=?", (g.user["id"],)).fetchone()
    )
    metrics = (
        calculate(
            **{
                key: measurements[key]
                for key in ("age", "height_cm", "weight_kg", "formula_sex", "activity")
            }
        )
        if measurements
        else None
    )
    return render_template(
        "settings.html",
        active="settings",
        model_present=recognizer().artifacts_present,
        provider=current_app.config["CHAT_PROVIDER"],
        metrics=metrics,
        activities=ACTIVITY_FACTORS,
    )


@web.post("/settings/measurements")
@login_required
def save_measurements():
    connection = get_db()
    if request.form.get("action") == "clear":
        with connection:
            connection.execute("DELETE FROM body_profiles WHERE user_id=?", (g.user["id"],))
            connection.execute("DELETE FROM chat_turns WHERE user_id=?", (g.user["id"],))
        flash("Body measurements removed.", "success")
        return redirect(url_for("web.settings"))
    try:
        values = calculate(
            **{
                key: request.form.get(key)
                for key in ("age", "height_cm", "weight_kg", "formula_sex", "activity")
            }
        )
    except ValueError as error:
        abort(400, description=str(error))
    with connection:
        connection.execute(
            """INSERT INTO body_profiles (user_id, age, height_cm, weight_kg, formula_sex, activity)
               VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET
               age=excluded.age, height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
               formula_sex=excluded.formula_sex, activity=excluded.activity,
               updated_at=CURRENT_TIMESTAMP""",
            (
                g.user["id"],
                values["age"],
                values["height_cm"],
                values["weight_kg"],
                values["formula_sex"],
                values["activity"],
            ),
        )
        connection.execute("DELETE FROM chat_turns WHERE user_id=?", (g.user["id"],))
    flash(
        "Measurements saved. Your calorie goal is still your editable tracking target.", "success"
    )
    return redirect(url_for("web.settings"))


@web.get("/health")
def health():
    get_db().execute("SELECT 1")
    return jsonify(status="ok")
