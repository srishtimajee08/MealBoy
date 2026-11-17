"""Validated uploads and lazy loading of a trained MobileNetV2 classifier.

The training pipeline embeds MobileNetV2 scaling in the model itself.
Inference therefore supplies RGB float pixels in [0, 255], exactly as training does.
"""

import io
import json
import math
import threading
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ModelUnavailable(RuntimeError):
    pass


def validate_image(content):
    if not content:
        raise ValueError("Choose a JPEG, PNG or WebP image.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Only JPEG, PNG and WebP images are supported.")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Use an image smaller than 20 megapixels.")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                return ImageOps.exif_transpose(image).convert("RGB")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValueError("This image could not be read. Try a smaller JPEG or PNG.") from error


class FoodRecognizer:
    def __init__(self, model_path, labels_path):
        self.model_path = Path(model_path)
        self.labels_path = Path(labels_path)
        self._model = None
        self._labels = []
        self._lock = threading.Lock()
        self.confidence_threshold = 0.7

    @property
    def artifacts_present(self):
        return self.model_path.is_file() and self.labels_path.is_file()

    def _load_model(self):
        if not self.artifacts_present:
            raise ModelUnavailable(
                "The food model has not been trained yet. You can log a meal manually below."
            )
        try:
            import tensorflow as tf
        except ImportError as error:
            raise ModelUnavailable(
                "Install requirements-ml.txt to enable image recognition."
            ) from error
        try:
            labels = json.loads(self.labels_path.read_text(encoding="utf-8"))
            if (
                not isinstance(labels, list)
                or not labels
                or any(not isinstance(label, str) for label in labels)
            ):
                raise ValueError("Labels must be a nonempty list of class names.")
            model = tf.keras.models.load_model(self.model_path, compile=False, safe_mode=True)
            if model.output_shape[-1] != len(labels):
                raise ValueError("Model output and label count differ.")
            if tuple(model.input_shape[1:]) != (224, 224, 3):
                raise ValueError("Model input must have shape (224, 224, 3).")
            threshold_path = self.model_path.with_name("confidence.json")
            if threshold_path.exists():
                threshold = float(json.loads(threshold_path.read_text())["threshold"])
                if not math.isfinite(threshold) or not 0 <= threshold <= 1:
                    raise ValueError("Confidence threshold must be between 0 and 1.")
                self.confidence_threshold = threshold
            self._labels = labels
            self._model = model
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise ModelUnavailable(
                "Model artifacts are invalid. Check the training export."
            ) from error

    def predict(self, image):
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise ModelUnavailable(
                "Install requirements-ml.txt to enable image recognition."
            ) from error
        with self._lock:
            if self._model is None:
                self._load_model()
            pixels = cv2.resize(np.asarray(image), (224, 224), interpolation=cv2.INTER_LINEAR)
            probabilities = np.asarray(
                self._model(pixels.astype("float32")[None, ...], training=False)
            )[0]
            if not np.all(np.isfinite(probabilities)):
                raise ModelUnavailable("The model returned invalid predictions.")
            indices = np.argsort(probabilities)[-3:][::-1]
            return [
                {"label": self._labels[index], "confidence": round(float(probabilities[index]), 4)}
                for index in indices
            ]
