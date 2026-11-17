# Supplied Food-101 archive audit

Source: `C:\Users\KIIT0001\Downloads\food-101.tar` (4,848,194,048 bytes).
Decoded 94,568 images across 96 folder labels.
Rejected unreadable/unsupported files: 0.

## Preparation

This archive contains images only, without official train/test metadata. It is a partial collection with a custom approximate 70/15/15 split (seed 42). Do not present its evaluation as the official Food-101 benchmark.

Original files remain untouched. Prepared names follow `food_name_img0001.jpg`. `manifest.json` maps every output to its original TAR member, label, hashes and group. Matching byte hashes, decoded-pixel hashes and exact 64-bit dHash signatures are grouped before splitting. Cross-label groups go to `review/` and are excluded from training and evaluation. Matching dHash is a candidate signal, not proof of duplication. Other near duplicates may remain; manual review is still needed.

Split totals: `{"train": 66193, "val": 14186, "test": 14185, "review": 4}`.
Byte duplicate extras: 7; decoded-pixel duplicate extras: 52.
Multi-image candidate groups: 86; cross-label groups: 2.

## Label quality and nutrition

Folder names are supplied labels, not independently verified annotations. The uploaded beignets examples include restaurant interiors (1367474.jpg, 2741104.jpg), empty dishes (2541549.jpg), and a preparation counter (634889.jpg). These need manual review before reporting final model quality. They have not been silently relabelled or deleted.

This dataset has no measured calories, macros, serving weights or ingredient amounts. Recognition and nutrition lookup remain separate. The catalogue column below records the historical preparation-time coverage. The current catalogue instead contains sourced USDA references covering 64 of these 96 labels; see `nutrition-and-body-estimates.md` and `reports/nutrition_catalogue.json`. These are reference recipes, not measurements of these photographs. The earlier nutrition CSV remains excluded because its serving basis is undocumented. Dosa, idli and biryani cannot be learned from folders absent in this archive.

