"""Build explicit per-100g references from the official USDA FNDDS 2021-2023 JSON.

Mappings select named reference recipes, not nutrient ground truth for photographs.
The original USDA descriptions are displayed to users for confirmation.
"""

import hashlib
import json
import math
import zipfile
from pathlib import Path

REFERENCES = {
    "apple": 2709215,
    "banana": 2709224,
    "rice": 2708408,
    "chicken_breast": 2705956,
    "egg": 2707154,
    "lentils": 2707425,
    "oatmeal": 2708381,
    "yogurt": 2705418,
    "pizza": 2708614,
    "hamburger": 2706920,
    "french_fries": 2709461,
    "fried_rice": 2708951,
    "idli": 2708346,
    "dosa": 2708347,
    "biryani": 2708985,
    "baklava": 2708044,
    "bibimbap": 2708950,
    "bread_pudding": 2705680,
    "breakfast_burrito": 2707343,
    "bruschetta": 2707652,
    "caesar_salad": 2709591,
    "carrot_cake": 2707859,
    "ceviche": 2706463,
    "cheesecake": 2707861,
    "chicken_curry": 2706437,
    "chicken_quesadilla": 2708593,
    "chicken_wings": 2706068,
    "chocolate_cake": 2707866,
    "churros": 2708070,
    "clam_chowder": 2707139,
    "club_sandwich": 2706993,
    "crab_cakes": 2706549,
    "creme_brulee": 2705684,
    "deviled_eggs": 2707181,
    "donuts": 2708072,
    "dumplings": 2708344,
    "edamame": 2707436,
    "eggs_benedict": 2707180,
    "falafel": 2707408,
    "french_onion_soup": 2710108,
    "french_toast": 2708335,
    "fried_calamari": 2706334,
    "frozen_yogurt": 2705452,
    "garlic_bread": 2707627,
    "gnocchi": 2708722,
    "greek_salad": 2709830,
    "grilled_cheese_sandwich": 2705802,
    "guacamole": 2709308,
    "hot_and_sour_soup": 2707136,
    "hot_dog": 2707056,
    "huevos_rancheros": 2707191,
    "hummus": 2707402,
    "ice_cream": 2705630,
    "lasagna": 2708753,
    "miso_soup": 2707455,
    "mussels": 2706350,
    "nachos": 2708577,
    "omelette": 2707201,
    "onion_rings": 2710055,
    "oysters": 2706351,
    "pad_thai": 2708805,
    "pancakes": 2708304,
    "pho": 2707124,
    "pork_chop": 2705867,
    "ramen": 2709153,
    "ravioli": 2708764,
    "red_velvet_cake": 2707884,
    "samosa": 2708730,
    "scallops": 2706357,
    "steak": 2705824,
    "strawberry_shortcake": 2707896,
    "sushi": 2708961,
    "tacos": 2708515,
    "tiramisu": 2705702,
    "waffles": 2708320,
}
NUTRIENTS = {
    "calories": (1008, "kcal"),
    "protein": (1003, "g"),
    "carbs": (1005, "g"),
    "fat": (1004, "g"),
}
SOURCE = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_json_2024-10-31.zip"


def build():
    archive = Path("datasets/usda/fndds-2021-2023.zip")
    with zipfile.ZipFile(archive) as handle:
        records = {
            f["fdcId"]: f for f in json.loads(handle.read("surveyDownload.json"))["SurveyFoods"]
        }
    foods = []
    for key, identifier in sorted(REFERENCES.items()):
        food = records[identifier]
        nutrients = {n["nutrient"]["id"]: n for n in food["foodNutrients"]}
        values = {}
        for name, (nutrient_id, unit) in NUTRIENTS.items():
            entry = nutrients[nutrient_id]
            if entry["nutrient"]["unitName"].lower() != unit:
                raise ValueError(f"Unexpected unit for {identifier}/{name}")
            value = float(entry["amount"])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid nutrient value for {identifier}/{name}")
            values[name] = value
        link = f"https://fdc.nal.usda.gov/food-details/{identifier}/nutrients"
        foods.append(
            {
                "key": key,
                "name": food["description"],
                **values,
                "basis_g": 100,
                "fdc_id": identifier,
                "source_url": link,
                "source": f"USDA FNDDS 2021-2023, FDC {identifier}, per 100 g edible portion; "
                f"reference: {food['description']}. Actual recipes may differ.",
                "category": food.get("wweiaFoodCategory", {}).get(
                    "wweiaFoodCategoryDescription", "Food"
                ),
            }
        )
    Path("mealboy/data/foods.json").write_text(json.dumps(foods, indent=2) + "\n", encoding="utf-8")
    labels = json.loads(Path("datasets/food101-prepared/labels.json").read_text())
    report = {
        "source_url": SOURCE,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "basis": "per 100 g edible portion",
        "reference_count": len(foods),
        "supported_dish_labels": sorted(set(labels) & REFERENCES.keys()),
        "unsupported_dish_labels": sorted(set(labels) - REFERENCES.keys()),
        "policy": "Explicit named reference foods; user confirms recipe and grams. "
        "No nutrient values inferred from images or the unverified CSV.",
    }
    Path("reports/nutrition_catalogue.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
