# Combined food image collection

Completed 2026-11-05. Both input archives remain unchanged.

The collection contains **111,211 image records**: 94,568 existing dish-labelled images and 16,643 ZIP category-labelled images. These are records, not unique photographs. All manifest paths exist and are unique; copied ZIP bytes and split separation were verified.

## Why the labels remain separate

The TAR has 96 dish labels. The ZIP has 11 broad categories, such as Dessert and Meat. Broad categories overlap dish labels, so flattening them into a 107-class softmax would create contradictory targets. Both datasets are indexed together but retain separate training targets: `food_dish` and `food_category`. No fine-grained dish labels or nutrition measurements were invented for the ZIP images.

## ZIP import results

| Partition | Images |
|---|---:|
| train | 7,244 |
| val | 853 |
| test | 888 |
| review | 7,658 |

Rejected/unreadable files: **0**. All 11 categories appear in train, validation and test.

**14,309 ZIP images are byte-identical to existing images.** There are also 623 byte-duplicate extras within the ZIP. These counts overlap and must not be added. All 16,643 records are preserved. Same-partition duplicates remain; training the category task separately avoids counting them twice within a single combined dish task.

The existing TAR partitions were preserved. ZIP `training`, `validation`, and `evaluation` map to `train`, `val`, and `test`. **7,658 ZIP records were retained in review because their duplicate groups conflict with held-out boundaries.** No held-out images were moved into training. New-only duplicate groups prioritize test, then validation, then train; conflicting records go to review. Exact byte/pixel hashes and identical dHash signatures were checked across both sources. This does not guarantee detection of every near duplicate.

## Category counts

| Category | Train | Validation | Test | Review |
|---|---:|---:|---:|---:|
| bread | 692 | 49 | 57 | 926 |
| dairy_product | 345 | 64 | 61 | 251 |
| dessert | 1089 | 120 | 133 | 1158 |
| egg | 677 | 47 | 49 | 875 |
| fried_food | 575 | 52 | 35 | 799 |
| meat | 991 | 132 | 133 | 950 |
| noodles_pasta | 377 | 76 | 71 | 210 |
| rice | 220 | 28 | 29 | 195 |
| seafood | 593 | 55 | 47 | 810 |
| soup | 1051 | 66 | 74 | 1309 |
| vegetable_fruit | 634 | 164 | 199 | 175 |

## Files and usage

- `datasets/collection.json`: collection index.
- `datasets/combined_manifest.json`: every image record; paths are relative to `datasets/`.
- `datasets/food101-prepared/`: unchanged dish dataset.
- `datasets/food11-prepared/`: added category dataset, manifest, summary and completion marker.
- `review/` images are retained for inspection and excluded from the train/val/test loaders. Do not blindly move these into training.

Train each target separately:

```powershell
.venv-ml\Scripts\python ml/train.py datasets/food101-prepared --output artifacts/food101
.venv-ml\Scripts\python ml/train.py datasets/food11-prepared --output artifacts/food11
```

Do not pass the dataset collection root to the directory classifier. TensorFlow installation remains incomplete from the earlier interrupted download; these commands require the ML dependencies first. This import did not train a model or produce accuracy results. The category model is not configured as the app dish recognizer.

Validation: 31 project tests passed, including archive safety, original-record preservation, and duplicate leakage handling. Ruff lint and formatting checks passed. Folder labels have not all been manually verified.

Combined record totals (across separate tasks): `{"train": 73437, "val": 15039, "test": 15073, "review": 7662}`.
