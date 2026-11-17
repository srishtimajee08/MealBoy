"""Portion arithmetic and a transparent, replaceable nutrition catalogue."""

import json
from pathlib import Path

CATALOGUE = json.loads((Path(__file__).parent / "data" / "foods.json").read_text(encoding="utf-8"))
FOODS = {food["key"]: food for food in CATALOGUE}
NUTRIENTS = ("calories", "protein", "carbs", "fat")


def estimate_nutrition(food_key, grams):
    food = FOODS[food_key]
    return {name: round(food[name] * grams / 100, 1) for name in NUTRIENTS}
