"""Supplement a flower candidate list with attributed Commons files."""

import argparse
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import quote, urlencode

from collect_bloom25 import download, get
from collect_bloom30 import TARGETS


def api(**params):
    return json.loads(get("https://commons.wikimedia.org/w/api.php?" + urlencode(
        {"action": "query", "format": "json", "formatversion": 2, **params})))["query"]


def plain(value):
    return unescape(re.sub(r"<[^>]*>", "", value)).strip()


def candidates(categories, search, flower_key):
    taxon_id, scientific_name = TARGETS[flower_key]
    pages = [str(row["pageid"]) for category in categories
             for row in api(list="categorymembers", cmtitle=f"Category:{category}", cmtype="file",
                            cmlimit=500)["categorymembers"]]
    if search:
        for offset in (0, 50):
            pages.extend(str(row["pageid"]) for row in api(list="search", srsearch=search, srnamespace=6,
                         srlimit=50, sroffset=offset)["search"])
    pages = list(dict.fromkeys(pages))
    for index in range(0, len(pages), 20):
        response = api(pageids="|".join(pages[index:index + 20]), prop="imageinfo",
                       iiprop="url|mime|size|extmetadata|user", iiurlwidth=512)
        for page in response["pages"]:
            info = page["imageinfo"][0]
            if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
                continue
            metadata = info["extmetadata"]
            license_name = metadata.get("LicenseShortName", {}).get("value", "").strip()
            if not re.fullmatch(r"CC BY(?:-SA)? [1-4]\.\d|CC0|Public domain", license_name, re.I):
                continue
            artist = plain(metadata.get("Artist", {}).get("value", "")) or info.get("user", "")
            if not artist or artist.casefold() in ("unknown", "unknown author"):
                continue
            key = f"commons:{page['pageid']}"
            yield {
                "key": flower_key, "scientific_name": scientific_name, "taxon_id": taxon_id,
                "photo_id": key, "observation_id": key, "observer_id": f"commons:{artist.casefold()}",
                "quality_grade": "category", "flowering_annotation": False, "license": license_name,
                "license_url": metadata.get("LicenseUrl", {}).get("value", ""),
                "credit": artist, "source": "https://commons.wikimedia.org/wiki/" + quote(page["title"].replace(" ", "_")),
                "image_url": info["url"] if info["size"] <= 4_000_000 else info["thumburl"],
                "path": f"photos/{flower_key}/commons-{page['pageid']}.jpg",
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", type=Path)
    parser.add_argument("--flower-key", choices=TARGETS, default="china-rose")
    parser.add_argument("--category", action="append", help="Commons category name without the Category prefix")
    parser.add_argument("--search", help="Search Commons File pages in addition to selected categories")
    parser.add_argument("--limit", type=int, help="Stop after saving this many new candidates")
    parser.add_argument("--exclude", type=Path, action="append", default=[])
    parser.add_argument("--exclude-observers", type=Path)
    args = parser.parse_args()
    manifest = args.collection / "candidates.json"
    args.collection.mkdir(parents=True, exist_ok=True)
    (args.collection / "photos" / args.flower_key).mkdir(parents=True, exist_ok=True)
    current = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    seen = {row["photo_id"] for row in current}
    for path in args.exclude:
        seen.update(row["photo_id"] for row in json.loads(path.read_text(encoding="utf-8")))
    excluded = set(json.loads(args.exclude_observers.read_text(encoding="utf-8"))) if args.exclude_observers else set()
    added = 0
    for row in candidates(args.category or ([] if args.search else [TARGETS[args.flower_key][1]]),
                          args.search, args.flower_key):
        if (row["photo_id"] not in seen and row["observer_id"] not in excluded
                and (record := download(args.collection, row)) is not None):
            current.append(record)
            added += 1
            if added == args.limit:
                break
        if added and added % 10 == 0:
            pending = manifest.with_suffix(".tmp")
            pending.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            pending.replace(manifest)
    pending = manifest.with_suffix(".tmp")
    pending.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(manifest)
    print(f"{added} Commons photos ready for review.", flush=True)


if __name__ == "__main__":
    main()
