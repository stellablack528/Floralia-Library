"""Collect flower-photo candidates. Human review records the accepted photo IDs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit

from collect_bloom25 import PHOTO_LICENSES, TAXA, download, get

NEW_TAXA = {
    "china-rose": (133614, "Rosa chinensis"),
    "florist-chrysanthemum": (53806, "Chrysanthemum × morifolium"),
    "arabian-jasmine": (135425, "Jasminum sambac"),
    "gardenia": (210990, "Gardenia jasminoides"),
    "ivy-leaved-morning-glory": (164091, "Ipomoea nil"),
}
TARGETS = {key: TAXA[key] for key in ("plum-blossom", "peach-blossom", "hydrangea", "wisteria")} | NEW_TAXA


def observations(taxon_id, page, order, flowering, order_by="observed_on", licenses=PHOTO_LICENSES):
    filters = dict(taxon_id=taxon_id, photo_license=",".join(sorted(licenses)),
                   per_page=100, page=page, order_by=order_by, order=order)
    if flowering:
        filters.update(term_id=12, term_value_id=13)
    url = "https://api.inaturalist.org/v1/observations?" + urlencode(filters)
    return json.loads(get(url))["results"]


def candidate_rows(key, taxon, excluded_photos, excluded_observations, limit, pages=3, *,
                   excluded_observers=(), order_by="observed_on", licenses=PHOTO_LICENSES):
    taxon_id, scientific_name = taxon
    used_observers, used_observations = set(), set()
    selected = []
    for flowering in (True, False):
        for page, order in ((page, order) for page in range(1, pages + 1) for order in ("desc", "asc")):
            for row in observations(taxon_id, page, order, flowering, order_by, licenses):
                observer = row["user"]["id"]
                if ((row.get("taxon") or {}).get("id") != taxon_id or observer in used_observers or observer in excluded_observers
                        or row["id"] in used_observations or row["id"] in excluded_observations
                        or not row.get("observed_on")):
                    continue
                for photo in row.get("photos", []):
                    match = re.search(r"/photos/(\d+)/square\.(jpe?g|png|webp)$",
                                      urlsplit(photo.get("url") or "").path, re.I)
                    if not match or photo.get("license_code") not in licenses:
                        continue
                    photo_id, extension = match.groups()
                    if int(photo_id) in excluded_photos or not photo.get("attribution"):
                        continue
                    selected.append({
                        "key": key, "scientific_name": scientific_name, "taxon_id": taxon_id,
                        "photo_id": int(photo_id), "observation_id": row["id"], "observer_id": observer,
                        "quality_grade": row["quality_grade"], "flowering_annotation": flowering,
                        "date": row["observed_on"], "license": photo["license_code"],
                        "credit": photo["attribution"], "source": f"https://www.inaturalist.org/observations/{row['id']}",
                        "image_url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{photo_id}/medium.{extension}",
                        "path": f"photos/{key}/{photo_id}.jpg",
                    })
                    used_observers.add(observer)
                    used_observations.add(row["id"])
                    break
                if len(selected) == limit:
                    return selected
            time.sleep(1)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--exclude", type=Path, action="append", required=True,
                        help="Previous candidates manifest; repeat for multiple runs")
    parser.add_argument("--limit", type=int, default=85)
    parser.add_argument("--pages", type=int, default=3, help="Pages per date order and flowering filter")
    parser.add_argument("--order-by", choices=("observed_on", "created_at"), default="observed_on")
    parser.add_argument("--exclude-observers", type=Path, help="JSON array of photographer IDs")
    parser.add_argument("--photo-license", action="append", choices=sorted(PHOTO_LICENSES | {"cc-by-nc", "cc-by-nc-sa"}),
                        help="Override the photo license filters; repeat for multiple licenses")
    parser.add_argument("--keys", nargs="+", choices=TARGETS, help="Collect selected classes, appending new observations")
    args = parser.parse_args()
    if args.limit < 1 or args.pages < 1:
        parser.error("--limit and --pages must be positive")
    manifest = args.output / "candidates.json"
    all_rows = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else []
    previous = [row for path in args.exclude for row in json.loads(path.read_text(encoding="utf-8"))] + all_rows
    excluded_photos = {row["photo_id"] for row in previous}
    excluded_observations = {row["observation_id"] for row in previous}
    excluded_observers = set(json.loads(args.exclude_observers.read_text(encoding="utf-8"))) if args.exclude_observers else set()
    licenses = set(args.photo_license) if args.photo_license else PHOTO_LICENSES
    complete = {row["key"] for row in all_rows}
    keys = args.keys or [key for key in TARGETS if key not in complete]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for key in keys:
            (args.output / "photos" / key).mkdir(parents=True, exist_ok=True)
            rows = candidate_rows(key, TARGETS[key], excluded_photos, excluded_observations, args.limit, args.pages,
                                  excluded_observers=excluded_observers, order_by=args.order_by, licenses=licenses)
            saved = [row for row in pool.map(lambda row: download(args.output, row), rows) if row is not None]
            if not saved:
                raise RuntimeError(f"No usable candidates for {key}")
            all_rows.extend(saved)
            excluded_photos.update(row["photo_id"] for row in saved)
            excluded_observations.update(row["observation_id"] for row in saved)
            pending = manifest.with_suffix(".tmp")
            pending.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
            pending.replace(manifest)
            print(f"{key}: {len(saved)} photographs ready for review", flush=True)


if __name__ == "__main__":
    main()
