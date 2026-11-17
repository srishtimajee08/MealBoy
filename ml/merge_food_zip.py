"""Add a broad-category ZIP to the dataset collection without mixing label levels."""

import argparse
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps


def signatures(record):
    return [(key, record[key]) for key in ("sha256", "pixel_sha256", "dhash")]


def merge(archive, existing, destination):
    if destination.exists():
        raise ValueError("Destination already exists; existing datasets are never overwritten.")
    if not (existing / "VERIFIED").exists():
        raise ValueError("Existing dataset must be verified first.")
    old = json.loads((existing / "manifest.json").read_text())
    old_signatures = defaultdict(set)
    for record in old:
        for signature in signatures(record):
            old_signatures[signature].add(record["split"])
    records, rejected, parents, seen = [], [], [], {}

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive) as handle:
        for member in sorted(handle.infolist(), key=lambda entry: entry.filename):
            if member.is_dir():
                continue
            match = re.fullmatch(
                r"(training|validation|evaluation)/([^/]+)/[^/]+\.jpg", member.filename
            )
            if not match or member.file_size > 20_000_000:
                rejected.append({"source": member.filename, "reason": "unsupported path or size"})
                continue
            content = handle.read(member)
            try:
                with Image.open(io.BytesIO(content)) as image:
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    rgb = ImageOps.exif_transpose(image).convert("RGB")
                    rgb.load()
                    width, height = rgb.size
                    pixel_hash = hashlib.sha256(
                        f"{width},{height}:".encode() + rgb.tobytes()
                    ).hexdigest()
                    thumb = rgb.convert("L").resize((9, 8)).tobytes()
                    bits = [
                        thumb[y * 9 + x] > thumb[y * 9 + x + 1] for y in range(8) for x in range(8)
                    ]
                    dhash = f"{sum(int(bit) << i for i, bit in enumerate(bits)):016x}"
            except (ValueError, OSError, Image.DecompressionBombError) as error:
                rejected.append({"source": member.filename, "reason": str(error)})
                continue
            label = re.sub(r"[^a-z0-9]+", "_", match[2].lower()).strip("_")
            record = {
                "source": member.filename,
                "source_archive": str(archive.resolve()),
                "label": label,
                "original_label": match[2],
                "task": "food_category",
                "source_split": {"training": "train", "validation": "val", "evaluation": "test"}[
                    match[1]
                ],
                "sha256": hashlib.sha256(content).hexdigest(),
                "pixel_sha256": pixel_hash,
                "dhash": dhash,
                "width": width,
                "height": height,
            }
            i = len(records)
            parents.append(i)
            for signature in signatures(record):
                if signature in seen:
                    parents[root(i)] = root(seen[signature])
                else:
                    seen[signature] = i
            records.append(record)
            if len(records) % 2000 == 0:
                print(f"Validated {len(records)} ZIP images", flush=True)

        groups = defaultdict(list)
        for i in range(len(records)):
            groups[root(i)].append(i)
        for indices in groups.values():
            labels = {records[i]["label"] for i in indices}
            existing_splits = set()
            for i in indices:
                for signature in signatures(records[i]):
                    existing_splits.update(old_signatures.get(signature, set()))
            # Keep the old data fixed. New overlaps inherit its allowed partition;
            # otherwise evaluation takes precedence. Never move held-out images to train.
            preferred = next(
                (
                    s
                    for s in ("test", "val", "train")
                    if any(records[i]["source_split"] == s for i in indices)
                ),
                "review",
            )
            if existing_splits:
                preferred = next(iter(existing_splits)) if len(existing_splits) == 1 else "review"
            for i in indices:
                r = records[i]
                r["group"] = root(i)
                r["existing_overlap"] = bool(existing_splits)
                r["split"] = r["source_split"]
                if len(labels) > 1:
                    r.update(split="review", review_reason="conflicting category labels")
                elif preferred == "review" or r["source_split"] != preferred:
                    r.update(
                        split="review", review_reason="duplicate candidate crosses source splits"
                    )

        counters, counts, directories = Counter(), defaultdict(Counter), set()
        for i, record in enumerate(records):
            label, split = record["label"], record["split"]
            counters[label] += 1
            relative = Path(split) / label / f"{label}_img{counters[label]:05d}.jpg"
            target = destination / relative
            if target.parent not in directories:
                target.parent.mkdir(parents=True, exist_ok=True)
                directories.add(target.parent)
            content = handle.read(record["source"])
            target.write_bytes(content)
            if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"Copy verification failed: {target}")
            record["path"] = relative.as_posix()
            counts[label][split] += 1
            if (i + 1) % 2000 == 0:
                print(f"Saved and verified {i + 1} ZIP images", flush=True)

    # Check split separation across both tasks, excluding review-only images.
    combined_signatures = defaultdict(set)
    for record in old + records:
        if record["split"] != "review":
            for signature in signatures(record):
                combined_signatures[signature].add(record["split"])
    if any(len(splits) > 1 for splits in combined_signatures.values()):
        raise ValueError("Duplicate signature crosses usable partitions.")
    summary = {
        "archive": str(archive.resolve()),
        "valid_images": len(records),
        "rejected": len(rejected),
        "classes": len(counts),
        "task": "food_category",
        "split_totals": dict(Counter(r["split"] for r in records)),
        "counts": dict(counts),
        "existing_overlap_images": sum(r["existing_overlap"] for r in records),
        "byte_duplicate_extras": len(records) - len({r["sha256"] for r in records}),
        "pixel_duplicate_extras": len(records) - len({r["pixel_sha256"] for r in records}),
        "policy": (
            "Preserve supplied splits; quarantine conflicting labels or cross-split candidates."
        ),
        "limitations": "Folder labels unverified; equal dHash does not find all near duplicates.",
    }
    for name, value in (
        ("manifest.json", records),
        ("summary.json", summary),
        ("labels.json", sorted(counts)),
        ("rejected.json", rejected),
    ):
        (destination / name).write_text(json.dumps(value, indent=2), encoding="utf-8")
    (destination / "VERIFIED").write_text("Copied hashes and cross-dataset partitions verified.\n")
    collection = []
    for folder, task, entries in (
        (existing, "food_dish", old),
        (destination, "food_category", records),
    ):
        for r in entries:
            collection.append(dict(r, task=task, path=(folder.name + "/" + r["path"])))
    (destination.parent / "combined_manifest.json").write_text(
        json.dumps(collection, indent=2), encoding="utf-8"
    )
    (destination.parent / "collection.json").write_text(
        json.dumps(
            {
                "images": len(collection),
                "manifest": "combined_manifest.json",
                "path_base": "this directory",
                "datasets": [
                    {"path": existing.name, "task": "food_dish", "images": len(old)},
                    {"path": destination.name, "task": "food_category", "images": len(records)},
                ],
                "warning": (
                    "Separate training targets: do not flatten broad categories and dish labels."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "counts"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--existing", type=Path, default=Path("datasets/food101-prepared"))
    parser.add_argument("--destination", type=Path, default=Path("datasets/food11-prepared"))
    args = parser.parse_args()
    merge(args.archive, args.existing, args.destination)