| Class | Train | Validation | Test | Review | Nutrition catalogue |
|---|---:|---:|---:|---:|---|
| baby_back_ribs | 68 | 15 | 15 | 0 | Missing |
| baklava | 700 | 150 | 150 | 0 | Missing |
| beef_carpaccio | 700 | 150 | 150 | 0 | Missing |
| beef_tartare | 700 | 150 | 150 | 0 | Missing |
| beet_salad | 700 | 150 | 150 | 0 | Missing |
| beignets | 700 | 150 | 150 | 0 | Missing |
| bibimbap | 700 | 150 | 150 | 0 | Missing |
| bread_pudding | 700 | 150 | 150 | 0 | Missing |
| breakfast_burrito | 700 | 150 | 150 | 0 | Missing |
| bruschetta | 700 | 150 | 150 | 0 | Missing |
| caesar_salad | 700 | 150 | 150 | 0 | Missing |
| cannoli | 329 | 71 | 70 | 0 | Missing |
| caprese_salad | 700 | 150 | 150 | 0 | Missing |
| carrot_cake | 700 | 150 | 150 | 0 | Missing |
| ceviche | 700 | 150 | 150 | 0 | Missing |
| cheese_plate | 700 | 150 | 150 | 0 | Missing |
| cheesecake | 700 | 150 | 150 | 0 | Missing |
| chicken_curry | 700 | 150 | 150 | 0 | Missing |
| chicken_quesadilla | 700 | 150 | 150 | 0 | Missing |
| chicken_wings | 700 | 150 | 150 | 0 | Missing |
| chocolate_cake | 700 | 150 | 150 | 0 | Missing |
| chocolate_mousse | 700 | 150 | 150 | 0 | Missing |
| churros | 700 | 150 | 150 | 0 | Missing |
| clam_chowder | 700 | 150 | 150 | 0 | Missing |
| club_sandwich | 700 | 150 | 150 | 0 | Missing |
| crab_cakes | 700 | 150 | 150 | 0 | Missing |
| creme_brulee | 700 | 150 | 150 | 0 | Missing |
| croque_madame | 700 | 150 | 150 | 0 | Missing |
| cup_cakes | 700 | 150 | 150 | 0 | Missing |
| deviled_eggs | 700 | 150 | 150 | 0 | Missing |
| donuts | 700 | 150 | 150 | 0 | Missing |
| dumplings | 700 | 150 | 150 | 0 | Missing |
| edamame | 700 | 150 | 150 | 0 | Missing |
| eggs_benedict | 700 | 150 | 150 | 0 | Missing |
| escargots | 700 | 150 | 150 | 0 | Missing |
| falafel | 700 | 150 | 150 | 0 | Missing |
| filet_mignon | 700 | 150 | 150 | 0 | Missing |
| fish_and_chips | 700 | 150 | 150 | 0 | Missing |
| foie_gras | 700 | 150 | 150 | 0 | Missing |
| french_fries | 700 | 150 | 150 | 0 | Illustrative only |
| french_onion_soup | 700 | 150 | 150 | 0 | Missing |
| french_toast | 700 | 150 | 150 | 0 | Missing |
| fried_calamari | 700 | 150 | 150 | 0 | Missing |
| fried_rice | 700 | 150 | 150 | 0 | Illustrative only |
| frozen_yogurt | 700 | 150 | 150 | 0 | Missing |
| garlic_bread | 700 | 150 | 150 | 0 | Missing |
| gnocchi | 700 | 150 | 150 | 0 | Missing |
| greek_salad | 700 | 150 | 150 | 0 | Missing |
| grilled_cheese_sandwich | 700 | 150 | 150 | 0 | Missing |
| guacamole | 700 | 150 | 150 | 0 | Missing |
| gyoza | 700 | 150 | 150 | 0 | Missing |
| hamburger | 700 | 150 | 150 | 0 | Illustrative only |
| hot_and_sour_soup | 700 | 150 | 150 | 0 | Missing |
| hot_dog | 700 | 150 | 150 | 0 | Missing |
| huevos_rancheros | 700 | 150 | 150 | 0 | Missing |
| hummus | 700 | 150 | 150 | 0 | Missing |
| ice_cream | 700 | 150 | 150 | 0 | Missing |
| lasagna | 700 | 150 | 150 | 0 | Missing |
| lobster_bisque | 700 | 150 | 150 | 0 | Missing |
| lobster_roll_sandwich | 700 | 150 | 150 | 0 | Missing |
| macarons | 700 | 150 | 150 | 0 | Missing |
| miso_soup | 700 | 150 | 150 | 0 | Missing |
| mussels | 700 | 150 | 150 | 0 | Missing |
| nachos | 700 | 150 | 150 | 0 | Missing |
| omelette | 699 | 150 | 150 | 1 | Missing |
| onion_rings | 700 | 150 | 150 | 0 | Missing |
| oysters | 700 | 150 | 150 | 0 | Missing |
| pad_thai | 700 | 150 | 150 | 0 | Missing |
| pancakes | 699 | 150 | 150 | 1 | Missing |
| panna_cotta | 700 | 150 | 150 | 0 | Missing |
| peking_duck | 700 | 150 | 150 | 0 | Missing |
| pho | 700 | 150 | 150 | 0 | Missing |
| pizza | 700 | 150 | 150 | 0 | Illustrative only |
| pork_chop | 700 | 150 | 150 | 0 | Missing |
| poutine | 700 | 150 | 150 | 0 | Missing |
| prime_rib | 699 | 150 | 150 | 1 | Missing |
| pulled_pork_sandwich | 700 | 150 | 150 | 0 | Missing |
| ramen | 700 | 150 | 150 | 0 | Missing |
| ravioli | 700 | 150 | 150 | 0 | Missing |
| red_velvet_cake | 700 | 150 | 150 | 0 | Missing |
| risotto | 700 | 150 | 150 | 0 | Missing |
| samosa | 700 | 150 | 150 | 0 | Missing |
| sashimi | 700 | 150 | 150 | 0 | Missing |
| scallops | 700 | 150 | 150 | 0 | Missing |
| seaweed_salad | 700 | 150 | 150 | 0 | Missing |
| shrimp_and_grits | 700 | 150 | 150 | 0 | Missing |
| spaghetti_carbonara | 700 | 150 | 150 | 0 | Missing |
| spring_rolls | 700 | 150 | 150 | 0 | Missing |
| steak | 699 | 150 | 150 | 1 | Missing |
| strawberry_shortcake | 700 | 150 | 150 | 0 | Missing |
| sushi | 700 | 150 | 150 | 0 | Missing |
| tacos | 700 | 150 | 150 | 0 | Missing |
| takoyaki | 700 | 150 | 150 | 0 | Missing |
| tiramisu | 700 | 150 | 150 | 0 | Missing |
| tuna_tartare | 700 | 150 | 150 | 0 | Missing |
| waffles | 700 | 150 | 150 | 0 | Missing |

## Training and evaluation

Training is a separate compute-intensive step. No accuracy is inferred from successful preparation. Use Python 3.12 with requirements-ml.txt installed.

Run status (2026-11-05): dataset preparation completed with every copied file hash verified. All 96 classes appear in each usable split. Project tests: 30 passed; dataset tests also passed after the directory-creation optimization. TensorFlow installation was attempted in .venv-ml but its download repeatedly disconnected and was stopped. This environment is incomplete. No model was trained and no accuracy results were produced during this preparation run.

```powershell
.venv-ml\Scripts\python ml/train.py datasets/food101-prepared --output artifacts/food101
.venv-ml\Scripts\python ml/evaluate.py datasets/food101-prepared/test --artifacts artifacts/food101 --output reports/food101-evaluation
```

Training exports model weights, ordered labels, histories, training curves and a configuration containing the dataset manifest hash. Evaluation exports measured classification metrics and a confusion matrix. Keep test data out of model selection.

After evaluation, set MODEL_PATH=artifacts/food101/food_model.keras and MODEL_LABELS_PATH=artifacts/food101/labels.json to use that model in the app.
