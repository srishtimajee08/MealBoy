"""Adult screening and resting-energy estimates, separate from editable user goals.

BMI: CDC adult categories (20+). Resting energy: simplified Mifflin-St Jeor,
PMID 2305711. Activity factors are rough user-selected assumptions, not measurements.
"""

import math

ACTIVITY_FACTORS = {
    "sedentary": (1.2, "Mostly sedentary"),
    "light": (1.375, "Light activity"),
    "moderate": (1.55, "Moderate activity"),
    "active": (1.725, "High activity"),
    "very_active": (1.9, "Very high activity"),
}


def calculate(age, height_cm, weight_kg, formula_sex, activity):
    try:
        age = int(age)
        height_cm, weight_kg = float(height_cm), float(weight_kg)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Enter valid age, height and weight values.") from None
    if (
        not 20 <= age <= 100
        or not math.isfinite(height_cm)
        or not math.isfinite(weight_kg)
        or not 100 <= height_cm <= 250
        or not 30 <= weight_kg <= 350
    ):
        raise ValueError("Use age 20–100 years, height 100–250 cm and weight 30–350 kg.")
    if formula_sex not in {"female", "male"} or activity not in ACTIVITY_FACTORS:
        raise ValueError("Select a formula coefficient and activity level.")
    bmi = weight_kg / (height_cm / 100) ** 2
    category = (
        "Underweight"
        if bmi < 18.5
        else "Healthy weight"
        if bmi < 25
        else "Overweight"
        if bmi < 30
        else "Obesity"
    )
    resting = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if formula_sex == "male" else -161)
    return {
        "age": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "formula_sex": formula_sex,
        "activity": activity,
        "bmi": round(bmi, 1),
        "bmi_category": category,
        "bmr": round(resting),
        "tdee": round(resting * ACTIVITY_FACTORS[activity][0]),
    }
