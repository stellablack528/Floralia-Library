"""Compare lightweight Bloom 25 training recipes on its archived data split."""

import argparse
from collections import defaultdict
from copy import deepcopy
from hashlib import file_digest
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader
import torchvision

from floralia_model import EXPANDED_CHECKPOINT, PREPROCESS, ROOT, load_model
from train_bloom25 import AUGMENT, Photos


SEEDS = (20261120, 20261121, 20261122)
RECIPES = ("head", "partial", "partial-balanced")
BATCH_SIZE = 64
HEAD_LR = 0.0005
CONV_LR = 0.0001
BALANCE_BETA = 0.99
TEMPERATURE = 2.0
DISTILLATION_WEIGHT = 2.0
LEGACY_CLASSES = 17
MAX_OLD_VALIDATION_DROP = 0.01


def checksum(path):
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_splits(manifest, runtime, class_count):
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    seen = defaultdict(dict)
    for split in ("train", "val", "test"):
        labels = set()
        for row in rows[split]:
            labels.add(row["class_id"])
            base = runtime / "data/raw/floralia-bloom25" if "photo_id" in row else runtime
            path = (base / row["path"]).resolve()
            if not path.is_relative_to(base):
                raise ValueError(f"Image path leaves its data directory: {row['path']}")
            digest = checksum(path)
            if row.get("sha256", digest) != digest or digest in seen["sha256"]:
                raise ValueError(f"Image changed or duplicated in the archived split: {row['path']}")
            seen["sha256"][digest] = split
            for field in ("photo_id", "observer_id", "observation_id"):
                if field in row and seen[field].setdefault(row[field], split) != split:
                    raise ValueError(f"{field} {row[field]} occurs in multiple splits")
            row["absolute_path"] = path
        if labels != set(range(class_count)):
            raise ValueError(f"{split} does not contain all {class_count} classes")
    return rows


def make_tail(model):
    return nn.Sequential(model.features[-1], model.avgpool, nn.Flatten(1), model.classifier)


@torch.no_grad()
def cache_features(prefix, rows, transform, device):
    features, labels = [], []
    for images, targets in DataLoader(Photos(rows, transform), batch_size=BATCH_SIZE):
        features.append(prefix(images.to(device)).cpu())
        labels.append(targets)
    return torch.cat(features), torch.cat(labels)


@torch.no_grad()
def predict(tail, features, device):
    return torch.cat([tail(batch.to(device)).cpu() for batch in features.split(BATCH_SIZE)])


def evaluate(logits, labels, classes):
    if not torch.isfinite(logits).all():
        raise RuntimeError("Evaluation produced nonfinite logits")
    rank = logits.topk(3, dim=1).indices
    size = len(classes)
    confusion = torch.bincount(labels * size + rank[:, 0], minlength=size ** 2).reshape(size, size)
    samples = confusion.sum(1)
    correct = confusion.diag()
    top3 = torch.bincount(labels[rank.eq(labels[:, None]).any(1)], minlength=size)
    recall = correct.double() / samples
    f1 = 2 * correct.double() / (samples + confusion.sum(0))
    old = slice(0, LEGACY_CLASSES)
    new = slice(LEGACY_CLASSES, None)

    def counts(group):
        return {"images": int(samples[group].sum()), "top1_correct": int(correct[group].sum()),
                "top3_correct": int(top3[group].sum())}

    return {
        "macro_top1": recall.mean().item(),
        "macro_f1": f1.mean().item(),
        "old_top1": recall[old].mean().item(),
        "new_top1": recall[new].mean().item(),
        "counts": {"old": counts(old), "new": counts(new)},
        "per_class": {item["key"]: counts(index) for index, item in enumerate(classes)},
        "confusion_matrix": confusion.tolist(),
    }


def setup_recipe(base, recipe, class_counts, device):
    tail = deepcopy(base).eval()
    tail.requires_grad_(False)
    head = tail[-1][-1].requires_grad_(True)
    groups = [{"params": head.parameters(), "lr": HEAD_LR}]
    if recipe != "head":
        conv = tail[0][0].requires_grad_(True)
        groups.append({"params": conv.parameters(), "lr": CONV_LR})
    counts = class_counts.to(device=device, dtype=torch.float32)
    if recipe == "partial-balanced":
        # Cui et al. use the effective number of unique examples per class.
        weights = (1 - BALANCE_BETA) / (1 - BALANCE_BETA ** counts)
    else:
        weights = (counts.mean() / counts).sqrt()
    return tail, torch.optim.AdamW(groups), weights / weights.mean()


