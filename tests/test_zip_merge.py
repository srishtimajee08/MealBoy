import hashlib
import io
import json
import zipfile

import pytest
from PIL import Image

from ml.merge_food_zip import merge


def test_merge_preserves_old_split_and_quarantines_new_leakage(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "VERIFIED").write_text("verified")
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "orange").save(buffer, format="JPEG")
    content = buffer.getvalue()
    old = [
        {
            "label": "garlic_bread",
            "split": "train",
            "path": "train/garlic_bread/a.jpg",
            "source": "old/a.jpg",
            "sha256": hashlib.sha256(content).hexdigest(),
            "pixel_sha256": "old-pixel",
            "dhash": "old-dhash",
        }
    ]
    (existing / "manifest.json").write_text(json.dumps(old))
    archive = tmp_path / "new.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("training/Bread/1.jpg", content)
        handle.writestr("evaluation/Bread/2.jpg", content)
        handle.writestr("../../escape.txt", "untrusted")
    destination = tmp_path / "new"
    merge(archive, existing, destination)
    rows = json.loads((destination / "manifest.json").read_text())
    assert {r["source_split"]: r["split"] for r in rows} == {"train": "train", "test": "review"}
    assert all(r["existing_overlap"] for r in rows)
    assert json.loads((existing / "manifest.json").read_text()) == old
    assert not (tmp_path / "escape.txt").exists()
    combined = json.loads((tmp_path / "combined_manifest.json").read_text())
    assert len(combined) == 3
    assert {r["task"] for r in combined} == {"food_dish", "food_category"}
    assert (destination / "VERIFIED").exists()
    with pytest.raises(ValueError, match="already exists"):
        merge(archive, existing, destination)
