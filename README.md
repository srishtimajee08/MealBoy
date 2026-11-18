# MealBoy

MealBoy is a food recognition and nutrition tracking application developed as a group project at KIIT. It brings image recognition, meal logging and a personal food diary into one place.

You can upload a food image, review the suggestions, choose a matching food reference and enter the portion weight. MealBoy then calculates calories and macronutrients, saves the meal and updates your dashboard. You can also log meals manually and ask questions about your saved records.

## About the project

We built MealBoy to make food journaling easier while keeping the calculations understandable. A photograph can suggest what a food might be, but it cannot reliably tell us its weight or exact recipe. That is why the application asks the user to confirm the food and enter its edible weight in grams.

The project runs locally using Flask and SQLite. Food recognition uses a trained MobileNetV2 model. The personal assistant retrieves information from the signed in user's records and includes links to the evidence behind its answers.

## Features

1. Account registration and login with password hashing and request protection.
2. Food image analysis with three suggestions and an uncertainty indicator.
3. Manual meal entry using a sourced nutrition catalogue.
4. Calories, protein, carbohydrates and fat calculated from portion weight.
5. A personal diary with date filters, CSV export and printable reports.
6. A dashboard with recent intake, a weekly chart and logging streaks.
7. A personal assistant that answers questions using saved meals and profile information.
8. Optional adult body estimates and an independently editable calorie goal.
9. Responsive pages with light and dark themes.

## Technology

Python and Flask handle application logic and requests. SQLite stores account information and meal records. Jinja templates, HTML, CSS and vanilla JavaScript provide the interface.

TensorFlow and Keras run the MobileNetV2 classifier. OpenCV handles image resizing. The assistant uses BM25 for text retrieval and SQL for complete date totals. Ollama is an optional addition for generated answers. Waitress serves the local application, while pytest and Ruff support development checks.

## Getting started on Windows

Install Python 3.12 with the Python launcher. Open PowerShell inside the MealBoy folder and run:

```powershell
.\setup_mealboy.ps1
.\run_mealboy.ps1
```

The setup script creates the ML environment and installs the pinned dependencies. Internet access is needed for this first installation.