def train_batch(tail, optimizer, weights, features, labels, teacher_logits):
    optimizer.zero_grad(set_to_none=True)
    scores = tail(features)
    loss = F.cross_entropy(scores, labels, weight=weights)
    old = labels < LEGACY_CLASSES
    if old.any():
        student = F.log_softmax(scores[old, :LEGACY_CLASSES] / TEMPERATURE, dim=1)
        teacher = F.softmax(teacher_logits[old, :LEGACY_CLASSES] / TEMPERATURE, dim=1)
        loss = loss + DISTILLATION_WEIGHT * F.kl_div(student, teacher, reduction="batchmean")
    if not torch.isfinite(loss):
        raise RuntimeError("Training produced a nonfinite loss")
    loss.backward()
    optimizer.step()
    return float(loss.detach())


def verify_changes(base, tail, recipe):
    expected = {"3.3.weight", "3.3.bias"}
    if recipe != "head":
        expected.add("0.0.weight")
    changed = {key for key, value in base.state_dict().items()
               if not torch.equal(value, tail.state_dict()[key])}
    if changed != expected:
        raise RuntimeError(f"{recipe} changed {sorted(changed)}, expected {sorted(expected)}")
    return sorted(changed)


def smoke_check(model, base, rows, class_counts, device):
    chosen = rows[:8] + [row for row in rows if row["class_id"] >= LEGACY_CLASSES][:8]
    images, labels = next(iter(DataLoader(Photos(chosen, PREPROCESS), batch_size=len(chosen))))
    images, labels = images.to(device), labels.to(device)
    with torch.no_grad():
        features = model.features[:-1](images)
        expected = model(images)
        torch.testing.assert_close(base(features), expected)
    for recipe in RECIPES:
        tail, optimizer, weights = setup_recipe(base, recipe, class_counts, device)
        train_batch(tail, optimizer, weights, features, labels, expected)
        verify_changes(base, tail, recipe)
    print(f"Smoke check passed on {len(labels)} images for all recipes", flush=True)


def fit(base, recipe, seed, train, teacher, val, class_counts, classes, epochs, device):
    tail, optimizer, weights = setup_recipe(base, recipe, class_counts, device)
    train_x, train_y = train
    val_x, val_y = val
    rng = torch.Generator().manual_seed(seed)
    history, best, best_state = [], None, None
    started = perf_counter()
    for epoch in range(1, epochs + 1):
        weighted_loss = 0.0
        for ids in torch.randperm(len(train_y), generator=rng).split(BATCH_SIZE):
            loss = train_batch(tail, optimizer, weights, train_x[ids].to(device),
                               train_y[ids].to(device), teacher[ids].to(device))
            weighted_loss += loss * len(ids)
        validation = evaluate(predict(tail, val_x, device), val_y, classes)
        row = {"epoch": epoch, "train_loss": weighted_loss / len(train_y),
               **{key: validation[key] for key in ("macro_top1", "macro_f1", "old_top1", "new_top1")}}
        history.append(row)
        if best is None or (row["macro_top1"], row["macro_f1"]) > (best["macro_top1"], best["macro_f1"]):
            best, best_state = row, deepcopy(tail.state_dict())
    tail.load_state_dict(best_state)
    changed = verify_changes(base, tail, recipe)
    print(f"{recipe} seed {seed}: epoch {best['epoch']}, validation macro Top-1 {best['macro_top1']:.2%}",
          flush=True)
    return tail, {"seed": seed, "best": best, "history": history, "changed_tensors": changed,
                  "validation": evaluate(predict(tail, val_x, device), val_y, classes),
                  "training_seconds": perf_counter() - started}


