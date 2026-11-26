"""Collect attributed, flower-organ photos from Pl@ntNet's GBIF observations."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

from collect_bloom25 import download, get


DATASET = "7a3679ef-5582-4aaa-81f0-8c2545cafc81"
TAXA = {
    "china-rose": (3005039, "Rosa chinensis"),
    "wisteria": (8149049, "Wisteria sinensis"),
    "peach-blossom": (8149923, "Prunus persica"),
}


def observations(taxon):
    for offset in range(0, 1500, 100):
        query = urlencode(dict(datasetKey=DATASET, taxonKey=taxon, mediaType="StillImage",
                               limit=100, offset=offset))
        page = json.loads(get(f"https://api.gbif.org/v1/occurrence/search?{query}"))
        yield from page["results"]
        if page["endOfRecords"] or not page["results"]:
            return


def candidates(key, maximum):
    taxon, name = TAXA[key]
    authors, observations_seen = set(), set()
    count = 0
    for row in observations(taxon):
        if row.get("species", "").casefold() != name.casefold():
            continue
        for media in row.get("media", []):
            license_name = media.get("license", "")
            author = (media.get("creator") or media.get("rightsHolder") or "").strip()
            uri = urlsplit(media.get("identifier", ""))
            photo = re.fullmatch(r"/image/o/([a-f\d]{40})", uri.path)
            occurrence = row["occurrenceID"]
            if (uri.scheme != "https" or uri.hostname != "bs.plantnet.org" or not photo
                    or not media.get("title", "").casefold().endswith(": flower")
                    or not license_name.casefold().endswith("(cc-by-sa)") or not author
                    or author.casefold() in authors or occurrence in observations_seen):
                continue
            photo_id = photo[1]
            yield {"key": key, "scientific_name": name, "source": f"https://www.gbif.org/occurrence/{row['key']}",
                   "observation_source": media.get("source", row.get("references")),
                   "photo_id": f"plantnet:{photo_id}", "observation_id": f"plantnet:{occurrence}",
                   "observer_id": f"plantnet:{author.casefold()}", "credit": author, "license": license_name,
                   "image_url": uri.geturl(), "path": f"photos/{key}/{photo_id}.jpg"}
            authors.add(author.casefold())
            observations_seen.add(occurrence)
            count += 1
            break
        if count >= maximum:
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", type=Path)
    parser.add_argument("--limit", type=int, default=48)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    manifest = args.collection / "candidates.json"
    rows = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else []
    collected = {r["key"] for r in rows}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for key in TAXA:
            if key in collected:
                continue
            (args.collection / "photos" / key).mkdir(parents=True, exist_ok=True)
            selected = list(candidates(key, args.limit))
            saved = [r for r in pool.map(lambda row: download(args.collection, row), selected) if r is not None]
            rows.extend(saved)
            pending = manifest.with_suffix(".tmp")
            pending.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            pending.replace(manifest)
            print(f"{key}: {len(saved)}/{len(selected)} downloads available for review", flush=True)


if __name__ == "__main__":
    main()
