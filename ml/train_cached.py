"""CPU transfer learning: resumable MobileNetV2 features and a trained softmax head.

The backbone is frozen. No fine-tuning or image augmentation is claimed. The shared
SQLite cache reuses identical image bytes across tasks, never their target labels.
Only train and validation partitions are read here; evaluate.py handles test data.
"""

import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path


def train(dataset, output, cache, epochs=40, batch_size=32, threads=6):
    import cv2
    import numpy as np
    import tensorflow as tf
    from PIL import Image, ImageOps

    tf.config.threading.set_intra_op_parallelism_threads(threads)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    tf.keras.utils.set_random_seed(42)
    if (output / "food_model.keras").exists():
        raise ValueError("Use a new output directory to preserve a trained model.")
    if not (dataset / "VERIFIED").exists():
        raise ValueError("Dataset has not completed verification.")
    output.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (dataset / "manifest.json").read_bytes()
    records = json.loads(manifest_bytes)
    labels = sorted({r["label"] for r in records if r["split"] == "train"})
    label_index = {label: i for i, label in enumerate(labels)}
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet", pooling="avg"
    )
    backbone.trainable = False
    inputs = tf.keras.Input((224, 224, 3), name="rgb_pixels")
    features = backbone(tf.keras.layers.Rescaling(1 / 127.5, offset=-1)(inputs), training=False)
    extractor = tf.keras.Model(inputs, features)

    @tf.function(reduce_retracing=True)
    def extract_batch(pixels):
        return extractor(pixels, training=False)

    fingerprint = hashlib.sha256()
    for weight in backbone.get_weights():
        fingerprint.update(weight.tobytes())
    signature = fingerprint.hexdigest() + ":pil-exif-rgb-opencv-linear-224-v1"
    cache.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(cache)
    connection.execute("CREATE TABLE IF NOT EXISTS metadata (signature TEXT PRIMARY KEY)")
    saved = connection.execute("SELECT signature FROM metadata").fetchall()
    if saved and saved != [(signature,)]:
        raise ValueError("Feature cache belongs to different weights or preprocessing.")
    connection.execute("INSERT OR IGNORE INTO metadata VALUES (?)", (signature,))
    connection.execute("CREATE TABLE IF NOT EXISTS features (sha256 TEXT PRIMARY KEY, value BLOB)")
    connection.commit()

    def extract(split):
        selected = sorted((r for r in records if r["split"] == split), key=lambda r: r["path"])
        if {r["label"] for r in selected} != set(labels):
            raise ValueError(f"Class mismatch in {split}")
        x = np.empty((len(selected), 1280), dtype="float32")
        y = np.array([label_index[r["label"]] for r in selected], dtype="int32")
        started = time.monotonic()
        for start in range(0, len(selected), batch_size):
            chunk = selected[start : start + batch_size]
            missing, pixels = [], []
            for offset, record in enumerate(chunk):
                cached = connection.execute(
                    "SELECT value FROM features WHERE sha256=?", (record["sha256"],)
                ).fetchone()
                if cached:
                    x[start + offset] = np.frombuffer(cached[0], dtype="float32")
                else:
                    path = dataset / record["path"]
                    content = path.read_bytes()
                    if hashlib.sha256(content).hexdigest() != record["sha256"]:
                        raise ValueError(f"Image changed since preparation: {path}")
                    with Image.open(path) as image:
                        rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
                    pixels.append(cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_LINEAR))
                    missing.append((offset, record["sha256"]))
            if missing:
                values = np.asarray(extract_batch(np.asarray(pixels, dtype="float32")))
                for (offset, digest), value in zip(missing, values):
                    x[start + offset] = value
                    connection.execute(
                        "INSERT OR IGNORE INTO features VALUES (?, ?)",
                        (digest, value.astype("float32").tobytes()),
                    )
                connection.commit()
            done = min(start + batch_size, len(selected))
            if start == 0 or done % (batch_size * 20) == 0 or done == len(selected):
                progress = {
                    "stage": "extract_" + split,
                    "completed": done,
                    "total": len(selected),
                    "elapsed_seconds": round(time.monotonic() - started),
                }
                (output / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
                print(json.dumps(progress), flush=True)
        return x, y

    x_train, y_train = extract("train")
    x_val, y_val = extract("val")
    connection.close()
    # Cached records are sorted by class/path. Mix the entire population before
    # using a bounded epoch shuffle, otherwise batches remain class-local.
    order = np.random.default_rng(42).permutation(len(y_train))
    x_train, y_train = x_train[order], y_train[order]
    head = tf.keras.Sequential(
        [
            tf.keras.Input((1280,)),
            tf.keras.layers.Dropout(0.3, seed=42),
            tf.keras.layers.Dense(
                len(labels), activation="softmax", kernel_regularizer=tf.keras.regularizers.L2(1e-4)
            ),
        ],
        name="food_classifier",
    )
    head.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    options = tf.data.Options()
    options.threading.private_threadpool_size = 2
    training = (
        tf.data.Dataset.from_tensor_slices((x_train, y_train))
        .shuffle(min(4096, len(y_train)), seed=42)
        .batch(256)
        .with_options(options)
    )
    validation = tf.data.Dataset.from_tensor_slices((x_val, y_val)).batch(256).with_options(options)
    history = head.fit(
        training,
        validation_data=validation,
        epochs=epochs,
        shuffle=False,
        verbose=2,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=5, restore_best_weights=True
            ),
            tf.keras.callbacks.ModelCheckpoint(
                str(output / "best_head.keras"), monitor="val_loss", save_best_only=True
            ),
            tf.keras.callbacks.CSVLogger(str(output / "head_history.csv")),
        ],
    )
    model = tf.keras.Model(inputs, head(features), name="mealboy_mobilenetv2")
    model.save(output / "food_model.keras")
    (output / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    scores = np.asarray(head.predict(validation.map(lambda x, y: x), verbose=0))
    # Validation-only uncertainty threshold; require >=90% observed precision and
    # >=100 accepted examples. A threshold of 1 signals no qualifying operating point.
    confidence, correct = scores.max(axis=1), scores.argmax(axis=1) == y_val
    candidates = []
    for threshold in np.arange(0.30, 1.00, 0.01):
        accepted = confidence >= threshold
        if accepted.sum() >= 100 and correct[accepted].mean() >= 0.90:
            candidates.append(float(threshold))
    threshold = round(min(candidates), 2) if candidates else 1.0
    (output / "confidence.json").write_text(
        json.dumps(
            {
                "threshold": threshold,
                "source": "validation only",
                "target_precision": 0.90,
                "minimum_accepted": 100,
                "qualifying_threshold_found": bool(candidates),
                "note": "Scores are uncalibrated; no guarantee on unseen foods.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    config = {
        "architecture": "MobileNetV2",
        "method": "frozen ImageNet backbone + softmax head",
        "augmentation": "none",
        "fine_tuning": False,
        "seed": 42,
        "shuffle_buffer": min(4096, len(y_train)),
        "initial_order": "full seeded permutation before bounded epoch shuffle",
        "tensorflow": tf.__version__,
        "dataset": str(dataset.resolve()),
        "dataset_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "feature_signature": signature,
        "train_samples": len(y_train),
        "validation_samples": len(y_val),
        "epochs_run": len(history.history["loss"]),
        "best_epoch": int(np.argmin(history.history["val_loss"])) + 1,
        "input": "224x224 RGB float32 [0,255]; embedded MobileNet scaling",
        "selection": "minimum validation loss; test images not loaded",
    }
    (output / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for axis, metric in zip(axes, ("accuracy", "loss")):
        for prefix in ("", "val_"):
            axis.plot(
                range(1, len(history.history[metric]) + 1),
                history.history[prefix + metric],
                label=prefix + metric,
            )
        axis.set(xlabel="Epoch", ylabel=metric)
        axis.legend()
    fig.tight_layout()
    fig.savefig(output / "training_curves.png", dpi=160)
    plt.close(fig)
    (output / "progress.json").write_text(json.dumps({"stage": "training_complete"}))
    print(json.dumps(config, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/features.sqlite3"))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    train(args.dataset, args.output, args.cache, args.epochs, args.batch_size, args.threads)
