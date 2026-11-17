"""Write a readable audit and nutrition coverage report for the prepared archive."""

import json
from pathlib import Path


def report(dataset, output):
    summary = json.loads((dataset / "summary.json").read_text())
    catalogue = json.loads(Path("mealboy/data/foods.json").read_text())
    foods = {food["key"]: food for food in catalogue}
    lines = [
        "# Supplied Food-101 archive audit",
        "",
        f"Source: `{summary['archive']}` ({summary['archive_bytes']:,} bytes).",
        f"Decoded {summary['valid_images']:,} images across {summary['classes']} folder labels.",
        f"Rejected unreadable/unsupported files: {summary['rejected']}.",
        "",
        "## Preparation",
        "",
        "This archive contains images only, without official train/test metadata. "
        "It is a partial collection with a custom approximate 70/15/15 split (seed 42). "
        "Do not present its evaluation as the official Food-101 benchmark.",
        "",
        "Original files remain untouched. Prepared names follow `food_name_img0001.jpg`. "
        "`manifest.json` maps every output to its original TAR member, label, hashes and group. "
        "Matching byte hashes, decoded-pixel hashes and exact 64-bit dHash signatures "
        "are grouped before splitting. Cross-label groups go to `review/` and are excluded "
        "from training and evaluation. Matching dHash is a candidate signal, not proof "
        "of duplication. Other near duplicates may remain; manual review is still needed.",
        "",
        f"Split totals: `{json.dumps(summary['split_totals'])}`.",
        f"Byte duplicate extras: {summary['byte_duplicate_extras']}; "
        f"decoded-pixel duplicate extras: {summary['pixel_duplicate_extras']}.",
        f"Multi-image candidate groups: {summary['candidate_groups_with_multiple_images']}; "
        f"cross-label groups: {summary['cross_label_groups_for_review']}.",
        "",
        "## Label quality and nutrition",
        "",
        "Folder names are supplied labels, not independently verified annotations. "
        "The uploaded beignets examples include restaurant interiors (1367474.jpg, "
        "2741104.jpg), empty dishes (2541549.jpg), and a preparation counter (634889.jpg). "
        "These need manual review before reporting final model quality. "
        "They have not been silently relabelled or deleted.",
        "",
        "This dataset has no measured calories, macros, serving weights or ingredient "
        "amounts. Recognition and nutrition lookup remain separate. Existing catalogue "
        "matches below are illustrative references, not verified measurements. "
        "The earlier nutrition CSV still needs a documented serving basis before import. "
        "Dosa, idli and biryani cannot be learned from folders absent in this archive.",
        "",
        "| Class | Train | Validation | Test | Review | Nutrition catalogue |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for label, counts in sorted(summary["counts"].items()):
        values = " | ".join(
            str(counts.get(split, 0)) for split in ("train", "val", "test", "review")
        )
        status = "Illustrative only" if label in foods else "Missing"
        lines.append(f"| {label} | {values} | {status} |")
    lines += [
        "",
        "## Training and evaluation",
        "",
        "Training is a separate compute-intensive step. No accuracy is inferred from "
        "successful preparation. Use Python 3.12 with requirements-ml.txt installed.",
        "",
        "Run status (2026-11-05): dataset preparation completed with every copied file "
        "hash verified. All 96 classes appear in each usable split. Project tests: "
        "30 passed; dataset tests also passed after the directory-creation optimization. "
        "TensorFlow installation was attempted in .venv-ml but its download repeatedly "
        "disconnected and was stopped. This environment is incomplete. No model was "
        "trained and no accuracy results were produced during this preparation run.",
        "",
        "```powershell",
        r".venv-ml\Scripts\python ml/train.py datasets/food101-prepared --output artifacts/food101",
        r".venv-ml\Scripts\python ml/evaluate.py datasets/food101-prepared/test "
        "--artifacts artifacts/food101 --output reports/food101-evaluation",
        "```",
        "",
        "Training exports model weights, ordered labels, histories, training curves and "
        "a configuration containing the dataset manifest hash. Evaluation exports measured "
        "classification metrics and a confusion matrix. Keep test data out of model selection.",
        "",
        "After evaluation, set MODEL_PATH=artifacts/food101/food_model.keras and "
        "MODEL_LABELS_PATH=artifacts/food101/labels.json to use that model in the app.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    report(Path("datasets/food101-prepared"), Path("docs/food101-dataset.md"))
