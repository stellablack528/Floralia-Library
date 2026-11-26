"""Measure the effect of new photos while holding model and training budget fixed."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import torch
from torch.nn import functional as F

from floralia_model import PREPROCESS, load_model
from optimize_bloom25 import checksum, write_json
from train_bloom25 import AUGMENT, embeddings
from train_bloom30 import OLD_COUNT, summarize


TARGETS = ("china-rose", "gardenia", "florist-chrysanthemum")
SEEDS = (20261126, 20261127, 20261128)
EPOCHS = 10
LEARNING_RATE = 0.0005


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(archived, collection, output, checkpoint):
    manifest = collection / "candidates.json"
    approved = set(read(collection / "approved.json"))
    rows = [row for row in read(manifest) if row["photo_id"] in approved]
    if {row["photo_id"] for row in rows} != approved:
        raise ValueError("Approved photo IDs must exist in the collection")
    historical = [row for group in archived.values() for row in group]
    old_observers = {row["observer_id"] for row in historical if "observer_id" in row}
    old_train_observers = {row["observer_id"] for row in archived["train"] if "observer_id" in row}
    seen = {field: {row[field] for row in historical if field in row}
            for field in ("photo_id", "observation_id", "sha256")}
    qualified = []
    for row in rows:
        if row["key"] not in TARGETS:
            raise ValueError(f"Unexpected target {row['key']}")
        if row["observer_id"] in old_observers - old_train_observers:
            continue
        if any(row[field] in values for field, values in seen.items()):
            continue
        for field, values in seen.items():
            values.add(row[field])
        qualified.append(row)
    grouped = defaultdict(list)
    for row in qualified:
        if row["observer_id"] not in old_observers:
            grouped[row["observer_id"]].append(row)
    group_order = sorted(grouped, key=lambda item: sha256(f"bloom30-data:{item}".encode()).digest())
    remaining = Counter(row["key"] for row in qualified)
    planned = {key: min(24, max(0, remaining[key] - 18)) for key in TARGETS}
    test, take = [], set()
    count_test = Counter()
    for key in sorted(TARGETS, key=remaining.get):
        for observer in group_order:
            if count_test[key] >= planned[key]:
                break
            group = grouped[observer]
            counts = Counter(row["key"] for row in group)
            if observer in take or key not in counts or any(remaining[k] - n < 18 for k, n in counts.items()):
                continue
            take.add(observer)
            count_test.update(counts)
            remaining.subtract(counts)
            test.extend(group)
    train = [row for row in qualified if row["observer_id"] not in take]
    if min(remaining.get(key, 0) for key in TARGETS) < 10 or min(count_test.get(key, 0) for key in TARGETS) < 5:
        raise ValueError(f"More reviewed independent photographs needed: train={dict(remaining)}, test={dict(count_test)}")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "protocol.json", {
        "seeds": SEEDS, "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
        "checkpoint_sha256": checksum(checkpoint), "splits_sha256": checksum(checkpoint.with_name("splits.json")),
        "manifest_sha256": checksum(manifest), "train": train, "blind_test": test,
    })
    print(f"Locked new photos: train={dict(remaining)}, test={dict(count_test)}", flush=True)


def encode(model, rows, transform, device, path_for, ids):
    resolved = []
    for row in rows:
        path = path_for(row)
        if "sha256" in row and checksum(path) != row["sha256"]:
            raise ValueError(f"Image checksum mismatch: {path}")
        resolved.append({**row, "absolute_path": path, "class_id": ids[row["key"]] if "key" in row else row["class_id"]})
    return embeddings(model, resolved, transform, device)


def train_head(base, train_x, train_y, teacher, seed, *, protected=None, old_class_weight=1.0):
    head = deepcopy(base).requires_grad_(True)
    optimizer = torch.optim.AdamW(head.parameters(), lr=LEARNING_RATE)
    rng = torch.Generator().manual_seed(seed)
    counts = train_y.bincount().float()
    weights = (counts.mean() / counts).sqrt()
    weights[:OLD_COUNT] *= old_class_weight
    history = []
    for _ in range(EPOCHS):
        loss_sum = 0.0
        for indexes in torch.randperm(len(train_y), generator=rng).split(64):
            labels = train_y[indexes]
            scores = head(train_x[indexes])
            loss = F.cross_entropy(scores, labels, weight=weights)
            old = labels < OLD_COUNT
            if old.any():
                loss = loss + F.kl_div(F.log_softmax(scores[old, :OLD_COUNT] / 2, dim=1),
                                       F.softmax(teacher[indexes][old, :OLD_COUNT] / 2, dim=1), reduction="batchmean")
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            if protected is not None:
                # Zero gradients alone does not stop AdamW from applying weight decay.
                with torch.no_grad():
                    head.weight[protected] = base.weight[protected]
                    head.bias[protected] = base.bias[protected]
            loss_sum += float(loss.detach()) * len(labels)
        history.append(loss_sum / len(train_y))
    if protected is not None:
        torch.testing.assert_close(head.weight[protected], base.weight[protected], atol=0, rtol=0)
        torch.testing.assert_close(head.bias[protected], base.bias[protected], atol=0, rtol=0)
    return head.eval(), history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("checkpoint", type=Path, help="Existing Bloom 30 checkpoint next to its splits.json")
    parser.add_argument("original_collection", type=Path)
    parser.add_argument("collection", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--protocol", type=Path, help="Read the locked protocol from a previous run")
    parser.add_argument("--protect-other-classes", action="store_true",
                        help="Compare updating the full head with updating only the three target outputs")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    split_file = args.checkpoint.with_name("splits.json")
    archived = read(split_file)
    if args.prepare:
        if args.protocol or args.protect_other_classes:
            parser.error("--prepare creates the original protocol; use a second output for protection experiments")
        prepare(archived, args.collection, args.output, args.checkpoint)
        return
    if (args.output / "metrics.json").exists():
        raise ValueError("Existing result; preserve it before starting a separate run")
    protocol_file = args.protocol or args.output / "protocol.json"
    locked = read(protocol_file)
    if (list(SEEDS) != locked["seeds"] or EPOCHS != locked["epochs"] or LEARNING_RATE != locked["learning_rate"]
            or locked["checkpoint_sha256"] != checksum(args.checkpoint)
            or locked["splits_sha256"] != checksum(split_file)
            or locked["manifest_sha256"] != checksum(args.collection / "candidates.json")):
        raise ValueError("Experiment inputs differ from the locked protocol")
    model, classes = load_model(args.checkpoint)
    if len(classes) != 30:
        raise ValueError("Expected a Bloom 30 checkpoint")
    device = torch.device(args.device)
    model.to(device).requires_grad_(False)
    base = model.classifier[-1]
    ids = {row["key"]: row["class_id"] for row in classes}

    def prior_path(row):
        if row.get("collection") == "bloom30":
            return args.original_collection / row["path"]
        root = args.runtime / "data/raw/floralia-bloom25" if "photo_id" in row else args.runtime
        return root / row["path"]

    def recent_path(row):
        return args.collection / row["path"]

    torch.manual_seed(SEEDS[0])
    common = [encode(model, archived["train"], transform, device, prior_path, ids) for transform in (PREPROCESS, AUGMENT)]
    fresh = [encode(model, locked["train"], transform, device, recent_path, ids) for transform in (PREPROCESS, AUGMENT)]
    x, y = (torch.cat([part[i] for part in common]) for i in range(2))
    new_x, new_y = (torch.cat([part[i] for part in fresh]) for i in range(2))
    labels = torch.cat((y, new_y))
    available = {ids[key]: y.eq(ids[key]).nonzero().flatten().cpu() for key in TARGETS}
    frozen_rows = torch.tensor([row["key"] not in TARGETS for row in classes], device=device)
    heads, histories = {}, {}
    for seed in SEEDS:
        if args.protect_other_classes:
            recipes = (("new_photos", new_x, None), ("protected_outputs", new_x, frozen_rows))
        else:
            rng = torch.Generator().manual_seed(seed)
            replay = [pool[int(torch.randint(len(pool), (1,), generator=rng).item())] for label in new_y.tolist()
                      for pool in [available[label]]]
            recipes = (("replay", x[torch.stack(replay).to(device)], None), ("new_photos", new_x, None))
        for key, extra, protected in recipes:
            features = torch.cat((x, extra))
            with torch.no_grad():
                scores = base(features)
            heads[key, seed], histories[key, seed] = train_head(base, features, labels, scores, seed, protected=protected)
        print(f"Paired training complete for seed {seed}", flush=True)
    # The new test images are first loaded after all training has finished.
    datasets = {
        "blind_test": encode(model, locked["blind_test"], PREPROCESS, device, recent_path, ids),
        "historical_25": encode(model, [r for r in archived["test"] if r["class_id"] < OLD_COUNT and not r.get("collection")],
                                PREPROCESS, device, prior_path, ids),
    }
    if args.protect_other_classes:
        datasets["archived_validation"] = encode(model, archived["val"], PREPROCESS, device, prior_path, ids)
    metrics = {"protocol_sha256": checksum(protocol_file), "baseline": {}, "trials": []}
    with torch.no_grad():
        for dataset, (features, targets) in datasets.items():
            metrics["baseline"][dataset] = summarize(base(features).cpu(), targets.cpu(), classes)
        for (key, seed), head in heads.items():
            trial = {"recipe": key, "seed": seed, "train_loss": histories[key, seed]}
            for dataset, (features, targets) in datasets.items():
                scores = head(features)
                trial[dataset] = summarize(scores.cpu(), targets.cpu(), classes)
                if dataset == "blind_test":
                    trial["blind_top1_correct"] = scores.argmax(1).eq(targets).tolist()
            metrics["trials"].append(trial)
    if args.protect_other_classes:
        metrics["protected_class_keys"] = [row["key"] for row in classes if row["key"] not in TARGETS]
        metrics["test_role"] = "Previously evaluated holdout; regression check only"
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "metrics.json", metrics)
    print("Holdout and historical scores saved.", flush=True)


if __name__ == "__main__":
    main()
