"""Check the deployed model through authenticated Flask uploads in an isolated database."""

import hashlib
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts/matplotlib-cache"))
    temporary = ROOT / "artifacts/runtime-temp"
    temporary.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(temporary)
    from mealboy import create_app

    metrics = json.loads((ROOT / "reports/food101-evaluation/metrics.json").read_text())
    model = ROOT / "artifacts/food_model.keras"
    assert hashlib.sha256(model.read_bytes()).hexdigest() == metrics["model_sha256"]
    labels = json.loads((ROOT / "artifacts/labels.json").read_text())
    assert len(labels) == 96
    chosen = {}
    with (ROOT / "reports/food101-evaluation/predictions.jsonl").open() as stream:
        for line in stream:
            record = json.loads(line)
            if record["actual"] in {"pizza", "beignets", "french_fries"}:
                chosen.setdefault(record["actual"], record)
    assert len(chosen) == 3
    results = []
    with tempfile.TemporaryDirectory(dir=ROOT / "reports", prefix="model-app-check-") as folder:
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "isolated-model-verification-only",
                "DATABASE": str(Path(folder) / "check.sqlite3"),
                "MODEL_PATH": str(model),
                "MODEL_LABELS_PATH": str(ROOT / "artifacts/labels.json"),
            }
        )
        client = app.test_client()
        client.get("/login")
        with client.session_transaction() as session:
            token = session["csrf_token"]
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "name": "Model Check",
                "email": "model@example.test",
                "password": "isolated-model-check-password",
            },
        )
        assert response.status_code == 302
        with client.session_transaction() as session:
            token = session["csrf_token"]
        for label, expected in chosen.items():
            path = Path(expected["path"])
            if not path.is_absolute():
                path = ROOT / path
            started = time.perf_counter()
            response = client.post(
                "/api/predict",
                data={
                    "csrf_token": token,
                    "image": (io.BytesIO(path.read_bytes()), path.name),
                },
            )
            elapsed = time.perf_counter() - started
            assert response.status_code == 200, response.get_json()
            payload = response.get_json()
            assert payload["needs_confirmation"] is True
            assert len(payload["predictions"]) == 3
            first = payload["predictions"][0]
            assert first["label"] == expected["predicted"]
            assert abs(first["confidence"] - expected["confidence"]) < 0.001
            assert payload["confidence_threshold"] == metrics["confidence_threshold"]
            results.append(
                {
                    "true_label": label,
                    "path": str(path),
                    "response": payload,
                    "request_seconds": round(elapsed, 3),
                    "note": "First request includes lazy TensorFlow/model loading.",
                }
            )
    output = ROOT / "reports/trained-app-verification.json"
    output.write_text(json.dumps({"passed": True, "checks": results}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
