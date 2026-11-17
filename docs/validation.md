# Local validation record

## November 2026 update

The September record below is historical. Both user image archives are prepared
and a Python 3.12 ML environment is installed. Both models completed training and
held-out evaluation on 5 November 2026. See `model-results.md` for measured results.
The 96-dish model is installed in the app. Authenticated Flask uploads of three
held-out examples matched the evaluated model's predicted labels and scores,
including the validation-selected uncertainty threshold. The checks used an
isolated temporary database and are recorded in `reports/trained-app-verification.json`.

The expanded suite passed 39 tests, including body-estimate validation, account
isolation, duplicate handling and prediction uncertainty. A separate browser-test
database verified sign-in, measurement saving without changing the calorie goal,
and a 200 g USDA cooked-white-rice entry: 258 kcal, 5.3 g protein, 56.0 g carbs and
0.6 g fat. The assistant returned the same totals with citations to that user's
diary. No real user records were added by this check.

The catalogue now uses 75 USDA FNDDS reference records, with explicit per-100 g
basis and source identifiers. This does not validate recipe matching or establish
weighed-meal accuracy. See `nutrition-and-body-estimates.md`.

## Historical September record

Environment: Windows, Python 3.14, Flask 3.1.3. Date: 22 September 2026.

## Verified

- Application integration tests and local-generator contract tests pass.
- Ruff lint and Python formatting checks pass.
- Desktop browser: sign-in, empty dashboard, manual meal entry, food diary,
  nutrient preview, and a cited assistant answer.
- A 200 g cooked-rice entry produced 260 kcal, 5.4 g protein, 56.4 g carbs,
  and 0.6 g fat in the diary and assistant evidence.
- Mobile browser at 390 × 844: dashboard has no horizontal overflow; navigation,
  settings, appearance toggle and sign-out controls remain available.
- Light/dark switching changes the persisted theme. No browser console errors
  were observed in the tested flow.
- Waitress serves the app on 127.0.0.1:5000.

The browser used a disposable synthetic account. It is removed after verification;
normal application startup does not seed any users, meals or chat history.

## Not verified or not yet configured

- No food dataset or trained model was provided. TensorFlow training, inference on
  real food images, and recognition accuracy have not been run or measured.
- This machine's Python 3.14 environment is for the web app. Follow the Python 3.12
  ML environment instructions before training.
- No running Ollama model was available for a live generated-answer experiment.
  Request construction, citation checks, malformed response handling and fallback
  behavior are covered by contract/integration tests, not a live LLM evaluation.
- Catalogue nutrition is illustrative. No weighed-meal nutrition study was performed.
- Public HTTPS deployment, multi-host scaling and independent security auditing
  are outside this local validation.

Use the evaluation plan to produce genuine experimental results before presenting
the application as a validated final-year research project.
