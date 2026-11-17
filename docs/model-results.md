# Local training and held-out evaluation

These results are generated from the completed local runs. They are not official Food-101 benchmark results: the supplied TAR contains 96 classes and uses a custom duplicate-grouped split.

| Task | Classes | Train | Validation | Test | Top-1 | Top-3 | Macro F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| food101 | 96 | 66,193 | 14,186 | 14,185 | 60.70% | 78.43% | 60.05% |
| food11 | 11 | 7,244 | 853 | 888 | 86.49% | 97.41% | 84.50% |

## Method

Both models use an ImageNet-initialized, frozen MobileNetV2 backbone and a separately trained softmax head. Inputs are EXIF-corrected RGB images resized to 224×224 with OpenCV bilinear interpolation. Scaling is embedded in each exported model. This run uses no augmentation or backbone fine-tuning.

Heads use Adam (0.001), dropout (0.3), L2 regularization (0.0001), batch size 256, seed 42, and at most 40 epochs. Early stopping selects minimum validation loss with patience 5. Test images are used only after training and operating-threshold selection. Shared image embeddings are cached by content hash; the two tasks retain separate label vocabularies.

The training records receive a full seeded random permutation before bounded per-epoch shuffling (4,096 records). A class-ordered shuffle trial was rejected using validation results before any test evaluation.

## Confidence and artifacts

Thresholds are selected on validation data for at least 90% observed accuracy among at least 100 accepted examples. This is an operating rule, not probability calibration or an unseen-food guarantee. The app requires user confirmation and marks lower-scoring predictions as uncertain.

### food101

Epochs run: 13; selected epoch: 8.
Confidence threshold: 0.67; test acceptance coverage: 41.83%; accuracy on accepted test images: 89.69%.

Median batched model inference time: 15.46 ms/image at batch size 32 on the local CPU. This excludes image decoding and is not end-to-end request latency.

Model SHA-256: `d6c9c4a326d236d955cba504ec34c64da0afaa945eff40a7b52527236131c567`.
Dataset manifest SHA-256: `abeff4012c794cc24e8117f4f09c81b1886ce753f7b76d714049b4c688e72916`.

![Training curves](../artifacts/food101/training_curves.png)
![Test confusion matrix](../reports/food101-evaluation/confusion_matrix.png)

[Per-class metrics](../reports/food101-evaluation/metrics.json), [individual predictions](../reports/food101-evaluation/predictions.jsonl), [configuration](../artifacts/food101/training_config.json).

### food11

Epochs run: 34; selected epoch: 29.
Confidence threshold: 0.65; test acceptance coverage: 85.59%; accuracy on accepted test images: 92.63%.

Median batched model inference time: 16.67 ms/image at batch size 32 on the local CPU. This excludes image decoding and is not end-to-end request latency.

Model SHA-256: `063dcc6d1053ffe32480933e01c57884782db3a5551f47b5ca95f2550d429353`.
Dataset manifest SHA-256: `4a8475c44e41fd2f265c65d0ff47bf9195d8d74ebd92b631597db5b3fb371e41`.

![Training curves](../artifacts/food11/training_curves.png)
![Test confusion matrix](../reports/food11-evaluation/confusion_matrix.png)

[Per-class metrics](../reports/food11-evaluation/metrics.json), [individual predictions](../reports/food11-evaluation/predictions.jsonl), [configuration](../artifacts/food11/training_config.json).

## Application and limitations

The 96-class dish model is installed as `artifacts/food_model.keras`. The 11-class category model remains a separate auxiliary artifact; broad categories cannot supply a specific dish's nutrition.

The catalogue contains 75 sourced USDA reference foods, covering 64 of the 96 dish labels. Unsupported labels require manual selection of a suitable reference. Nutrition is calculated from user-entered grams and per-100 g reference values, not inferred portion size or exact recipe composition.

Source labels can be noisy and some photos do not clearly depict food. Duplicate candidates and cross-source conflicts were grouped or quarantined, but perceptual matching cannot guarantee detection of every related image. Results describe these held-out partitions, not all cuisines, multi-food plates, real-world distribution shifts, or clinical accuracy. No test-set tuning was performed. The small pipeline smoke run is excluded.

Run `python tools/report_training.py` to regenerate this report after both evaluations complete. Local model, dataset, and report artifacts are gitignored.
