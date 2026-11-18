# MealBoy delivery guide

This is a local Windows academic application with trained food recognition,
USDA-reference portion calculations, a private food diary, dashboard, CSV export,
printable reports, adult body estimates and a cited personal-record assistant.

## Run on this computer

Open PowerShell in the MealBoy folder and run `./run_mealboy.ps1`.
Open **http://127.0.0.1:5000**, create your own account and sign in.
Keep the terminal open while using the app; Ctrl+C stops it.

## Run the delivery ZIP on another computer

1. Extract the ZIP to a writable folder, outside the compressed-folder viewer.
2. Install Python 3.12 (64-bit) with the Python launcher.
3. Open PowerShell in the extracted `MealBoy` folder and run `./setup_mealboy.ps1`.
   This first setup needs internet access to install the pinned dependencies.
4. Run `./run_mealboy.ps1` and visit the localhost address above.

The trained model is included; image recognition needs no retraining or API key.
The default extractive assistant also works locally after setup. Optional Ollama
generation is described in README.md and is not required for the delivered flow.
Personal accounts and diary records are created locally in `instance/` on first use.
The delivery ZIP excludes existing accounts, secrets, uploads, raw datasets and
Python environments. It includes a file-hash manifest and a ZIP checksum.

## Demonstration

1. Open Analyze food and upload one clear food image. The first prediction can be
   slower while TensorFlow and the model load. Review the three suggestions.
2. Confirm a matching USDA reference food and enter its edible weight in grams.
   Save the meal and check the diary and dashboard totals.
3. Ask the assistant “How much protein did I log today?” and inspect its citations.
4. In Settings, optionally save adult measurements. These estimates leave your
   calorie goal independently editable.
5. Export a date range as CSV or use Print / PDF. A second account has its own
   records and assistant evidence.

## Results and boundaries

See [measured model results](docs/model-results.md),
[validation record](docs/validation.md) and
[nutrition sources](docs/nutrition-and-body-estimates.md).
There are separate 96-dish and 11-category models; the app uses the dish model.
The current USDA catalogue covers 64 of its 96 labels. Other labels need a manual
reference selection. A photograph does not establish portion mass, exact recipe,
ingredients or allergens. Low-confidence predictions are explicitly flagged.

The image archive uses a custom split, so results are not the official Food-101
benchmark. This delivery is ready for local demonstration and evaluation; public
hosting needs HTTPS and the deployment configuration documented in README.md.
There is no clinical validation or live generative-LLM evaluation.

## Reproduce checks

Install `requirements-dev.txt` into the environment, then run `python -m pytest -q`.
The full source training pipeline is `python ml/run_training.py`; raw prepared
datasets are not bundled. Keep the original workspace to reproduce dataset-based
experiments and `tools/verify_trained_app.py`. Evaluation metrics and curves are
included in the ZIP for inspection without the original images.
