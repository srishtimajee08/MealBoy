"""Run and log the complete local training/evaluation pipeline, then install the dish model."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    os.chdir(ROOT)
    temporary = ROOT / "artifacts/runtime-temp"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(temporary)
    os.environ["TMP"] = str(temporary)
    os.environ.setdefault("KERAS_HOME", str(ROOT / "artifacts/keras-cache"))
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts/matplotlib-cache"))
    logs = ROOT / "reports/training-run"
    logs.mkdir(parents=True, exist_ok=True)
    status_path = logs / "status.json"
    completed = []

    def status(stage, state, **extra):
        value = {
            "stage": stage,
            "state": state,
            "completed": completed,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        status_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        print(json.dumps(value), flush=True)

    for task in ("food101", "food11"):
        output = ROOT / "artifacts" / task
        marker = output / "progress.json"
        if marker.exists() and json.loads(marker.read_text()).get("stage") == "training_complete":
            completed.append("train_" + task)
            continue
        stage = "train_" + task
        status(stage, "running")
        command = [
            sys.executable,
            "-u",
            "ml/train_cached.py",
            f"datasets/{task}-prepared",
            "--output",
            f"artifacts/{task}",
        ]
        with (logs / f"{stage}.log").open("a", encoding="utf-8") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            status(stage, "failed", exit_code=result.returncode)
            return result.returncode
        completed.append(stage)

    for task in ("food101", "food11"):
        stage = "evaluate_" + task
        evaluation = ROOT / "reports" / f"{task}-evaluation"
        marker = evaluation / "progress.json"
        if marker.exists() and json.loads(marker.read_text()).get("stage") == "evaluation_complete":
            completed.append(stage)
            continue
        status(stage, "running")
        command = [
            sys.executable,
            "-u",
            "ml/evaluate.py",
            f"datasets/{task}-prepared/test",
            "--artifacts",
            f"artifacts/{task}",
            "--output",
            str(evaluation),
        ]
        with (logs / f"{stage}.log").open("a", encoding="utf-8") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            status(stage, "failed", exit_code=result.returncode)
            return result.returncode
        completed.append(stage)
    for name in ("food_model.keras", "labels.json", "confidence.json"):
        target = ROOT / "artifacts" / name
        source = ROOT / "artifacts/food101" / name
        if target.exists():
            if (
                hashlib.sha256(target.read_bytes()).digest()
                != hashlib.sha256(source.read_bytes()).digest()
            ):
                raise ValueError(f"Refusing to replace a different deployment artifact: {target}")
            continue
        shutil.copyfile(source, target)
    status("complete", "complete", deployed_model="artifacts/food_model.keras")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
