# Reference review and project scope

Reference: [NutriScan Pro video](https://www.youtube.com/watch?v=ua5oo3Bzzyc),
published by Always Daya. Reviewed the expanded description and auto-generated English
transcript on 22 September 2026. Transcript wording may contain recognition errors;
source code and backend implementation were not available for inspection.

## What the reference demonstrates

The walkthrough includes registration/sign-in (about 1:38), a nutrition dashboard
(1:54), image uploads with predicted food and nutrition (2:50), meal saving (5:04),
profile and goal settings (5:38), meal planning (7:57), progress and weight tracking
(8:44), an admin overview (9:17), theme switching (9:54), and history/PDF export (10:13).
The description lists a React/Angular frontend, an API backend, CNN-based machine
learning, and GitHub Pages deployment. These claims do not verify Flask, MobileNetV2,
the training dataset, model accuracy, portion measurement, or user-data access controls.
A public live-project address is mentioned, but no usable repository link is provided
in the expanded description. No personalized retrieval chatbot is described.

## MealBoy's implementation decisions

| Concern | Decision | Why it matters for a major project |
|---|---|---|
| Framework | Flask + Jinja + SQLite | Easy to run, inspect, and explain end to end |
| Food recognition | Train MobileNetV2; save exact label order | Reproducible inference rather than unexplained labels |
| Portion size | User enters grams after confirming the food | Avoids claiming weight estimation from a single photograph |
| Nutrition | Deterministic per-100-g lookup scaled by grams | Clear formula and replaceable data source |
| Personalization | Logged meals + profile, filtered by authenticated owner | Prevents cross-account retrieval |
| Retrieval | BM25 lexical baseline | Inspectable ranking, offline availability, measurable baseline |
| Generation | Optional local Ollama + citations | Full RAG path without requiring a paid service |
| Totals | SQL aggregates over the complete date range | Avoids summing an incomplete top-k retrieval sample |
| Missing setup | Explicit unavailable state | No fake predictions, accuracy, or generated responses |

## Scope boundaries

Implemented: authentication, food logging, classifier integration, nutrition estimation,
dashboard, diary, CSV/printable reports, preferences, private assistant, training and
evaluation tooling. Meal planning, weight tracking, an admin console, and camera capture
are possible extensions, not implemented features. The personalized RAG assistant is the
main addition to the referenced project concept.

No subjective “health score” is computed because there is no defined, validated scoring
method in the available material. Likewise, recognizing food is not enough to verify
ingredients, allergens, cooking oil, or portion volume.

## Technical sources used

- [TensorFlow MobileNetV2 API](https://www.tensorflow.org/api_docs/python/tf/keras/applications/MobileNetV2)
- [Flask upload handling](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Food-101 dataset and official split description](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/)

Use licensed research data and cite the original authors in the project report. The
current catalogue uses USDA FNDDS reference records with an explicit per-100 g basis;
see `nutrition-and-body-estimates.md`. Reference recipes must not be presented as
experimentally measured nutrition for arbitrary photographs.
