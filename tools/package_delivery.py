"""Package only explicit application, model and evaluation deliverables."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    status = json.loads((ROOT / "reports/training-run/status.json").read_text())
    check = json.loads((ROOT / "reports/trained-app-verification.json").read_text())
    if status["state"] != "complete" or check["passed"] is not True:
        raise ValueError("Training, evaluation and application verification must complete first.")
    paths = set()
    for folder in ("mealboy", "ml", "tools", "tests", "docs"):
        paths.update(
            path
            for path in (ROOT / folder).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    for name in (
        "README.md",
        "DELIVERY.md",
        "app.py",
        "pyproject.toml",
        ".env.example",
        "requirements.txt",
        "requirements-ml.txt",
        "requirements-ml.lock.txt",
        "requirements-dev.txt",
        "setup_mealboy.ps1",
        "run_mealboy.ps1",
        "artifacts/food_model.keras",
        "artifacts/labels.json",
        "artifacts/confidence.json",
        "reports/nutrition_catalogue.json",
        "reports/trained-app-verification.json",
        "reports/training-run/status.json",
    ):
        paths.add(ROOT / name)
    for task in ("food101", "food11"):
        for name in (
            "food_model.keras",
            "labels.json",
            "confidence.json",
            "training_config.json",
            "head_history.csv",
            "training_curves.png",
        ):
            paths.add(ROOT / "artifacts" / task / name)
        for name in (
            "metrics.json",
            "confusion_matrix.csv",
            "confusion_matrix.png",
            "predictions.jsonl",
        ):
            paths.add(ROOT / "reports" / f"{task}-evaluation" / name)
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"Missing deliverables: {missing}")
    output = ROOT / "delivery"
    output.mkdir(exist_ok=True)
    archive = output / "MealBoy-delivery.zip"
    manifest = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(paths):
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            package.writestr("MealBoy/" + relative, data)
            manifest[relative] = hashlib.sha256(data).hexdigest()
        package.writestr("MealBoy/delivery-manifest.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "MealBoy-delivery.sha256").write_text(f"{digest}  {archive.name}\n")
    print(
        json.dumps(
            {
                "archive": str(archive),
                "files": len(manifest),
                "bytes": archive.stat().st_size,
                "sha256": digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
