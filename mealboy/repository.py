"""User-scoped reads shared by the dashboard, diary and retrieval layer."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .db import get_db


def user_today(user):
    return datetime.now(ZoneInfo(user["timezone"])).date()


def get_meals(user_id, start=None, end=None):
    query = "SELECT * FROM meals WHERE user_id = ?"
    parameters = [user_id]
    if start:
        query += " AND eaten_on >= ?"
        parameters.append(str(start))
    if end:
        query += " AND eaten_on <= ?"
        parameters.append(str(end))
    query += " ORDER BY eaten_on DESC, id DESC"
    return get_db().execute(query, parameters).fetchall()


def summarize(user_id, start, end):
    """Aggregate all matching records, never just the retrieved top-k documents."""
    row = (
        get_db()
        .execute(
            """SELECT COUNT(*) AS meal_count, COUNT(DISTINCT eaten_on) AS logged_days,
                  COALESCE(SUM(calories), 0) AS calories,
                  COALESCE(SUM(protein), 0) AS protein,
                  COALESCE(SUM(carbs), 0) AS carbs,
                  COALESCE(SUM(fat), 0) AS fat
           FROM meals WHERE user_id = ? AND eaten_on BETWEEN ? AND ?""",
            (user_id, str(start), str(end)),
        )
        .fetchone()
    )
    return {key: round(row[key], 1) for key in row.keys()}


def week_series(user_id, today):
    start = today - timedelta(days=6)
    rows = (
        get_db()
        .execute(
            """SELECT eaten_on, SUM(calories) AS calories FROM meals
           WHERE user_id = ? AND eaten_on BETWEEN ? AND ? GROUP BY eaten_on""",
            (user_id, str(start), str(today)),
        )
        .fetchall()
    )
    totals = {row["eaten_on"]: round(row["calories"]) for row in rows}
    return [
        {
            "date": str(start + timedelta(days=offset)),
            "label": (start + timedelta(days=offset)).strftime("%a"),
            "calories": totals.get(str(start + timedelta(days=offset)), 0),
        }
        for offset in range(7)
    ]


def logging_streak(user_id, today):
    rows = (
        get_db()
        .execute(
            "SELECT DISTINCT eaten_on FROM meals WHERE user_id = ? ORDER BY eaten_on DESC",
            (user_id,),
        )
        .fetchall()
    )
    days = {date.fromisoformat(row[0]) for row in rows}
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count
