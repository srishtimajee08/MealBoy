"""Inspect the supplied nutrition CSV and locally downloaded Nutrition5k metadata.

This script produces diagnostics only. It never edits source data, imports meals,
changes model labels, creates train/test splits, or guesses missing serving weights.
Run with --help for the two source paths and optional JSON report destination.
"""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def file_fingerprint(path):
    """Record exactly which source version was inspected."""
    return {
        "file": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def is_nonnegative_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def audit_nutrition_csv(path):
    """Separate raw parsing defects from statistics after a proposed field alignment.

    The supplied file has unquoted commas inside some food names. A proposed
    alignment is counted only if the name has balanced parentheses and all trailing
    nutrient fields are numeric. This remains a proposal, not an automatic import.
    """
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        source_rows = [(reader.line_num, row) for row in reader]

    expected_header = [
        "Food_Item",
        "Category",
        "Calories (kcal)",
        "Protein (g)",
        "Carbohydrates (g)",
        "Fat (g)",
        "Fiber (g)",
        "Sugars (g)",
        "Sodium (mg)",
        "Cholesterol (mg)",
        "Meal_Type",
        "Water_Intake (ml)",
    ]
    if header != expected_header:
        raise ValueError("The CSV schema has changed. Inspect the new headers before adapting it.")

    width_issues = []
    numeric_issues = []
    accepted_rows = []
    raw_rows = []
    for line_number, row in source_rows:
        raw_rows.append(tuple(row))
        candidate = row
        if len(row) != len(header):
            issue = {"line": line_number, "actual_fields": len(row), "raw_fields": row}
            if len(row) > len(header):
                name_parts = len(row) - len(header) + 1
                candidate = [",".join(row[:name_parts]), *row[name_parts:]]
                balanced_name = candidate[0].count("(") == candidate[0].count(")")
                numeric_suffix = all(
                    is_nonnegative_number(candidate[index]) for index in [*range(2, 10), 11]
                )
                if balanced_name and numeric_suffix:
                    issue["proposed_food_name"] = candidate[0]
                else:
                    candidate = None
            else:
                candidate = None
            width_issues.append(issue)
        if candidate is None:
            continue
        for index in [*range(2, 10), 11]:
            if not is_nonnegative_number(candidate[index]):
                numeric_issues.append({"line": line_number, "field": header[index]})
        accepted_rows.append(dict(zip(header, candidate)))

    names = Counter(row["Food_Item"].strip() for row in accepted_rows)
    nutrition_variants = defaultdict(set)
    for row in accepted_rows:
        nutrition_variants[row["Food_Item"]].add(tuple(row[field] for field in header[2:10]))
    return {
        **file_fingerprint(path),
        "row_count": len(source_rows),
        "columns": header,
        "raw_duplicate_rows_beyond_first": len(raw_rows) - len(set(raw_rows)),
        "malformed_rows": width_issues,
        "statistics_basis": "In-memory proposed alignment; original CSV is unchanged.",
        "rows_after_proposed_alignment": len(accepted_rows),
        "unique_food_names_after_proposed_alignment": len(names),
        "missing_cells": {
            field: sum(not row[field].strip() for row in accepted_rows) for field in header
        },
        "invalid_numeric_cells_after_proposed_alignment": numeric_issues,
        "category_counts": dict(Counter(row["Category"] for row in accepted_rows)),
        "meal_type_counts": dict(Counter(row["Meal_Type"] for row in accepted_rows)),
        "food_names_with_different_nutrient_values": {
            name: len(values) for name, values in nutrition_variants.items() if len(values) > 1
        },
        "has_serving_weight_column": False,
        "has_image_or_dish_id_column": False,
        "has_source_or_reference_column": False,
        "per_100g_conversion": "Unavailable without documented serving mass.",
        "food_names": sorted(names),
    }


def load_ids(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}


def audit_nutrition5k(root):
    """Read the actual six-field dish prefix and seven-field ingredient blocks.

    The downloaded CSV layout differs from the README's example. Treating dish IDs
    as class labels would train plate identities, not general food recognition.
    """
    ingredient_path = root / "metadata" / "ingredients_metadata.csv"
    with ingredient_path.open(encoding="utf-8-sig", newline="") as stream:
        ingredients = list(csv.DictReader(stream))
    ingredient_names = {f"ingr_{int(row['id']):010d}": row["ingr"] for row in ingredients}
    nutrient_columns = ["cal/g", "fat(g)", "carb(g)", "protein(g)"]
    ingredient_numeric_issues = [
        {"id": row["id"], "field": field}
        for row in ingredients
        for field in nutrient_columns
        if not is_nonnegative_number(row[field])
    ]

    dishes = {}
    source_counts = {}
    malformed = []
    duplicate_ids = []
    discrepancies = []
    sources = [file_fingerprint(ingredient_path)]
    for filename in ["dish_metadata_cafe1.csv", "dish_metadata_cafe2.csv"]:
        path = root / "metadata" / filename
        sources.append(file_fingerprint(path))
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            count = 0
            for row in reader:
                count += 1
                if len(row) < 13 or (len(row) - 6) % 7:
                    malformed.append({"file": filename, "line": reader.line_num})
                    continue
                dish_id = row[0]
                totals = [float(value) for value in row[1:6]]
                blocks = [row[index : index + 7] for index in range(6, len(row), 7)]
                ingredient_ids = {block[0] for block in blocks}
                if dish_id in dishes:
                    duplicate_ids.append(dish_id)
                # totals: calories, mass, fat, carbs, protein.
                sums = [sum(float(block[index]) for block in blocks) for index in [3, 2, 4, 5, 6]]
                if any(abs(total - value) > 1.0 for total, value in zip(totals, sums)):
                    discrepancies.append(dish_id)
                dishes[dish_id] = {
                    "ingredient_ids": ingredient_ids,
                    "calories": totals[0],
                    "mass": totals[1],
                    "numeric_valid": all(math.isfinite(value) and value >= 0 for value in totals),
                }
        source_counts[filename] = count

    split_info = {}
    for modality in ["rgb", "depth"]:
        train_path = root / "dish_ids" / "splits" / f"{modality}_train_ids.txt"
        test_path = root / "dish_ids" / "splits" / f"{modality}_test_ids.txt"
        train_ids = load_ids(train_path)
        test_ids = load_ids(test_path)
        sources.extend([file_fingerprint(train_path), file_fingerprint(test_path)])
        frequencies = Counter(
            ingredient
            for dish_id in train_ids & dishes.keys()
            for ingredient in dishes[dish_id]["ingredient_ids"]
        )
        split_info[modality] = {
            "train_dish_ids": len(train_ids),
            "test_dish_ids": len(test_ids),
            "overlapping_ids": sorted(train_ids & test_ids),
            "ids_without_metadata": sorted((train_ids | test_ids) - dishes.keys()),
            "training_ingredient_count": len(frequencies),
            "training_ingredient_dish_frequencies": dict(frequencies.most_common()),
            "least_frequent_training_ingredients": [
                {"id": key, "name": ingredient_names.get(key), "dish_count": count}
                for key, count in frequencies.most_common()[-10:]
            ],
            "most_frequent_training_ingredients": [
                {"id": key, "name": ingredient_names.get(key), "dish_count": count}
                for key, count in frequencies.most_common(10)
            ],
        }

    ingredient_counts = Counter(len(dish["ingredient_ids"]) for dish in dishes.values())
    observed_ids = set().union(*(dish["ingredient_ids"] for dish in dishes.values()))
    return {
        "sources": sources,
        "dish_rows_by_file": source_counts,
        "unique_dish_ids": len(dishes),
        "ingredient_metadata_rows": len(ingredients),
        "unique_ingredient_metadata_ids": len(ingredient_names),
        "observed_ingredient_ids": len(observed_ids),
        "unknown_ingredient_ids": sorted(observed_ids - ingredient_names.keys()),
        "ingredient_numeric_issues": ingredient_numeric_issues,
        "dish_numeric_issues": [key for key, dish in dishes.items() if not dish["numeric_valid"]],
        "duplicate_dish_ids": duplicate_ids,
        "malformed_dish_rows": malformed,
        "ingredients_per_dish_distribution": dict(sorted(ingredient_counts.items())),
        "single_ingredient_dishes": ingredient_counts[1],
        "multi_ingredient_dishes": sum(
            count for size, count in ingredient_counts.items() if size > 1
        ),
        "zero_calorie_dishes": [key for key, dish in dishes.items() if dish["calories"] == 0],
        "zero_mass_dishes": [key for key, dish in dishes.items() if dish["mass"] == 0],
        "total_vs_ingredient_sum_discrepancies_over_1_unit": discrepancies,
        "splits": split_info,
        "imagery_downloaded_by_this_audit": False,
        "image_counts_and_corruption_check": "Not performed: no training imagery downloaded.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--nutrition5k", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.csv.resolve():
        parser.error("The report must not overwrite the source CSV.")
    result = {
        "csv": audit_nutrition_csv(args.csv),
        "nutrition5k": audit_nutrition5k(args.nutrition5k),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Audit written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
