"""Write a reproducible report from completed held-out evaluations only."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def percent(value):
    return "not available" if value is None else f"{value:.2%}"


def main():
    lines = [
        "# Local training and held-out evaluation",
        "",
        "These results are generated from the completed local runs. They are not "
        "official Food-101 benchmark results: the supplied TAR contains 96 classes "
        "and uses a custom duplicate-grouped split.",
        "",
        "| Task | Classes | Train | Validation | Test | Top-1 | Top-3 | Macro F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    runs = []
    for task in ("food101", "food11"):
        artifacts = ROOT / "artifacts" / task
        evaluation = ROOT / "reports" / f"{task}-evaluation"
        marker = json.loads((evaluation / "progress.json").read_text())
        if marker["stage"] != "evaluation_complete":
            raise ValueError(f"Evaluation has not completed: {task}")
        config = json.loads((artifacts / "training_config.json").read_text())
        metrics = json.loads((evaluation / "metrics.json").read_text())
        labels = json.loads((artifacts / "labels.json").read_text())
        digest = hashlib.sha256((artifacts / "food_model.keras").read_bytes()).hexdigest()
        if digest != metrics["model_sha256"]:
            raise ValueError(f"Evaluated model no longer matches: {task}")
        runs.append((task, config, metrics))
        lines.append(
            f"| {task} | {len(labels)} | {config['train_samples']:,} | "
            f"{config['validation_samples']:,} | {metrics['test_samples']:,} | "
            f"{percent(metrics['accuracy'])} | {percent(metrics['top3_accuracy'])} | "
            f"{percent(metrics['macro avg']['f1-score'])} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            "Both models use an ImageNet-initialized, frozen MobileNetV2 backbone and "
            "a separately trained softmax head. Inputs are EXIF-corrected RGB images "
            "resized to 224×224 with OpenCV bilinear interpolation. Scaling is embedded "
            "in each exported model. This run uses no augmentation or backbone fine-tuning.",
            "",
            "Heads use Adam (0.001), dropout (0.3), L2 regularization (0.0001), "
            "batch size 256, seed 42, and at most 40 epochs. Early stopping selects "
            "minimum validation loss with patience 5. Test images are used only after "
            "training and operating-threshold selection. Shared image embeddings are "
            "cached by content hash; the two tasks retain separate label vocabularies.",
            "",
            "The training records receive a full seeded random permutation before "
            "bounded per-epoch shuffling (4,096 records). A class-ordered shuffle "
            "trial was rejected using validation results before any test evaluation.",
            "",
            "## Confidence and artifacts",
            "",
            "Thresholds are selected on validation data for at least 90% observed "
            "accuracy among at least 100 accepted examples. This is an operating rule, "
            "not probability calibration or an unseen-food guarantee. The app requires "
            "user confirmation and marks lower-scoring predictions as uncertain.",
        ]
    )
    for task, config, metrics in runs:
        lines.extend(
            [
                "",
                f"### {task}",
                "",
                f"Epochs run: {config['epochs_run']}; selected epoch: {config['best_epoch']}.",
                f"Confidence threshold: {metrics['confidence_threshold']:.2f}; "
                f"test acceptance coverage: {percent(metrics['accepted_coverage'])}; "
                f"accuracy on accepted test images: {percent(metrics['accepted_accuracy'])}.",
                "",
                f"Median batched model inference time: "
                f"{metrics['median_batch_inference_ms_per_image']:.2f} ms/image "
                f"at batch size {metrics['batch_size']} on the local CPU. This excludes "
                "image decoding and is not end-to-end request latency.",
                "",
                f"Model SHA-256: `{metrics['model_sha256']}`.",
                f"Dataset manifest SHA-256: `{config['dataset_manifest_sha256']}`.",
                "",
                f"![Training curves](../artifacts/{task}/training_curves.png)",
                f"![Test confusion matrix](../reports/{task}-evaluation/confusion_matrix.png)",
                "",
                f"[Per-class metrics](../reports/{task}-evaluation/metrics.json), "
                f"[individual predictions](../reports/{task}-evaluation/predictions.jsonl), "
                f"[configuration](../artifacts/{task}/training_config.json).",
            ]
        )
    lines.extend(
        [
            "",
            "## Application and limitations",
            "",
            "The 96-class dish model is installed as `artifacts/food_model.keras`. "
            "The 11-class category model remains a separate auxiliary artifact; broad "
            "categories cannot supply a specific dish's nutrition.",
            "",
            "The catalogue contains 75 sourced USDA reference foods, covering 64 of "
            "the 96 dish labels. Unsupported labels require manual selection of a "
            "suitable reference. Nutrition is calculated from user-entered grams and "
            "per-100 g reference values, not inferred portion size or exact recipe composition.",
            "",
            "Source labels can be noisy and some photos do not clearly depict food. "
            "Duplicate candidates and cross-source conflicts were grouped or quarantined, "
            "but perceptual matching cannot guarantee detection of every related image. "
            "Results describe these held-out partitions, not all cuisines, multi-food "
            "plates, real-world distribution shifts, or clinical accuracy. No test-set "
            "tuning was performed. The small pipeline smoke run is excluded.",
            "",
            "Run `python tools/report_training.py` to regenerate this report after both "
            "evaluations complete. Local model, dataset, and report artifacts are gitignored.",
        ]
    )
    target = ROOT / "docs/model-results.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
