"""Stable class IDs shared by model loading, folio generation, and SQLite."""

import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
BLOOM25_KEYS = ("camellia", "hydrangea", "plum-blossom", "peach-blossom", "lotus",
                "osmanthus", "tree-peony", "wisteria")
BLOOM30_KEYS = ("china-rose", "florist-chrysanthemum", "arabian-jasmine", "gardenia",
                "ivy-leaved-morning-glory")


def catalog(count=30, folder=KNOWLEDGE_DIR):
    if count not in (17, 25, 30):
        raise ValueError(f"Unsupported flower class count: {count}")
    classes = json.loads((folder / "classes.json").read_text(encoding="utf-8"))
    if [row["class_id"] for row in classes] != list(range(17)) or len({row["key"] for row in classes}) != 17:
        raise ValueError("Expected 17 Flower17 classes in ID order")
    if count == 17:
        return classes
    folios = json.loads((folder / "extra_folios.json").read_text(encoding="utf-8"))
    keys = BLOOM25_KEYS if count == 25 else BLOOM25_KEYS + BLOOM30_KEYS
    if set(keys) & {row["key"] for row in classes}:
        raise ValueError("Expanded classes reuse a Flower17 key")
    for key in keys:
        folio = folios[key]
        classes.append({"class_id": len(classes), "key": key, "name_zh": folio["name_zh"],
                        "name_en": folio["name_en"], "scientific_name": folio["profile"]["representative_name"]})
    return classes
