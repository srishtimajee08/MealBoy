# Nutrition references and body estimates

The app uses explicitly selected USDA FNDDS 2021-2023 records. The official
[FNDDS documentation](https://www.ars.usda.gov/ARSUserFiles/80400530/pdf/fndds/2021_2023_FNDDS_Doc.pdf)
defines nutrient values per 100 g of edible portion. The
[USDA download](https://fdc.nal.usda.gov/download-datasets/) was obtained on 2026-11-05.

`tools/build_nutrition_catalogue.py` records the selected FDC identifiers, checks
nutrient units and preserves the original USDA descriptions. Its output contains
75 reference foods, covering 64 of the 96 trained dish labels. The source ZIP hash
and unsupported labels are recorded in `reports/nutrition_catalogue.json`.
The catalogue ships locally, so logging meals does not contact USDA or need an API key.

A label such as pizza selects a specific reference recipe, not measured nutrition
for the photographed plate. The dropdown and source text identify that recipe.
The user confirms the reference and enters edible grams. Calories and macros are
calculated on the server as `reference_per_100g * grams / 100`. Round after scaling.
Missing references are not assigned guessed values. Components can be logged separately.
Previously saved meals retain their original values and nutrition-source text.

The earlier user-supplied daily-food CSV remains excluded because its serving basis
is undocumented. The former illustrative chapati entry was removed rather than assigned
an unsupported USDA match. Idli, dosa and vegetable biryani now have USDA references
for manual logging; this does not mean the image model was trained to recognise them.

## Optional body measurements

Settings accepts optional age, height, weight, formula coefficient and activity
assumption. Values are stored in a separate owner-scoped table. Saving or clearing
them clears stale chat snapshots. Private retrieval can cite only the signed-in
user's measurements and computed estimates.

BMI = weight in kg / (height in metres squared). The app uses
[CDC adult BMI categories](https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html)
for ages 20 and above. It is a screening measure, not a diagnosis or body-composition
measurement. Input limits are application validation limits, not clinical thresholds.

The resting-energy estimate uses the simplified
[Mifflin-St Jeor equation](https://pubmed.ncbi.nlm.nih.gov/2305711/):
`10 * kg + 6.25 * cm - 5 * years + coefficient`, with +5 for the male coefficient
and -161 for the female coefficient. The paper estimates resting energy expenditure;
the UI identifies this as a BMR estimate for familiarity rather than a measured BMR.

TDEE multiplies the unrounded resting estimate by a user-selected activity factor
(1.2, 1.375, 1.55, 1.725 or 1.9). These are rough conventional assumptions, not
validated individual activity measurements. Values are rounded only for display.
No weight-loss deficit or medical diet is prescribed. The calorie goal stays an
independently editable tracking target. The calculator is not intended for pregnancy,
breastfeeding, children, or clinical nutrition planning.
