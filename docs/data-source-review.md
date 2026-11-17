# Review of the supplied food datasets

This review records measurements from the supplied CSV and downloaded Nutrition5k
metadata. No model has been trained and no accuracy result is available. The
existing frontend and application behavior have not been changed by this audit.

## How the two sources can be used

Photos are the model inputs. Food labels paired with those photos are the training
targets. Nutrition5k connects photos to ingredient labels and nutrient measurements
using dish IDs; the model does not need text printed on an example image.

Most Nutrition5k plates have several ingredient labels. Learning from this source
therefore calls for multi-label ingredient recognition, rather than treating every
plate as one named dish. Some ingredients, such as oil and salt, are not reliably
visible. Predictions must remain suggestions that users can correct.

The supplied daily-food CSV is intended as a nutrition reference. It has no image
IDs and cannot automatically be joined to Nutrition5k photographs. Its serving
basis must be documented before using its numbers for weight-based calculations.
Providing a number in a CSV does not establish its accuracy or its serving basis.

## CSV audit

Source: `C:\Users\KIIT0001\Downloads\archive\daily_food_nutrition_dataset.csv`.

- 651 data rows and 12 columns.
- 54 exact duplicate rows beyond the first occurrence.
- Six rows contain an unquoted comma inside the food name, producing 13 fields:
  source lines 21, 50, 235, 238, 378 and 445 (including the header).
- No serving-weight, image-ID or source-reference columns.
- Some names specify cups, slices or other portions; others do not specify a portion.

The audit proposes repairing the six field alignments in memory for inspection.
It does not change the original CSV or certify the nutrition values. In particular,
do not assume that all rows represent 100 grams, infer gram weights from cups, or
interpret `Water_Intake (ml)` as the water content of a food.

Before importing these values into the diary calculator, obtain the original
source documentation and a serving basis for each usable row. A useful normalized
reference table would contain `food_name`, `serving_size_g`, `calories`,
`protein_g`, `carbohydrates_g`, `fat_g` and `source`. All nutrient values must refer
to that same serving size. Optional fiber values should remain missing when unknown.

## Nutrition5k metadata audit

Official source: [Nutrition5k repository](https://github.com/google-research-datasets/Nutrition5k).
Metadata and split files were downloaded from its linked public storage bucket.
Local copies are under `datasets/nutrition5k/`; fingerprints are in the JSON report.

| Measurement | Audited count |
| --- | ---: |
| Unique dish IDs | 5,006 |
| Cafe1 dish rows | 4,768 |
| Cafe2 dish rows | 238 |
| Ingredient reference rows | 555 |
| Ingredient IDs observed in dish metadata | 256 |
| Single-ingredient dishes | 1,816 |
| Multiple-ingredient dishes | 3,190 |
| Official RGB training dish IDs | 4,059 |
| Official RGB test dish IDs | 709 |
| Ingredients present in RGB training metadata | 210 |
| Official depth training dish IDs | 2,758 |
| Official depth test dish IDs | 507 |

These are metadata counts, not verified image counts or a finalized set of model
classes. Labels are very imbalanced: olive oil occurs in 1,418 RGB training dishes,
while several labels occur once. A `plate only` label also needs explicit handling.

There are 240 dishes with zero total calories and 506 dishes where at least one
dish total differs from the sum of its ingredient values by more than one unit
(kcal for energy; grams for mass and macros). These are review flags, not proof
that every flagged row is unusable. Do not silently repair them or use unreviewed
totals as regression targets.

The actual downloaded dish CSV format differs from the repository's example:

```text
dish_id, total_calories, total_mass, total_fat, total_carb, total_protein,
ingredient_id, ingredient_name, grams, calories, fat, carbs, protein,
[repeat the seven ingredient fields for each further ingredient]
```

There is no ingredient-count field in these downloaded rows. The ingredient
reference filename is `ingredients_metadata.csv` (plural). Its nutrition values
are per gram according to the official documentation. Retain that basis explicitly
when preparing a reference table; do not mix it with the supplied CSV's unknown basis.

## What is needed before training

Original training imagery has not been downloaded or checked. The complete archive
is approximately 181.4 GB according to the repository. Choose the required imagery
subset before downloading; metadata alone cannot train image recognition.

After imagery is available:

1. Match image paths to actual dish IDs and verify readable files and label coverage.
2. Preserve official test separation and keep related plate scans together when
   making a validation split. Never split video frames independently.
3. Review rare labels, invisible ingredients and inconsistent nutrient measurements.
4. Train a lightweight transfer-learning model for multiple ingredient labels.
5. Evaluate per-label precision/recall, micro/macro F1 and average precision, alongside
   training/validation loss. Ordinary single-label accuracy and a single multiclass
   confusion matrix are insufficient for this target.
6. Save model weights, label mapping, preprocessing settings and decision thresholds.

For tracking, users must still confirm the food and its serving amount. If a plate
contains several predicted ingredients, a total plate weight alone does not tell
us each ingredient's weight. Ask for ingredient portions or a verified recipe
serving before summing nutrition values. Direct image-to-nutrient regression could
be studied separately, with measured error, but cannot promise exact nutrition.

## Reproducing the metadata audit

The audit uses only Python's standard library:

```powershell
python tools/audit_data_sources.py --csv "C:\Users\KIIT0001\Downloads\archive\daily_food_nutrition_dataset.csv" --nutrition5k datasets/nutrition5k --output reports/data_source_audit.json
```

The report includes source hashes, field-alignment issues, label frequencies and
split checks. It does not download images, train a model or alter source files.
