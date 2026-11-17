"""Prepare a licensed local Food-101 download without touching the official test split.

Usage: python ml/prepare_food101.py datasets/food-101 datasets/prepared
Optionally pass --classes pizza hamburger french_fries fried_rice for a small experiment.
"""

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path


def prepare(source, destination, classes=None):
    if destination.exists():
        raise ValueError("Choose a new output directory; existing datasets are never overwritten.")
    rng = random.Random(42)
    train_names = (source / "meta/train.txt").read_text().splitlines()
    test_names = (source / "meta/test.txt").read_text().splitlines()
    available = sorted({name.split("/")[0] for name in train_names})
    selected = classes or available
    if len(set(selected)) < 2 or set(selected) - set(available):
        raise ValueError("Choose at least two distinct Food-101 class names from meta/classes.txt.")
    manifest = {"seed": 42, "source": "Food-101 official splits", "files": []}
    seen_hashes = {}
    for class_name in selected:
        training = [name for name in train_names if name.startswith(class_name + "/")]
        rng.shuffle(training)
        validation_size = max(1, round(len(training) * 0.2))
        partitions = {
            "val": training[:validation_size],
            "train": training[validation_size:],
            "test": [name for name in test_names if name.startswith(class_name + "/")],
        }
        for split, names in partitions.items():
            target = destination / split / class_name
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                image_path = source / "images" / f"{name}.jpg"
                digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
                if digest in seen_hashes and seen_hashes[digest] != split:
                    raise ValueError(f"Duplicate image across splits: {name}. Review the dataset.")
                seen_hashes[digest] = split
                shutil.copyfile(image_path, target / image_path.name)
                manifest["files"].append({"path": name, "split": split, "sha256": digest})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(manifest['files'])} images across {len(selected)} classes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--classes", nargs="+")
    args = parser.parse_args()
    prepare(args.source, args.destination, args.classes)
