"""Validate and export the Flower17 knowledge base for the Web library."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
classes = json.loads((KNOWLEDGE / "classes.json").read_text(encoding="utf-8"))
profiles = json.loads((KNOWLEDGE / "botanical_profiles.json").read_text(encoding="utf-8"))
sources = json.loads((KNOWLEDGE / "cultural_sources.json").read_text(encoding="utf-8"))
culture = defaultdict(list)
for record in sources["verified_items"]:
    culture[record["class_key"]].append(record)

class_keys = {item["key"] for item in classes}
if [item["class_id"] for item in classes] != list(range(17)) or len(class_keys) != 17:
    raise ValueError("Expected all 17 Flower17 class IDs and unique keys in dataset order")
for name, records in (("botanical profiles", profiles), ("cultural records", culture)):
    missing, unknown = class_keys - records.keys(), records.keys() - class_keys
    if missing or unknown:
        raise ValueError(f"Invalid {name}: missing {sorted(missing)}, unknown {sorted(unknown)}")


def require_text(record: dict, fields: tuple[str, ...], context: str) -> None:
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"{context}: {field} must be nonempty text")


def require_source(record: dict, context: str) -> None:
    require_text(record, ("title", "publisher", "url"), context)
    url = urlsplit(record["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError(f"{context}: expected a public HTTPS source URL")

cards = []
for item in classes:
    key = item["key"]
    profile = profiles[key]
    records = culture[key]
    require_text(profile, ("representative_name", "family", "genus", "habitat", "flowering", "scope"), key)
    traits = profile["traits"]
    if len(traits) < 2 or not all(isinstance(trait, str) and trait.strip() for trait in traits):
        raise ValueError(f"{key}: expected at least two visible traits")
    if not profile["references"]:
        raise ValueError(f"{key}: expected a botanical source")
    for source in profile["references"]:
        require_source(source, key)
    for record in records:
        require_source(record, key)
        require_text(record, ("kind", "theme", "creator", "locator", "our_summary", "scope", "checked_on"), key)
    cards.append(
        {
            "class_id": item["class_id"],
            "order": item["class_id"] + 1,
            "key": key,
            "zh": item["name_zh"],
            "en": item["name_en"],
            "latin": profile["representative_name"],
            "family": profile["family"],
            "genus": profile["genus"],
            "traits": traits,
            "habitat": profile["habitat"],
            "season": profile["flowering"],
            "note": profile["scope"],
            "sources": profile["references"],
            "culture": [{field: value for field, value in record.items() if field != "class_key"} for record in records],
        }
    )

prefix = """/* Generated from knowledge/classes.json, botanical_profiles.json and cultural_sources.json.
   Edit those source files, then run src/sync_web_cards.py. */
window.FF = window.FF || {};
FF.data = { flowers: """
suffix = """ };
FF.data.byKey = function (key) {
  return this.flowers.find(f => f.key === key) || null;
};
/* UI-only demo. This is not a trained flower classifier. */
FF.data.demoIdentify = function (byteSum, byteMod) {
  const idx = (byteSum * 7 + byteMod * 13) % this.flowers.length;
  const primary = this.flowers[idx];
  const second = this.flowers[(idx + 5 + byteMod % 4) % this.flowers.length];
  const third = this.flowers[(idx + 11 + byteSum % 3) % this.flowers.length];
  const p1 = 62 + (byteSum % 31);
  const rest = 100 - p1;
  const p2 = Math.max(2, Math.round(rest * ((byteMod % 5 + 3) / 10)));
  const p3 = Math.max(1, rest - p2);
  return [
    { flower: primary, score: p1 },
    { flower: second, score: p2 },
    { flower: third, score: p3 }
  ];
};
"""
js_dir = ROOT / "web" / "js" if (ROOT / "web" / "js").is_dir() else ROOT / "js"
output = js_dir / "data.js"
output.write_text(prefix + json.dumps(cards, ensure_ascii=False, indent=2) + suffix, encoding="utf-8")
print(f"Updated {output} with {len(cards)} classes")
