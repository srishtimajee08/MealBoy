"""Train a readable two-stage MobileNetV2 transfer-learning baseline.

Dataset layout: dataset/{train,val,test}/{class_name}/*.jpg
Test data is never loaded here. Use evaluate.py once model selection is finished.
"""

import argparse
import hashlib
import json
from pathlib import Path


def train(dataset, output, epochs=10, fine_tune_epochs=5, batch_size=32):
    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)
    if (output / "food_model.keras").exists():
        raise ValueError("Use a new output directory to preserve the existing experiment.")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = dataset / "manifest.json"
    if (dataset / "summary.json").exists() and not (dataset / "VERIFIED").exists():
        raise ValueError("Dataset preparation is incomplete: missing VERIFIED marker.")
    training = tf.keras.utils.image_dataset_from_directory(
        dataset / "train",
        image_size=(224, 224),
        batch_size=batch_size,
        label_mode="int",
        seed=42,
    )
    labels = training.class_names
    if len(labels) < 2:
        raise ValueError("Training requires at least two classes.")
    validation = tf.keras.utils.image_dataset_from_directory(
        dataset / "val",
        image_size=(224, 224),
        batch_size=batch_size,
        label_mode="int",
        class_names=labels,
        shuffle=False,
    )
    training = training.prefetch(tf.data.AUTOTUNE)
    validation = validation.prefetch(tf.data.AUTOTUNE)

    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet"
    )
    backbone.trainable = False
    inputs = tf.keras.Input(shape=(224, 224, 3), name="rgb_pixels")
    augmented = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal", seed=42),
            tf.keras.layers.RandomRotation(0.08, seed=42),
            tf.keras.layers.RandomZoom(0.1, seed=42),
        ],
        name="augmentation",
    )(inputs)
    # This standard Keras layer is serialized in the model; inference must not scale again.
    normalized = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1, name="mobilenet_scaling")(
        augmented
    )
    features = backbone(normalized, training=False)  # Preserve batch-normalization statistics.
    features = tf.keras.layers.GlobalAveragePooling2D()(features)
    features = tf.keras.layers.Dropout(0.3)(features)
    outputs = tf.keras.layers.Dense(len(labels), activation="softmax", name="food_class")(features)
    model = tf.keras.Model(inputs, outputs)

    def compile_model(rate):
        model.compile(
            optimizer=tf.keras.optimizers.Adam(rate),
            loss="sparse_categorical_crossentropy",
            metrics=[
                "accuracy",
                tf.keras.metrics.SparseTopKCategoricalAccuracy(
                    k=min(3, len(labels)), name="top3_accuracy"
                ),
            ],
        )

    def callbacks(stage):
        return [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=3, restore_best_weights=True
            ),
            tf.keras.callbacks.CSVLogger(str(output / f"{stage}_history.csv")),
        ]

    compile_model(1e-3)
    histories = [
        model.fit(
            training, validation_data=validation, epochs=epochs, callbacks=callbacks("head")
        ).history
    ]
    head_loss = model.evaluate(validation, verbose=0)[0]
    model.save(output / "head_model.keras")

    if fine_tune_epochs:
        backbone.trainable = True
        for layer in backbone.layers[:-30]:
            layer.trainable = False
        for layer in backbone.layers:
            if isinstance(layer, tf.keras.layers.BatchNormalization):
                layer.trainable = False
        compile_model(1e-5)
        fine_history = model.fit(
            training,
            validation_data=validation,
            epochs=fine_tune_epochs,
            callbacks=callbacks("finetune"),
        )
        histories.append(fine_history.history)
        fine_loss = model.evaluate(validation, verbose=0)[0]
        if fine_loss > head_loss:
            model = tf.keras.models.load_model(output / "head_model.keras")
    model.save(output / "food_model.keras")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    for axis, metric in zip(axes, ("accuracy", "loss")):
        for prefix in ("", "val_"):
            values = [v for history in histories for v in history[prefix + metric]]
            axis.plot(range(1, len(values) + 1), values, label=prefix + metric)
        axis.set(xlabel="Epoch", ylabel=metric, title=f"Training and validation {metric}")
        axis.legend()
    figure.tight_layout()
    figure.savefig(output / "training_curves.png", dpi=160)
    plt.close(figure)
    (output / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (output / "training_config.json").write_text(
        json.dumps(
            {
                "architecture": "MobileNetV2",
                "tensorflow": tf.__version__,
                "seed": 42,
                "dataset": str(dataset.resolve()),
                "epochs": epochs,
                "fine_tune_epochs": fine_tune_epochs,
                "batch_size": batch_size,
                "input": "224x224 RGB float32 in [0,255]",
                "selection": "lowest validation loss; held-out test split not used",
                "dataset_manifest_sha256": (
                    hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                    if manifest_path.exists()
                    else None
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Exported model and label order to {output.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--fine-tune-epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.epochs < 1 or args.fine_tune_epochs < 0 or args.batch_size < 1:
        parser.error("Use positive epochs/batch size and nonnegative fine-tune epochs.")
    train(args.dataset, args.output, args.epochs, args.fine_tune_epochs, args.batch_size)
