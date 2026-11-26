"""Validate and export the botanical folios for the Web library."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from flower_catalog import catalog


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
classes = json.loads((KNOWLEDGE / "classes.json").read_text(encoding="utf-8"))
extra_folios = json.loads((KNOWLEDGE / "extra_folios.json").read_text(encoding="utf-8"))
english_folios = json.loads((KNOWLEDGE / "folio_english.json").read_text(encoding="utf-8"))
profiles = json.loads((KNOWLEDGE / "botanical_profiles.json").read_text(encoding="utf-8"))
sources = json.loads((KNOWLEDGE / "cultural_sources.json").read_text(encoding="utf-8"))
flower_language = json.loads((KNOWLEDGE / "flower_language.json").read_text(encoding="utf-8"))
PUBLISHED_READING_KINDS = {
    "诗歌", "童话", "史诗与名字", "小说", "小说与名字", "诗歌与名字",
    "戏剧", "戏剧与象征", "宋诗", "散文", "宋词", "唐诗", "神话", "林地传说", "用物史",
}
culture = defaultdict(list)
for record in sources["verified_items"]:
    culture[record["class_key"]].append(record)

class_keys = {item["key"] for item in classes}
if [item["class_id"] for item in classes] != list(range(17)) or len(class_keys) != 17:
    raise ValueError("Expected all 17 Flower17 class IDs and unique keys in dataset order")
folio_keys = class_keys | extra_folios.keys()
if english_folios.keys() != folio_keys:
    raise ValueError("Every folio must have English content")
if flower_language["entries"].keys() != folio_keys:
    raise ValueError("Every folio must have exactly one flower-language entry")
if class_keys & extra_folios.keys() or any(not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", key) for key in extra_folios):
    raise ValueError("Additional folio keys must be unique and use lowercase words separated by hyphens")
for name, records in (("botanical profiles", profiles), ("cultural records", culture)):
    missing, unknown = class_keys - records.keys(), records.keys() - class_keys
    if missing or unknown:
        raise ValueError(f"Invalid {name}: missing {sorted(missing)}, unknown {sorted(unknown)}")


def require_text(record: dict, fields: tuple[str, ...], context: str) -> None:
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"{context}: {field} must be nonempty text")


def require_https(value: str, context: str) -> None:
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError(f"{context}: expected a public HTTPS source URL")


def require_source(record: dict, context: str) -> None:
    require_text(record, ("title", "publisher", "url"), context)
    require_https(record["url"], context)


for source_key, source in flower_language["sources"].items():
    require_source(source, source_key)
for key, meaning in flower_language["entries"].items():
    require_text(meaning, ("zh", "en", "source", "locator"), key)
    if meaning["source"] not in flower_language["sources"]:
        raise ValueError(f"{key}: unknown flower-language source")
    if "note" in meaning:
        require_text(meaning["note"], ("zh", "en"), key)


def make_card(key: str, item: dict, profile: dict, records: list, order: int) -> dict:
    require_text(item, ("name_zh", "name_en"), key)
    require_text(profile, ("representative_name", "family", "genus", "habitat", "flowering", "scope"), key)
    traits = profile["traits"]
    if len(traits) < 2 or not all(isinstance(trait, str) and trait.strip() for trait in traits):
        raise ValueError(f"{key}: expected at least two visible traits")
    if not profile["references"]:
        raise ValueError(f"{key}: expected a botanical source")
    for source in profile["references"]:
        require_source(source, key)
    if "comparison" in profile:
        require_text(profile, ("comparison",), key)
    english = english_folios[key]
    require_text(english, ("family", "habitat", "season", "note"), key)
    if "comparison" in english:
        require_text(english, ("comparison",), key)
    if len(english["culture"]) != len(records) or len(english["traits"]) != len(traits):
        raise ValueError(f"{key}: English traits and cultural records must match the folio")
    published = []
    english_culture = []
    for record, translation in zip(records, english["culture"], strict=True):
        if record["kind"] not in PUBLISHED_READING_KINDS:
            continue
        require_source(record, key)
        require_text(record, ("kind", "theme", "creator", "locator", "our_summary", "scope", "checked_on"), key)
        if "excerpt" in record or "excerpt_language" in record:
            require_text(record, ("excerpt",), key)
            if "excerpt_language" in record:
                require_text(record, ("excerpt_language",), key)
        published.append({field: value for field, value in record.items() if field != "class_key"})
        english_culture.append(translation)
    meaning = flower_language["entries"][key]
    return {
        "class_id": item.get("class_id"),
        "order": order,
        "key": key,
        "zh": item["name_zh"],
        "en": item["name_en"],
        **({"aliases": item["aliases"]} if "aliases" in item else {}),
        "latin": profile["representative_name"],
        "family": profile["family"],
        "genus": profile["genus"],
        "traits": traits,
        "habitat": profile["habitat"],
        "season": profile["flowering"],
        "note": profile["scope"],
        **({"comparison": profile["comparison"]} if "comparison" in profile else {}),
        "sources": profile["references"],
        "culture": published,
        "flower_language": {**meaning, "source": flower_language["sources"][meaning["source"]]},
        "english": {
            **{field: english[field] for field in ("family", "habitat", "season", "note", "traits")},
            **({"comparison": english["comparison"]} if "comparison" in english else {}),
            "culture": english_culture,
        },
    }


cards = [
    make_card(item["key"], item, profiles[item["key"]], culture[item["key"]], order)
    for order, item in enumerate(classes, start=1)
]
for order, (key, item) in enumerate(extra_folios.items(), start=len(cards) + 1):
    if "class_id" in item:
        raise ValueError(f"{key}: a library-only folio must not declare a model class ID")
    aliases = item.get("aliases", [])
    if not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias.strip() for alias in aliases):
        raise ValueError(f"{key}: aliases must be a list of nonempty names")
    cards.append(make_card(key, item, item["profile"], item["culture"], order))

class_ids = {item["key"]: item["class_id"] for item in catalog()}
for card in cards:
    card["class_id"] = class_ids.get(card["key"])

prefix = """/* Generated from knowledge files. See docs/knowledge.md for sources.
   Edit those source files, then run src/sync_web_cards.py. */
window.FF = window.FF || {};
FF.data = { flowers: """
suffix = """ };
FF.data.recognizableFlowers = FF.data.flowers.filter(f => f.class_id !== null && f.class_id < 17);
FF.data.byKey = function (key) {
  return this.flowers.find(f => f.key === key) || null;
};
/* UI-only demo. This is not a trained flower classifier. */
FF.data.demoIdentify = function (byteSum, byteMod) {
  const flowers = this.recognizableFlowers;
  const idx = (byteSum * 7 + byteMod * 13) % flowers.length;
  const primary = flowers[idx];
  const second = flowers[(idx + 5 + byteMod % 4) % flowers.length];
  const third = flowers[(idx + 11 + byteSum % 3) % flowers.length];
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
print(f"Updated {output} with {len(cards)} folios ({len(class_ids)} model classes)")
