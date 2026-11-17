"""Inspectable BM25 retrieval over one user's records, with exact date summaries.

No global document index exists: access control happens before document creation.
BM25 is the offline lexical baseline; it needs no downloaded embedding model.
"""

import math
import re
from collections import Counter
from datetime import date, timedelta

from .body_metrics import calculate
from .db import get_db
from .repository import get_meals, summarize

STOP_WORDS = set("a an the my me i is are was were of to for in on and what how did do".split())
ALIASES = {
    "ate": "food",
    "eaten": "food",
    "eating": "food",
    "meals": "meal",
    "calorie": "calories",
    "carbohydrates": "carbs",
    "proteins": "protein",
}


def tokens(text):
    return [
        ALIASES.get(word, word)
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if word not in STOP_WORDS
    ]


def rank_documents(question, documents, limit=5):
    if not documents:
        return []
    query = set(tokens(question))
    document_tokens = [tokens(document["text"]) for document in documents]
    average_length = sum(map(len, document_tokens)) / len(document_tokens) or 1
    frequencies = Counter(term for words in document_tokens for term in set(words))
    scored = []
    for document, words in zip(documents, document_tokens):
        counts = Counter(words)
        score = 0.0
        for term in query:
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
            )
            normalization = frequency + 1.5 * (0.25 + 0.75 * len(words) / average_length)
            score += inverse_frequency * frequency * 2.5 / normalization
        if score > 0:
            scored.append((score, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [document for _, document in scored[:limit]]


def question_period(question, today):
    """Recognize a small, documented set of periods; never silently guess others."""
    text = question.lower()
    explicit = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if explicit:
        try:
            days = [date.fromisoformat(value) for value in explicit]
        except ValueError:
            raise ValueError("Use valid dates in YYYY-MM-DD format.") from None
        if len(days) > 2 or days[0] > days[-1]:
            raise ValueError("Use one date or a start date followed by an end date.")
        if days[0] < date(1900, 1, 1) or days[-1] > today:
            raise ValueError("Choose recorded dates between 1900-01-01 and today.")
        return days[0], days[-1], "selected dates"
    if "yesterday" in text:
        day = today - timedelta(days=1)
        return day, day, "yesterday"
    if "today" in text:
        return today, today, "today"
    if "last week" in text:
        end = today - timedelta(days=today.weekday() + 1)
        return end - timedelta(days=6), end, "last calendar week"
    if "this week" in text:
        return today - timedelta(days=today.weekday()), today, "this week so far"
    if "last 7 days" in text or "past 7 days" in text:
        return today - timedelta(days=6), today, "last 7 days including today"
    if "this month" in text:
        return today.replace(day=1), today, "this month so far"
    if "all time" in text or "all-time" in text or "ever" in text:
        return date(1900, 1, 1), today, "all logged dates"
    return None


def build_context(user, question, today):
    period = question_period(question, today)
    profile = {
        "id": "profile",
        "title": "Your saved profile",
        "url": "/settings",
        "text": (
            f"Name: {user['name']}. Daily calorie goal: {user['calorie_goal']} kcal. "
            f"Preferences (user-written): {user['preferences'] or 'Not provided'}."
        ),
    }
    body = get_db().execute("SELECT * FROM body_profiles WHERE user_id=?", (user["id"],)).fetchone()
    if body:
        metrics = calculate(
            **{
                key: body[key]
                for key in ("age", "height_cm", "weight_kg", "formula_sex", "activity")
            }
        )
        profile["text"] += (
            f" Saved measurements: age {body['age']}, height {body['height_cm']:g} cm, "
            f"weight {body['weight_kg']:g} kg. BMI screening estimate: {metrics['bmi']} "
            f"({metrics['bmi_category']}). Resting energy BMR estimate: {metrics['bmr']} kcal/day. "
            f"Maintenance TDEE estimate: {metrics['tdee']} kcal/day, using "
            f"{body['activity']} activity assumption and "
            f"{body['formula_sex']} formula coefficient. "
            "These are estimates, not diagnoses or prescribed calorie targets."
        )
    if period:
        start, end, label = period
        meals = get_meals(user["id"], start, end)
    else:
        meals = get_meals(user["id"])
    documents = []
    for meal in meals:
        documents.append(
            {
                "id": f"meal-{meal['id']}",
                "title": f"{meal['food_name']} · {meal['eaten_on']}",
                "url": f"/diary?start={meal['eaten_on']}&end={meal['eaten_on']}#meal-{meal['id']}",
                "text": (
                    f"Food meal on {meal['eaten_on']}, {meal['meal_type']}: "
                    f"{meal['food_name']}, {meal['grams']:g} g; "
                    f"{meal['calories']:g} kcal calories, {meal['protein']:g} g protein, "
                    f"{meal['carbs']:g} g carbs, {meal['fat']:g} g fat. "
                    f"Note (user-written): {meal['note'] or 'None'}."
                ),
            }
        )
    selected = rank_documents(question, [profile, *documents])
    if period:
        # A period is already a meaningful filter. Include recent records even when
        # words such as "log" or "summarize" do not overlap the meal descriptions.
        if not any(item["id"].startswith("meal-") for item in selected):
            selected = [*selected, *documents[:5]][:5]
        totals = summarize(user["id"], start, end)
        summary = {
            "id": "period-summary",
            "title": f"Complete log summary · {label}",
            "url": f"/diary?start={start}&end={end}",
            "text": (
                f"Period: {start} to {end} ({label}). "
                f"{totals['meal_count']} logged meals across {totals['logged_days']} days. "
                f"Total recorded calories: {totals['calories']:g} kcal; "
                f"protein: {totals['protein']:g} g; carbs: {totals['carbs']:g} g; "
                f"fat: {totals['fat']:g} g. Missing logs do not mean no food was eaten. "
                f"Current saved daily goal: {user['calorie_goal']} kcal."
            ),
        }
        selected = [summary, *selected]
    return selected[:6]
