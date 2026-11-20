"""Collect openly licensed flower observation photos for the Bloom expansion."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, UnidentifiedImageError


TAXA = {
    "camellia": (83056, "Camellia japonica"),
    "hydrangea": (122034, "Hydrangea macrophylla"),
    "plum-blossom": (357447, "Prunus mume"),
    "peach-blossom": (78755, "Prunus persica"),
    "lotus": (82814, "Nelumbo nucifera"),
    "osmanthus": (371103, "Osmanthus fragrans"),
    "tree-peony": (125432, "Paeonia × suffruticosa"),
    "wisteria": (127306, "Wisteria sinensis"),
}
PHOTO_LICENSES = {"cc0", "cc-by", "cc-by-sa"}
USER_AGENT = "Floralia-Library/1.0 (https://github.com/stellablack528/Floralia-Library)"


def get(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=14) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def observations(taxon_id, flowering, licenses):
    filters = {"taxon_id": taxon_id, "photo_license": ",".join(sorted(licenses)), "per_page": 200}
    if flowering:
        filters.update(term_id=12, term_value_id=13)
    data = json.loads(get("https://api.inaturalist.org/v1/observations?" + urlencode(filters)))
    return data["results"]


def candidates(key, taxon_id, name, licenses=PHOTO_LICENSES):
    seen = set()
    for flowering in (True, False):
        for row in observations(taxon_id, flowering, licenses):
            if (row.get("taxon") or {}).get("id") != taxon_id or row["id"] in seen:
                continue
            if row.get("quality_grade") not in {"research", "casual", "needs_id"}:
                continue
            seen.add(row["id"])
            for photo in row.get("photos", []):
                source = urlsplit(photo.get("url") or "")
                match = re.search(r"/photos/(\d+)/square\.(jpe?g|png|webp)$", source.path, re.I)
                if not match or photo.get("license_code") not in licenses:
                    continue
                photo_id, extension = match.groups()
                yield {
                    "key": key, "taxon_id": taxon_id, "scientific_name": name, "photo_id": int(photo_id),
                    "observation_id": row["id"], "observer_id": row["user"]["id"], "license": photo["license_code"],
                    "credit": photo.get("attribution"), "quality_grade": row["quality_grade"],
                    "flowering_annotation": flowering,
                    "source": f"https://www.inaturalist.org/observations/{row['id']}",
                    "image_url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{photo_id}/medium.{extension}",
                    "path": f"photos/{key}/{photo_id}.jpg",
                }
                break


def download(root, record):
    destination = root / record["path"]
    try:
        if not destination.exists():
            with Image.open(BytesIO(get(record["image_url"]))) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                if min(image.size) < 180:
                    return None
                image.save(destination, quality=94)
        record["sha256"] = sha256(destination.read_bytes()).hexdigest()
        return record
    except (OSError, UnidentifiedImageError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=125, help="Maximum candidate photos per flower")
    parser.add_argument("--supplement-peony-local", action="store_true",
                        help="Append extra peony photos licensed for noncommercial local use")
    args = parser.parse_args()
    root = args.output
    manifest = root / "candidates.json"
    if args.supplement_peony_local:
        key = "tree-peony"
        all_records = json.loads(manifest.read_text(encoding="utf-8"))
        unique = {item["observer_id"] for item in all_records if item["key"] == key}
        extra = []
        for row in candidates(key, *TAXA[key], {"cc-by-nc", "cc-by-nc-sa"}):
            if row["observer_id"] not in unique:
                unique.add(row["observer_id"])
                extra.append(row)
        with ThreadPoolExecutor(max_workers=8) as pool:
            saved = [row for row in pool.map(lambda row: download(root, row), extra[:args.limit]) if row is not None]
        manifest.write_text(json.dumps(all_records + saved, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{key}: {len(saved)} additional local-use photos", flush=True)
        return
    for key in TAXA:
        (root / "photos" / key).mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as metadata_pool:
        pending = {key: metadata_pool.submit(list, candidates(key, *taxon)) for key, taxon in TAXA.items()}
        with ThreadPoolExecutor(max_workers=10) as photo_pool:
            all_records = []
            for key, job in pending.items():
                records = job.result()
                # One photo per photographer per class where possible. The split later keeps photographers together.
                unique = {}
                for record in records:
                    unique.setdefault(record["observer_id"], record)
                jobs = [photo_pool.submit(download, root, row) for row in list(unique.values())[:args.limit]]
                saved = [record for job in jobs if (record := job.result()) is not None]
                all_records.extend(saved)
                manifest.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"{key}: {len(saved)} downloaded from {len(unique)} photographers", flush=True)


if __name__ == "__main__":
    main()
