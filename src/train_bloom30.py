"""Train and evaluate Bloom 30 without overwriting production Bloom 25 weights."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import torch
from torch import nn
from torch.nn import functional as F

from flower_catalog import catalog
from floralia_model import EXPANDED_CHECKPOINT, PREPROCESS, ROOT, load_model
from optimize_bloom25 import cache_features, checksum, load_splits, make_tail, predict, save_candidate, write_json
from train_bloom25 import AUGMENT


SEED = 20261125
OLD_COUNT = 25
NEW_COUNT = 30
HARD_KEYS = ("plum-blossom", "peach-blossom", "hydrangea", "wisteria")
PAIR_KEYS = (("plum-blossom", "peach-blossom"), ("hydrangea", "wisteria"))


def reserve_review_photos(additions, historical_observers, targets):
    """Top up small evaluation groups using only previously unseen photographers."""
    minimum_train = {key: 5 if key in HARD_KEYS else 10 for key in targets}
    train = Counter(row["key"] for row in additions["train"])
    groups = defaultdict(list)
    for row in additions["train"]:
        if row["observer_id"] not in historical_observers:
            groups[row["observer_id"]].append(row)
    for split in ("test", "val"):
        counts = Counter(row["key"] for row in additions[split])
        for key in targets:
            for observer, photos in list(groups.items()):
                if counts[key] >= 5:
                    break
                group = Counter(row["key"] for row in photos)
                if not group[key] or any(train[k] - n < minimum_train[k] for k, n in group.items()):
                    continue
                additions[split].extend(photos)
                train.subtract(group)
                counts.update(group)
                del groups[observer]
    moved = {row["photo_id"] for split in ("test", "val") for row in additions[split]}
    additions["train"] = [row for row in additions["train"] if row["photo_id"] not in moved]


def splits(checkpoint, runtime, collection, classes):
    rows = load_splits(checkpoint.with_name("splits.json"), runtime, OLD_COUNT)
    historical = {split: list(group) for split, group in rows.items()}
    ids = {item["key"]: item["class_id"] for item in classes}
    digests = {checksum(row["absolute_path"]) for group in rows.values() for row in group}
    photo_ids = {row["photo_id"] for group in rows.values() for row in group if "photo_id" in row}
    observations = {row["observation_id"] for group in rows.values() for row in group if "observation_id" in row}
    observers = {row["observer_id"]: split for split, group in rows.items()
                 for row in group if "observer_id" in row}
    historical_observers = set(observers)
    additions = defaultdict(list)
    manifest = json.loads((collection / "candidates.json").read_text(encoding="utf-8"))
    approved = set(json.loads((collection / "approved.json").read_text(encoding="utf-8")))
    if not approved <= {row["photo_id"] for row in manifest}:
        raise ValueError("Approval list contains photo IDs missing from the manifest")
    for row in manifest:
        if (row["photo_id"] not in approved or row["photo_id"] in photo_ids
                or row["observation_id"] in observations):
            continue
        path = (collection / row["path"]).resolve()
        if not path.is_relative_to(collection):
            raise ValueError(f"Photo outside its collection directory: {row['path']}")
        digest = checksum(path)
        if digest != row["sha256"]:
            raise ValueError(f"Photo changed since review: {row['path']}")
        if digest in digests:
            continue
        observer = row["observer_id"]
        bucket = int.from_bytes(sha256(f"bloom25:28:{observer}".encode()).digest()[:4], "big") % 100
        split = observers.setdefault(observer, "train" if bucket < 64 else "val" if bucket < 80 else "test")
        additions[split].append({**row, "class_id": ids[row["key"]], "absolute_path": path,
                                 "collection": "bloom30"})
        digests.add(digest)
        observations.add(row["observation_id"])
        photo_ids.add(row["photo_id"])
    targets = HARD_KEYS + tuple(item["key"] for item in classes[OLD_COUNT:])
    reserve_review_photos(additions, historical_observers, targets)
    counts = {split: Counter(row["key"] for row in additions[split]) for split in rows}
    for key in targets:
        minimum_train = 5 if key in HARD_KEYS else 10
        if counts["train"][key] < minimum_train or min(counts["val"][key], counts["test"][key]) < 3:
            raise ValueError(f"{key} has too few reviewed photos: {[counts[s][key] for s in rows]}")
    return {split: historical[split] + additions[split] for split in rows}, historical, additions, counts


def summarize(logits, labels, classes):
    ranks = logits.topk(3, dim=1).indices
    per_class = {}
    for item in classes:
        select = labels.eq(item["class_id"])
        if select.any():
            matches = ranks[select].eq(labels[select, None])
            per_class[item["key"]] = {"images": int(select.sum()), "top1": int(matches[:, 0].sum()),
                                      "top3": int(matches.any(1).sum())}
    ids = {row["key"]: row["class_id"] for row in classes}
    pair_errors = {}
    for a, b in PAIR_KEYS:
        pair_errors[f"{a}->{b}"] = int((labels.eq(ids[a]) & ranks[:, 0].eq(ids[b])).sum())
        pair_errors[f"{b}->{a}"] = int((labels.eq(ids[b]) & ranks[:, 0].eq(ids[a])).sum())
    return {"images": len(labels), "top1": int(ranks[:, 0].eq(labels).sum()),
            "top3": int(ranks.eq(labels[:, None]).any(1).sum()),
            "macro_top1": sum(v["top1"] / v["images"] for v in per_class.values()) / len(per_class),
            "per_class": per_class, "pair_errors": pair_errors}


def build_student(base, partial, output_count, device):
    student = deepcopy(base).eval().requires_grad_(False)
    head = student[-1][-1]
    expanding = output_count != head.out_features
    if expanding:
        new = nn.Linear(head.in_features, output_count, device=device)
        with torch.no_grad():
            new.weight[:OLD_COUNT].copy_(head.weight)
            new.bias[:OLD_COUNT].copy_(head.bias)
        student[-1][-1] = head = new
    head.requires_grad_(True)
    groups = [{"params": head.parameters(), "lr": 0.002 if expanding else 0.0005}]
    if partial:
        groups.append({"params": student[0][0].requires_grad_(True).parameters(),
                       "lr": 0.00015 if expanding else 0.0001})
    return student, torch.optim.AdamW(groups)


def fit(base, partial, features, labels, teacher, validation, classes, epochs, device, *, hard_weight=1.0):
    torch.manual_seed(SEED)
    student, optimizer = build_student(base, partial, len(classes), device)
    untouched = deepcopy(student.state_dict())
    counts = labels.bincount(minlength=len(classes)).to(device, dtype=torch.float32)
    weights = (counts.mean() / counts).sqrt()
    hard_ids = [item["class_id"] for item in classes if item["key"] in HARD_KEYS]
    weights[hard_ids] *= hard_weight
    history, best = [], None
    rng = torch.Generator().manual_seed(SEED)
    for epoch in range(1, epochs + 1):
        loss_total = 0.0
        for batch in torch.randperm(len(labels), generator=rng).split(64):
            x, y = features[batch].to(device), labels[batch].to(device)
            z = student(x)
            loss = F.cross_entropy(z, y, weight=weights)
            old = y < OLD_COUNT
            if old.any():
                target = F.softmax(teacher[batch].to(device)[old] / 2.0, dim=1)
                logits = F.log_softmax(z[old, :OLD_COUNT] / 2.0, dim=1)
                loss = loss + F.kl_div(logits, target, reduction="batchmean")
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite loss during Bloom 30 training")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            loss_total += float(loss.detach()) * len(batch)
        vx, vy = validation
        val = summarize(predict(student, vx, device), vy, classes)
        row = {"epoch": epoch, "train_loss": loss_total / len(labels), **val}
        history.append(row)
        if best is None or row["macro_top1"] > best[0]["macro_top1"]:
            best = row, deepcopy(student.state_dict())
    changed = {key for key, value in student.state_dict().items() if not torch.equal(value, untouched[key])}
    allowed = {"3.3.weight", "3.3.bias"} | ({"0.0.weight"} if partial else set())
    if changed != allowed:
        raise RuntimeError(f"Unexpected changed parameters: {sorted(changed)}")
    student.load_state_dict(best[1])
    return student, {"best": best[0], "history": history, "changed": sorted(changed), "hard_weight": hard_weight}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path, help="Existing Bloom 25 runtime directory")
    parser.add_argument("collection", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--epochs", default=18, type=int)
    parser.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--repair25", action="store_true", help="Use only old labels to isolate targeted data repair")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable. Use --device cpu for the same experiment.")
    start = perf_counter()
    device = torch.device(args.device)
    runtime = args.runtime.resolve()
    checkpoint = runtime / EXPANDED_CHECKPOINT.relative_to(ROOT)
    model, old_classes = load_model(checkpoint)
    classes = catalog(NEW_COUNT)
    rows, historical, additions, counts = splits(checkpoint, runtime, args.collection.resolve(), classes)
    if args.repair25:
        classes = old_classes
        for group in (rows, additions):
            for split, photos in group.items():
                group[split] = [row for row in photos if row["class_id"] < OLD_COUNT]
        counts = {split: Counter(row["key"] for row in group) for split, group in additions.items()}
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    model.to(device).requires_grad_(False)
    base = make_tail(model)
    prefix = model.features[:-1]
    if args.smoke:
        batch = [next(row for row in rows["train"] if row["class_id"] == index) for index in range(len(classes))]
        train = cache_features(prefix, batch, PREPROCESS, device)
        teacher = predict(base, train[0], device)
        for partial in (False, True):
            fit(base, partial, *train, teacher, train, classes, 1, device)
        print(f"{len(classes)}-class smoke check passed for head and partial fine-tuning", flush=True)
        return
    args.output.mkdir(parents=True)
    write_json(args.output / "splits.json", {split: [{key: val for key, val in row.items()
               if key != "absolute_path"} for row in group] for split, group in rows.items()})
    torch.manual_seed(SEED)
    views = [cache_features(prefix, rows["train"], transform, device)
             for transform in (PREPROCESS, AUGMENT, AUGMENT)]
    train = tuple(torch.cat([view[i] for view in views]) for i in range(2))
    del views
    teacher = predict(base, train[0], device)
    validation = cache_features(prefix, rows["val"], PREPROCESS, device)
    models, results = {}, {}
    for name, partial, hard_weight in (("head", False, 1.0), ("partial", True, 1.0), ("partial-hard", True, 1.35)):
        models[name], results[name] = fit(base, partial, *train, teacher, validation, classes, args.epochs, device,
                                         hard_weight=hard_weight)
        print(f"{name}: validation macro Top-1 {results[name]['best']['macro_top1']:.2%}", flush=True)
    selected = max(results, key=lambda key: results[key]["best"]["macro_top1"])
    write_json(args.output / "selection.json", {"method": selected, "validation": results, "seed": SEED})
    history_x, history_y = cache_features(prefix, historical["test"], PREPROCESS, device)
    new_x, new_y = cache_features(prefix, additions["test"], PREPROCESS, device)
    old_mask = new_y < OLD_COUNT
    baseline = {"historical": summarize(predict(base, history_x, device), history_y, old_classes),
                "fresh_hard": summarize(predict(base, new_x[old_mask], device), new_y[old_mask], old_classes)}
    results["baseline"] = baseline
    for name, student in models.items():
        history_z = predict(student, history_x, device)
        new_z = predict(student, new_x, device)
        results[name]["test"] = {
            "historical": summarize(history_z, history_y, classes),
            "fresh_hard": summarize(new_z[old_mask], new_y[old_mask], classes),
        }
        if not args.repair25:
            results[name]["test"]["new_classes"] = summarize(new_z[~old_mask], new_y[~old_mask], classes)
        file = args.output / f"{name}.pt"
        results[name]["checkpoint_sha256"] = save_candidate(model, student, classes, file)
        restored, _ = load_model(file)
        torch.testing.assert_close(predict(make_tail(restored.to(device)), new_x[:16], device), new_z[:16])
    write_json(args.output / "metrics.json", {"selected": selected, "counts": counts, "seed": SEED,
               "epochs": args.epochs, "torch": torch.__version__, "device": str(device),
               "elapsed_seconds": perf_counter() - start, "results": results})
    print(f"Finished {len(classes)}-class experiment. Validation selected {selected}.", flush=True)


if __name__ == "__main__":
    main()
