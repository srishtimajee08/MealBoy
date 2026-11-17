"""Prepare the supplied image-only TAR with reproducible, duplicate-grouped splits.

No extractall: archive paths are never used as filesystem destinations.
Original bytes and folder labels are retained; the manifest records renamed images.
"""

import argparse
import hashlib
import io
import json
import random
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps


def prepare(archive, destination):
    if destination.exists():
        raise ValueError("Choose a new output directory; existing data is never overwritten.")
    destination.mkdir(parents=True)
    staging = destination / "staging"
    staging.mkdir()
    records, rejected = [], []
    parents, signatures = [], {}

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    with tarfile.open(archive, "r|*") as handle:
        for member in handle:
            if not member.isfile():
                continue
            match = re.fullmatch(r"(?:[^/]+/)*images/([a-z0-9_]+)/([^/]+\.jpg)", member.name)
            if not match or member.size > 20_000_000:
                rejected.append({"source": member.name, "reason": "unsupported path or size"})
                continue
            content = handle.extractfile(member).read()
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
                    thumb = list(rgb.convert("L").resize((9, 8)).tobytes())
                    bits = [
                        thumb[y * 9 + x] > thumb[y * 9 + x + 1] for y in range(8) for x in range(8)
                    ]
                    dhash = f"{sum(int(bit) << i for i, bit in enumerate(bits)):016x}"
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                rejected.append({"source": member.name, "reason": str(error)})
                continue
            index = len(records)
            parents.append(index)
            digest = hashlib.sha256(content).hexdigest()
            # Matching perceptual signatures are conservative candidate groups, not proof
            # of duplication. Grouping prevents these candidates crossing partitions.
            for signature in ("bytes:" + digest, "pixels:" + pixel_hash, "dhash:" + dhash):
                if signature in signatures:
                    parents[root(index)] = root(signatures[signature])
                else:
                    signatures[signature] = index
            (staging / f"{index}.jpg").write_bytes(content)
            records.append(
                {
                    "source": member.name,
                    "label": match[1],
                    "sha256": digest,
                    "pixel_sha256": pixel_hash,
                    "dhash": dhash,
                    "width": width,
                    "height": height,
                }
            )
            if len(records) % 5000 == 0:
                print(f"Validated {len(records)} images", flush=True)

    groups = defaultdict(list)
    for i in range(len(records)):
        groups[root(i)].append(i)
    by_class = defaultdict(list)
    conflicts = []
    for group, indices in groups.items():
        labels = {records[i]["label"] for i in indices}
        if len(labels) > 1:
            conflicts.append(group)
        else:
            by_class[next(iter(labels))].append(group)
    assignments = {group: "review" for group in conflicts}
    rng = random.Random(42)
    for label in sorted(by_class):
        candidates = sorted(by_class[label])
        rng.shuffle(candidates)
        total = sum(len(groups[g]) for g in candidates)
        targets = {"train": total * 0.70, "val": total * 0.15, "test": total * 0.15}
        counts = Counter()
        for group in candidates:
            split = max(targets, key=lambda key: targets[key] - counts[key])
            assignments[group] = split
            counts[split] += len(groups[group])

    counters = Counter()
    counts = defaultdict(Counter)
    created_directories = set()
    for i, record in enumerate(records):
        group = root(i)
        split, label = assignments[group], record["label"]
        counters[label] += 1
        relative = Path(split) / label / f"{label}_img{counters[label]:04d}.jpg"
        target = destination / relative
        if target.parent not in created_directories:
            target.parent.mkdir(parents=True, exist_ok=True)
            created_directories.add(target.parent)
        (staging / f"{i}.jpg").rename(target)
        record.update(path=relative.as_posix(), split=split, group=group)
        counts[label][split] += 1
        if (i + 1) % 5000 == 0:
            print(f"Placed {i + 1} images into splits", flush=True)
    staging.rmdir()
    labels = sorted(counts)
    summary = {
        "archive": str(archive.resolve()),
        "archive_bytes": archive.stat().st_size,
        "seed": 42,
        "split": "custom approximate 70/15/15; no official metadata supplied",
        "classes": len(labels),
        "valid_images": len(records),
        "rejected": len(rejected),
        "split_totals": dict(Counter(r["split"] for r in records)),
        "byte_duplicate_extras": len(records) - len({r["sha256"] for r in records}),
        "pixel_duplicate_extras": len(records) - len({r["pixel_sha256"] for r in records}),
        "candidate_groups_with_multiple_images": sum(len(g) > 1 for g in groups.values()),
        "cross_label_groups_for_review": len(conflicts),
        "counts": dict(counts),
        "limitations": [
            "Folder labels have not all been manually verified.",
            "Equal dHash grouping does not detect every near duplicate.",
            "Cross-label signature matches are excluded into review/.",
            "Images contain no ground-truth serving weights or nutrition.",
        ],
    }
    for filename, value in (
        ("manifest.json", records),
        ("summary.json", summary),
        ("labels.json", labels),
        ("rejected.json", rejected),
    ):
        (destination / filename).write_text(json.dumps(value, indent=2), encoding="utf-8")
    # Verify group separation and copied-byte integrity before declaring completion.
    for indices in groups.values():
        assert len({records[i]["split"] for i in indices}) == 1
    for record in records:
        assert (
            hashlib.sha256((destination / record["path"]).read_bytes()).hexdigest()
            == (record["sha256"])
        )
    (destination / "VERIFIED").write_text("All file hashes and group partitions verified.\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "counts"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.archive, args.destination)
