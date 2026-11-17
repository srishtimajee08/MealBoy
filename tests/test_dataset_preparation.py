import io
import json
import random
import tarfile

import pytest
from PIL import Image

from ml.prepare_archive import prepare


def test_archive_duplicates_and_unsafe_paths(tmp_path):
    archive = tmp_path / "input.tar"
    image = io.BytesIO()
    Image.new("RGB", (16, 16), "orange").save(image, format="JPEG")
    with tarfile.open(archive, "w") as handle:
        for name in (
            "food/images/pizza/a.jpg",
            "food/images/pizza/b.jpg",
            "food/images/waffles/c.jpg",
            "../../outside.txt",
        ):
            info = tarfile.TarInfo(name)
            info.size = len(image.getvalue())
            handle.addfile(info, io.BytesIO(image.getvalue()))
    destination = tmp_path / "prepared"
    prepare(archive, destination)
    manifest = json.loads((destination / "manifest.json").read_text())
    assert len(manifest) == 3
    assert {r["split"] for r in manifest} == {"review"}
    assert len({r["group"] for r in manifest}) == 1
    assert (destination / "VERIFIED").exists()
    assert not (tmp_path / "outside.txt").exists()
    summary = json.loads((destination / "summary.json").read_text())
    assert summary["byte_duplicate_extras"] == 2
    assert summary["rejected"] == 1
    with pytest.raises(ValueError, match="never overwritten"):
        prepare(archive, destination)


def test_split_is_reproducible_and_keeps_duplicates_together(tmp_path):
    rng = random.Random(12)
    archive = tmp_path / "foods.tar"
    with tarfile.open(archive, "w") as handle:
        for label in ("pizza", "waffles"):
            for i in range(20):
                buffer = io.BytesIO()
                Image.frombytes("RGB", (32, 32), rng.randbytes(32 * 32 * 3)).save(
                    buffer, format="JPEG"
                )
                for suffix in ("a", "b"):
                    member = tarfile.TarInfo(f"images/{label}/{i}{suffix}.jpg")
                    member.size = len(buffer.getvalue())
                    handle.addfile(member, io.BytesIO(buffer.getvalue()))
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        prepare(archive, output)
    assert (outputs[0] / "manifest.json").read_bytes() == (
        outputs[1] / "manifest.json"
    ).read_bytes()
    records = json.loads((outputs[0] / "manifest.json").read_text())
    for label in ("pizza", "waffles"):
        assert {r["split"] for r in records if r["label"] == label} == {"train", "val", "test"}
    for digest in {r["sha256"] for r in records}:
        assert len({r["split"] for r in records if r["sha256"] == digest}) == 1