def save_candidate(model, tail, classes, checkpoint):
    state = {key: value.cpu() for key, value in model.state_dict().items()}
    for tail_index, model_key in ((0, f"features.{len(model.features) - 1}"), (3, "classifier")):
        for name, value in tail[tail_index].state_dict().items():
            state[f"{model_key}.{name}"] = value.cpu()
    torch.save({"architecture": "mobilenet_v3_small", "classes": classes, "state_dict": state}, checkpoint)
    digest = checksum(checkpoint)
    checkpoint.with_suffix(".sha256").write_text(digest + "\n", encoding="ascii")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path, help="Directory containing photos and the archived Bloom 25 run")
    parser.add_argument("output", type=Path, help="New directory for run results and candidate checkpoints")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--smoke", action="store_true", help="Run integrity and one-batch checks without writing files")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable in this environment. Use --device cpu or install a CUDA build of PyTorch.")
    runtime = args.runtime.resolve()
    checkpoint = runtime / EXPANDED_CHECKPOINT.relative_to(ROOT)
    manifest = checkpoint.with_name("splits.json")
    model, classes = load_model(checkpoint)
    if len(classes) != 25:
        raise ValueError("Expected the Bloom 25 checkpoint")
    rows = load_splits(manifest, runtime, len(classes))
    counts = torch.bincount(torch.tensor([row["class_id"] for row in rows["train"]]))
    model = model.to(device).requires_grad_(False)
    base = make_tail(model)
    smoke_check(model, base, rows["train"], counts, device)
    if args.smoke:
        return

    args.output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    torch.manual_seed(SEEDS[0])
    views = [cache_features(model.features[:-1], rows["train"], transform, device)
             for transform in (PREPROCESS, AUGMENT, AUGMENT)]
    train_x, train_y = (torch.cat([view[index] for view in views]) for index in (0, 1))
    del views
    train = train_x, train_y
    val = cache_features(model.features[:-1], rows["val"], PREPROCESS, device)
    teacher = predict(base, train_x, device)
    baseline = evaluate(predict(base, val[0], device), val[1], classes)
    print(f"Current Bloom 25 validation macro Top-1: {baseline['macro_top1']:.2%}", flush=True)

    results, candidates = {}, {}
    for recipe in RECIPES:
        results[recipe] = []
        for seed in SEEDS:
            tail, result = fit(base, recipe, seed, train, teacher, val, counts, classes, args.epochs, device)
            results[recipe].append(result)
            if seed == SEEDS[0]:
                candidates[recipe] = tail
        write_json(args.output / f"{recipe}-validation.json", results[recipe])
    averages = {recipe: {key: mean(run["best"][key] for run in trials)
                         for key in ("macro_top1", "macro_f1", "old_top1", "new_top1")}
                for recipe, trials in results.items()}
    eligible = [recipe for recipe, trial in averages.items() if trial["macro_top1"] > baseline["macro_top1"]
                and trial["old_top1"] >= baseline["old_top1"] - MAX_OLD_VALIDATION_DROP]
    selected = max(eligible, key=lambda recipe: (averages[recipe]["macro_top1"], averages[recipe]["macro_f1"]),
                   default="current")
    selection = {"recipe": selected, "seed": SEEDS[0], "mean_validation": averages,
                 "current_validation": baseline, "max_old_validation_drop": MAX_OLD_VALIDATION_DROP}
    write_json(args.output / "selection.json", selection)
    print(f"Locked the validation decision before test evaluation: {selected}", flush=True)

    test_x, test_y = cache_features(model.features[:-1], rows["test"], PREPROCESS, device)
    test = {"current": evaluate(predict(base, test_x, device), test_y, classes)}
    checkpoints = {}
    for recipe, tail in candidates.items():
        test[recipe] = evaluate(predict(tail, test_x, device), test_y, classes)
        path = args.output / f"{recipe}.pt"
        checkpoints[recipe] = save_candidate(model, tail, classes, path)
        reloaded, _ = load_model(path)
        torch.testing.assert_close(predict(make_tail(reloaded.to(device)), test_x[:16], device),
                                   predict(tail, test_x[:16], device))
    report = {"device": torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
              "torch": torch.__version__, "torchvision": torchvision.__version__, "seeds": SEEDS,
              "images": {split: len(group) for split, group in rows.items()},
              "class_order": [item["key"] for item in classes],
              "checkpoint_sha256": checksum(checkpoint), "split_sha256": checksum(manifest),
              "checkpoint_candidates": checkpoints, "epochs": args.epochs, "batch_size": BATCH_SIZE,
              "head_lr": HEAD_LR, "conv_lr": CONV_LR, "balance_beta": BALANCE_BETA,
              "temperature": TEMPERATURE, "distillation_weight": DISTILLATION_WEIGHT,
              "elapsed_seconds": perf_counter() - started, "selection": selection, "test": test}
    write_json(args.output / "metrics.json", report)
    print(json.dumps({recipe: metrics["counts"] for recipe, metrics in test.items()}), flush=True)


if __name__ == "__main__":
    main()
