"""Compare the full-head recipe with extra supervision of old flower classes."""

import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path

import torch

from check_bloom30_data import EPOCHS, LEARNING_RATE, TARGETS, encode, read, train_head
from floralia_model import PREPROCESS, load_model
from optimize_bloom25 import checksum, make_tail, save_candidate, write_json
from train_bloom25 import AUGMENT
from train_bloom30 import HARD_KEYS, OLD_COUNT, summarize


METHODS = {"full_head": 1.0, "old_weighted": 1.35}


def verify_new_rows(rows, previous):
    counts = Counter(r["key"] for r in rows)
    if not counts.keys() <= set(TARGETS + HARD_KEYS):
        raise ValueError("Unexpected evaluation labels")
    if sum(counts[k] for k in TARGETS) < 10 or sum(counts[k] for k in HARD_KEYS) < 10:
        raise ValueError(f"Insufficient new evaluation coverage: {dict(counts)}")
    for key in ("photo_id", "observation_id", "sha256", "observer_id"):
        historical = {r[key] for r in previous if key in r}
        test = {r[key] for r in rows}
        if test & historical:
            raise ValueError(f"New evaluation overlaps previous data on {key}")
        if key != "observer_id" and len(test) != len(rows):
            raise ValueError(f"Duplicated new evaluation {key}")
    return counts


def score(head, features, labels, classes):
    with torch.no_grad():
        return summarize(head(features).cpu(), labels.cpu(), classes)


def grouped_scores(head, data, classes):
    features, labels = data
    old = labels < OLD_COUNT
    return {"old": score(head, features[old], labels[old], classes),
            "new": score(head, features[~old], labels[~old], classes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("old_collection", type=Path)
    parser.add_argument("supplement", type=Path)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--fit", action="store_true")
    modes.add_argument("--evaluate", type=Path, metavar="LOCKED_EVALUATION_JSON")
    args = parser.parse_args()
    archived_path = args.checkpoint.with_name("splits.json")
    protocol = read(args.protocol)
    if (protocol["checkpoint_sha256"] != checksum(args.checkpoint)
            or protocol["splits_sha256"] != checksum(archived_path)
            or protocol["manifest_sha256"] != checksum(args.supplement / "candidates.json")
            or protocol["epochs"] != EPOCHS or protocol["learning_rate"] != LEARNING_RATE):
        raise ValueError("The training inputs no longer match the original protocol")
    archive = read(archived_path)
    model, classes = load_model(args.checkpoint)
    if len(classes) != 30:
        raise ValueError("Expected a 30-class checkpoint")
    device = torch.device(args.device)
    model.to(device).requires_grad_(False)
    base = model.classifier[-1]
    ids = {row["key"]: row["class_id"] for row in classes}

    def prior_path(row):
        if row.get("collection") == "bloom30":
            return args.old_collection / row["path"]
        folder = args.runtime / "data/raw/floralia-bloom25" if "photo_id" in row else args.runtime
        return folder / row["path"]

    path_protocol = checksum(args.protocol)
    if args.fit:
        args.output.mkdir(parents=True, exist_ok=False)
        torch.manual_seed(protocol["seeds"][0])
        chunks = [encode(model, group, transform, device, path, ids)
                  for group, path in ((archive["train"], prior_path),
                                      (protocol["train"], lambda row: args.supplement / row["path"]))
                  for transform in (PREPROCESS, AUGMENT)]
        train_x, train_y = (torch.cat([chunk[i] for chunk in chunks]) for i in range(2))
        with torch.no_grad():
            teacher = base(train_x)
        val = encode(model, archive["val"], PREPROCESS, device, prior_path, ids)
        log = {"protocol_sha256": path_protocol, "methods": METHODS, "runs": []}
        for seed in protocol["seeds"]:
            for name, weight in METHODS.items():
                head, history = train_head(base, train_x, train_y, teacher, seed, old_class_weight=weight)
                path = args.output / f"{name}-{seed}.pt"
                torch.save(head.cpu().state_dict(), path)
                log["runs"].append({"method": name, "seed": seed, "history": history, "head_sha256": checksum(path),
                                    "validation": grouped_scores(head.to(device), val, classes)})
            print(f"Trained both methods for seed {seed}", flush=True)
        write_json(args.output / "training.json", log)
        return

    file = args.output / "metrics.json"
    if file.exists():
        raise ValueError("Final scores already exist for this run.")
    log = read(args.output / "training.json")
    if path_protocol != log["protocol_sha256"]:
        raise ValueError("Training and evaluation protocols differ")
    new_rows = read(args.evaluate)
    counts = verify_new_rows(new_rows, [row for split in archive.values() for row in split]
                             + protocol["train"] + protocol["blind_test"])
    fresh = encode(model, new_rows, PREPROCESS, device, lambda row: Path(row["absolute_path"]), ids)
    history_rows = [row for row in archive["test"] if row["class_id"] < OLD_COUNT and not row.get("collection")]
    historical = encode(model, history_rows, PREPROCESS, device, prior_path, ids)
    result = {"counts": dict(counts), "evaluation_sha256": checksum(args.evaluate), "baseline": {
        "fresh": grouped_scores(base, fresh, classes), "historical": score(base, *historical, classes)}, "runs": []}
    for run in log["runs"]:
        method, seed = run["method"], run["seed"]
        path = args.output / f"{method}-{seed}.pt"
        if checksum(path) != run["head_sha256"]:
            raise ValueError(f"Head changed after training: {path}")
        head = deepcopy(base)
        head.load_state_dict(torch.load(path, map_location=device, weights_only=True))
        result["runs"].append({"method": method, "seed": seed, "fresh": grouped_scores(head, fresh, classes),
                               "historical": score(head, *historical, classes)})
        if seed == protocol["seeds"][0]:
            tail = deepcopy(make_tail(model))
            tail[-1][-1] = head
            save_candidate(model, tail, classes, args.output / f"{method}-trial.pt")
    write_json(file, result)
    print(f"New-photo and historical evaluation complete: {dict(counts)}", flush=True)


if __name__ == "__main__":
    main()