Open [MealBoy locally](http://127.0.0.1:5000), create an account and sign in. Keep the server process running while using the application. Press Ctrl+C in its terminal to stop it.

The first startup creates the local database and signing secret inside `instance/`. No default account or sample meal history is created. Back up this directory privately if you want to preserve your records.

### Model availability

This repository includes the trained dish model and its label and confidence files in `artifacts/`. Raw datasets, training caches and personal records are excluded from Git.

For image recognition, keep `food_model.keras`, `labels.json` and `confidence.json` together in `artifacts/`. You can also reproduce the training pipeline. Without a compatible model, image analysis reports that setup is required. Manual meal logging and the default assistant remain available.

## Project submission

The [presentation](docs/MealBoy_Presentation_With_Snapshots.pptx) includes application screenshots and the four technical sections. The [academic report](docs/MealBoy_Academic_Submission_Report.pdf) provides the full project explanation.

## Using MealBoy

1. Create an account and set your preferences.
2. Choose manual entry or upload a clear food image.
3. Review the suggested food and select a suitable nutrition reference.
4. Enter the edible portion weight in grams and save the meal.
5. Check the diary and dashboard for the calculated totals.
6. Ask the assistant about your records and open its source links.

For example, a 200 g portion of the selected USDA cooked white rice reference produces 258 kcal. This calculation uses the chosen reference food. It does not measure the nutritional content of a photograph.

## Food recognition and results

The supplied image archives contain two different kinds of labels. One describes 96 individual dishes. The other describes 11 broad categories. These are trained as separate tasks because broad categories overlap individual dishes.

Both completed experiments use an ImageNet initialised MobileNetV2 backbone with frozen weights and a trained classification head. Images are converted to RGB and resized to 224 by 224 pixels. Input scaling is included in the exported model. The recorded runs did not use augmentation or backbone fine tuning.

### Dish recognition

The dish experiment used 66,193 training images, 14,186 validation images and 14,185 test images.

1. Top 1 accuracy: 60.70%.
2. Top 3 accuracy: 78.43%.
3. Macro F1: 60.05%.
4. Confidence threshold: 0.67.
5. Accepted test coverage: 41.83%.
6. Accuracy among accepted test predictions: 89.69%.

This is the model used by the application. User confirmation is required even when a prediction exceeds the confidence threshold.

### Category recognition

The category experiment used 7,244 training images, 853 validation images and 888 test images.

1. Top 1 accuracy: 86.49%.
2. Top 3 accuracy: 97.41%.
3. Macro F1: 84.50%.

The category model is an auxiliary experiment. It does not replace the dish model or identify a specific nutrition reference.

These results come from the project's custom partitions. They are not official benchmark results for the complete original dataset. See the [measured results](docs/model-results.md) for the method, artifact hashes and limitations.

## Nutrition data

The catalogue contains 75 selected USDA FNDDS reference foods with values per 100 g of edible food. These cover 64 of the 96 dish labels. Some foods are available for manual logging without being trained image classes.

The calculation is:

```text
Portion nutrient value = reference value per 100 g × portion grams ÷ 100
```

The server calculates the values and stores the nutrition source with each meal. A missing reference is not filled with a guessed value. For mixed meals, components can be logged separately.

Optional body estimates use the saved measurements and activity assumption. They do not automatically change the calorie goal and are not intended for clinical nutrition planning. Read the [nutrition documentation](docs/nutrition-and-body-estimates.md) for source details and calculation boundaries.

## Personal assistant

The default assistant uses BM25 retrieval and returns evidence from the current account. It works without an LLM. Questions about supported date ranges use complete database totals rather than adding only the few retrieved records.

Examples include:

1. How much protein did I log today?
2. Summarise my meals this week.
3. What is my saved calorie goal?
4. Find my rice meals.

Supported periods include today, yesterday, this week, last calendar week, the last seven days, this month, all time and explicit ISO dates. Each question needs its own context. Previous chat messages are displayed as history but are not used as evidence.

### Optional Ollama integration

Install Ollama, download the configured model and keep the local Ollama service running:

```text
ollama pull llama3.2:3b
```

Set these values in `.env` and restart MealBoy:

```dotenv
CHAT_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

The configured endpoint receives the question and retrieved context. The default address keeps this processing local. A remote endpoint changes where the information is sent.

Connection failures, timeouts and invalid citation references trigger a labelled evidence fallback. Citation checks confirm that references exist; they do not prove every generated statement is correct. The project includes adapter tests, but no live Ollama evaluation is reported.

## Reproducing training

Training requires the original prepared datasets, which are not included in the delivery ZIP or source repository. Dataset preparation and duplicate handling are described in the [dish dataset notes](docs/food101-dataset.md) and [combined collection notes](docs/combined-dataset.md).

With the prepared datasets and ML environment available, run:

```powershell
.venv-ml\Scripts\python ml/run_training.py
```

The pipeline caches image features, trains the separate heads, selects checkpoints and confidence thresholds using validation data, and evaluates the test partitions. Progress is recorded in `reports/training-run/status.json`.

Generate the results summary after evaluation:

```powershell
.venv-ml\Scripts\python tools/report_training.py
```

The application expects the same preprocessing and label order used during evaluation. Do not apply input scaling a second time to an exported model that already contains it.

## Project structure

```text
app.py                 Application entry point
mealboy/               Application package
  auth.py              Registration and login
  db.py                Database connections
  schema.sql           Database tables
  repository.py        Account scoped queries and summaries
  routes.py            Pages and request handling
  recognition.py       Image validation and prediction
  nutrition.py         Portion calculations
  body_metrics.py      Optional body estimates
  retrieval.py         Personal record retrieval
  chat.py              Evidence answers and generator adapter
  data/foods.json      Nutrition catalogue
  templates/           Page templates
  static/              Styles and browser scripts
ml/                    Dataset preparation and model experiments
tests/                 Automated tests
docs/                  Technical documentation
artifacts/             Local model files and training outputs
reports/               Local evaluation records
instance/              Private local database and configuration
```

## Testing

The recorded November validation passed 39 tests. Coverage includes authentication, account isolation, nutrition arithmetic, dataset duplicate handling, prediction uncertainty and assistant fallback behaviour.

Install the development dependencies in the configured environment and run:

```powershell
.venv-ml\Scripts\python -m pip install -r requirements-dev.txt
.venv-ml\Scripts\python -m pytest -q
.venv-ml\Scripts\python -m ruff check .
.venv-ml\Scripts\python -m ruff format --check .
```

Tests use temporary databases. The [validation record](docs/validation.md) separates completed checks from features that still need broader evaluation.

## Privacy and deployment

Meal records, exports, chat history and retrieval are scoped to the signed in account. Passwords are hashed, mutations require CSRF tokens and uploaded images are processed in memory rather than retained.

The current delivery is intended for local academic use. Public hosting requires HTTPS, a stable secret, secure cookie settings and a private persistent database directory. Password recovery, email verification, database migrations and larger scale operations require further work.

Do not publish `.env`, the `instance/` directory, personal exports or dataset images. Dataset redistribution must follow the relevant source terms.

## Current limitations

The classifier does not recognise every cuisine and has not been validated as an unknown food detector. Confidence scores are not guarantees of correctness. Images do not establish food weight, exact ingredients or allergens.

Nutrition depends on the selected reference and the weight entered by the user. The project has no clinical validation or weighed meal accuracy study. BM25 uses lexical matching and does not understand every synonym or date expression.

## Documentation

1. [Delivery guide](DELIVERY.md)
2. [Architecture and security](docs/architecture.md)
3. [Model results](docs/model-results.md)
4. [Nutrition sources](docs/nutrition-and-body-estimates.md)
5. [Dataset collection](docs/combined-dataset.md)
6. [Evaluation plan](docs/evaluation.md)

MealBoy is ready for local project demonstration with the supplied trained artifacts. The documentation records both what the application can do and the limits of the current implementation.
