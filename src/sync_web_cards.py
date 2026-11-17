"""Render the 17 reviewed class names and cultural-source state into the demo UI."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
classes = json.loads((ROOT / "knowledge" / "classes.json").read_text(encoding="utf-8"))
sources = json.loads((ROOT / "knowledge" / "cultural_sources.json").read_text(encoding="utf-8"))
verified = {item["class_key"]: item for item in sources["verified_items"]}

cards = []
for item in classes:
    cultural = verified.get(item["key"])
    cards.append(
        {
            "class_id": item["class_id"],
            "order": item["class_id"] + 1,
            "key": item["key"],
            "zh": item["name_zh"],
            "en": item["name_en"],
            "latin": item["scientific_name"] or "待核对",
            "family": "待核对",
            "speak": "待补充",
            "meaning": cultural["our_summary"] if cultural else "待补充：尚无逐条核对的文学或文化资料。",
            "traits": ["待补充"],
            "season": "待补充",
            "note": item["scientific_name_note"] + (" 文学关联见下方已核对来源；其他内容待补充。" if cultural else " 文学与文化资料待补充。"),
            "sources": [{"title": cultural["title"], "creator": cultural["creator"], "url": cultural["url"]}] if cultural else [],
        }
    )

prefix = """/* Generated from knowledge/classes.json and knowledge/cultural_sources.json.
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
