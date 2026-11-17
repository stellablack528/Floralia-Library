"""Validate Oxford Flower17 partition 1 and build a reproducible image manifest.

Run from the project root with .venv/Scripts/python.exe src/prepare_flower17.py.
No images are copied or modified. The official test split is only indexed.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "knowledge" / "classes.json"
SPLITS = ROOT / "data" / "splits" / "datasplits.mat"
IMAGES = ROOT / "data" / "raw" / "jpg"
OUTPUT = ROOT / "data" / "processed" / "flower17_partition1.csv"


def main() -> None:
    classes = json.loads(CLASSES.read_text(encoding="utf-8"))
    assert len(classes) == 17
    assert [item["class_id"] for item in classes] == list(range(17))
    assert len({item["key"] for item in classes}) == 17

    mat = loadmat(SPLITS)
    memberships: dict[int, str] = {}
    counts: dict[str, Counter[int]] = {}
    for field, split, expected in (("trn1", "train", 680), ("val1", "val", 340), ("tst1", "test", 340)):
        ids = [int(value) for value in mat[field].ravel()]
        assert len(ids) == expected and len(set(ids)) == expected, field
        for image_id in ids:
            assert 1 <= image_id <= 1360, image_id
            assert image_id not in memberships, f"Image {image_id} occurs in multiple splits"
            memberships[image_id] = split
        counts[split] = Counter((image_id - 1) // 80 for image_id in ids)

    assert set(memberships) == set(range(1, 1361))
    assert all(counts["train"][i] == 40 for i in range(17))
    assert all(counts["val"][i] == 20 for i in range(17))
    assert all(counts["test"][i] == 20 for i in range(17))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("image_id", "relative_path", "class_id", "class_key", "split"))
        for image_id in range(1, 1361):
            path = IMAGES / f"image_{image_id:04d}.jpg"
            assert path.is_file(), path
            with Image.open(path) as image:
                image.verify()
            class_id = (image_id - 1) // 80
            writer.writerow((image_id, path.relative_to(ROOT).as_posix(), class_id, classes[class_id]["key"], memberships[image_id]))

    print(f"Wrote {OUTPUT}")
    print("Images: 1360 | classes: 17 | train: 680 | val: 340 | test: 340")
    print("Each class: 80 images (40 train, 20 val, 20 test); no split overlap")
    print("Example: image_0001.jpg -> class 0 Daffodil; image_0081.jpg -> class 1 Snowdrop")


if __name__ == "__main__":
    main()
