"""Evaluate released or experimental Bloom 30 weights on new flower photos."""

import argparse
from collections import Counter
import json
from pathlib import Path

from floralia_model import identify, load_model
from optimize_bloom25 import checksum, write_json


FOCUS = {"china-rose", "wisteria", "peach-blossom"}
IDENTIFIERS = ("photo_id", "observation_id", "observer_id", "sha256")


def check_records(rows, earlier):
    if not {r["partition"] for r in rows} <= {"train", "test"}:
        raise ValueError("Each curated photo needs a train or test partition")
    train = [r for r in rows if r["partition"] == "train"]
    test = [r for r in rows if r["partition"] == "test"]
    if {r["key"] for r in test} != FOCUS:
        raise ValueError("The independent check must cover all three selected categories")
    if any(r["key"] != "china-rose" or "cc-by-nc" in r["license"].casefold() for r in train):
        raise ValueError("This collection's training split is reserved for the open-license China rose photos")
    for key in IDENTIFIERS:
        historical = {r[key] for r in earlier if key in r}
        train_ids, test_ids = {r[key] for r in train}, {r[key] for r in test}
        if train_ids & test_ids or (train_ids | test_ids) & historical:
            raise ValueError(f"Previously used {key} or {key} shared between splits")
        if key != "observer_id" and len(train_ids | test_ids) != len(rows):
            raise ValueError(f"Duplicated {key}")
    for row in rows:
        if checksum(Path(row["absolute_path"])) != row["sha256"]:
            raise ValueError(f"Photo content changed: {row['photo_id']}")
    return train, test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--archive", type=Path, required=True, help="Original Bloom 30 splits")
    parser.add_argument("--protocol", type=Path, required=True, help="Previous supplement and holdout")
    parser.add_argument("--prior-test", type=Path, required=True, help="Previous joint evaluation photos")
    parser.add_argument("--model", action="append", required=True, help="Label=checkpoint path; repeat")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output to avoid overwriting an existing evaluation")

    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))

    earlier = [row for group in read(args.archive).values() for row in group]
    protocol = read(args.protocol)
    earlier.extend(protocol["train"] + protocol["blind_test"] + read(args.prior_test))
    train, test = check_records(read(args.manifest), earlier)
    photos = [(row, Path(row["absolute_path"]).read_bytes()) for row in test]
    metrics = {"manifest_sha256": checksum(args.manifest), "train": dict(Counter(r["key"] for r in train)),
               "test": dict(Counter(r["key"] for r in test)), "models": {}}
    for spec in args.model:
        label, sep, file = spec.partition("=")
        if not sep or not label or not file or label in metrics["models"]:
            parser.error("--model must contain a unique label followed by = and a checkpoint path")
        model, classes = load_model(Path(file))
        if len(classes) != 30:
            raise ValueError("Expected 30-class checkpoints")
        rows = []
        for row, raw in photos:
            result = identify(raw, model, classes)
            rows.append({"photo_id": row["photo_id"], "expected": row["key"], "candidates": result["candidates"]})
        by_class = {}
        for key in sorted(FOCUS):
            selected = [r for r in rows if r["expected"] == key]
            predictions = [[p["key"] for p in r["candidates"]] for r in selected]
            by_class[key] = {"images": len(selected), "top1": sum(p[0] == key for p in predictions),
                             "top3": sum(key in p for p in predictions),
                             "wrong_first_choices": dict(Counter(p[0] for p in predictions if p[0] != key))}
        metrics["models"][label] = {"per_class": by_class, "predictions": rows}
        print(label, by_class, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, metrics)


if __name__ == "__main__":
    main()
