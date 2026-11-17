"""Evaluate the frozen model once on held-out images, using deployment preprocessing."""

import argparse
import hashlib
import json
import time
from pathlib import Path


def evaluate(test_directory, artifacts, output, batch_size=32):
    import cv2
    import matplotlib
    import numpy as np
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageOps

    tf.config.threading.set_intra_op_parallelism_threads(6)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    labels = json.loads((artifacts / "labels.json").read_text())
    model = tf.keras.models.load_model(artifacts / "food_model.keras", compile=False)

    @tf.function(reduce_retracing=True)
    def infer_batch(pixels):
        return model(pixels, training=False)

    actual, predicted, top_three, latencies, confidences = [], [], [], [], []
    samples = []
    for index, label in enumerate(labels):
        images = sorted(
            path
            for path in (test_directory / label).glob("*")
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        if not images:
            raise ValueError(f"No test images for class {label}.")
        samples.extend((path, index) for path in images)
    output.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(samples), batch_size):
        batch = samples[start : start + batch_size]
        pixels = []
        for path, index in batch:
            with Image.open(path) as image:
                rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
            pixels.append(cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_LINEAR))
        started = time.perf_counter()
        batch_scores = np.asarray(infer_batch(np.asarray(pixels, dtype="float32")))
        latencies.append((time.perf_counter() - started) / len(batch))
        for (_, index), scores in zip(batch, batch_scores):
            actual.append(index)
            predicted.append(int(np.argmax(scores)))
            top_three.append(index in np.argsort(scores)[-min(3, len(labels)) :])
            confidences.append(float(scores.max()))
        if start == 0 or (start + batch_size) % (batch_size * 20) == 0:
            progress = {"stage": "test_evaluation", "completed": len(actual), "total": len(samples)}
            (output / "progress.json").write_text(json.dumps(progress))
            print(json.dumps(progress), flush=True)
    report = classification_report(
        actual,
        predicted,
        labels=list(range(len(labels))),
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )
    report["top3_accuracy"] = float(np.mean(top_three))
    report["median_batch_inference_ms_per_image"] = float(np.median(latencies) * 1000)
    report["batch_size"] = batch_size
    report["test_samples"] = len(actual)
    report["model_sha256"] = hashlib.sha256(
        (artifacts / "food_model.keras").read_bytes()
    ).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    confidence_path = artifacts / "confidence.json"
    if confidence_path.exists():
        threshold = json.loads(confidence_path.read_text())["threshold"]
        accepted = np.asarray(confidences) >= threshold
        report["confidence_threshold"] = threshold
        report["accepted_coverage"] = float(accepted.mean())
        report["accepted_accuracy"] = (
            float((np.asarray(actual)[accepted] == np.asarray(predicted)[accepted]).mean())
            if accepted.any()
            else None
        )
    (output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    matrix = confusion_matrix(actual, predicted, labels=list(range(len(labels))))
    np.savetxt(output / "confusion_matrix.csv", matrix, delimiter=",", fmt="%d")
    figure, axis = plt.subplots(figsize=(max(8, len(labels) * 0.3), max(6, len(labels) * 0.3)))
    image = axis.imshow(matrix, cmap="Greens")
    if len(labels) <= 25:
        axis.set_xticks(range(len(labels)), labels=labels, rotation=90)
        axis.set_yticks(range(len(labels)), labels=labels)
    axis.set(xlabel="Predicted class", ylabel="Actual class", title="Held-out confusion matrix")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(output / "confusion_matrix.png", dpi=160)
    plt.close(figure)
    with (output / "predictions.jsonl").open("w", encoding="utf-8") as stream:
        for (path, truth), guess, score in zip(samples, predicted, confidences):
            stream.write(
                json.dumps(
                    {
                        "path": str(path),
                        "actual": labels[truth],
                        "predicted": labels[guess],
                        "confidence": score,
                    }
                )
                + "\n"
            )
    (output / "progress.json").write_text(json.dumps({"stage": "evaluation_complete"}))
    print(
        json.dumps(
            {key: report[key] for key in ("accuracy", "top3_accuracy", "test_samples")}, indent=2
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test_directory", type=Path)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    evaluate(args.test_directory, args.artifacts, args.output, args.batch_size)
