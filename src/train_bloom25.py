"""Expand Bloom's classification head using Flower17 replay and new flower photos."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageOps
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

from floralia_model import CHECKPOINT, CHECKPOINT_SHA256, PREPROCESS, expanded_classes, load_model


AUGMENT = T.Compose([
    T.RandomResizedCrop(224, scale=(.72, 1.), ratio=(.85, 1.18), antialias=True),
    T.RandomHorizontalFlip(), T.ColorJitter(.12, .12, .12, .03),
    T.ToTensor(), T.Normalize(PREPROCESS.mean, PREPROCESS.std),
])


class Photos(Dataset):
    def __init__(self, records, transform):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        row = self.records[index]
        with Image.open(row["absolute_path"]) as image:
            tensor = self.transform(ImageOps.exif_transpose(image).convert("RGB"))
        return tensor, row["class_id"]


def datasets(runtime, collection, classes):
    rows = {name: [] for name in ("train", "val", "test")}
    with (runtime / "data/processed/flower17_partition1.csv").open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            rows[row["split"]].append({"class_id": int(row["class_id"]), "source": "Oxford Flower17",
                                      "path": row["relative_path"], "absolute_path": runtime / row["relative_path"]})

    approved = json.loads((collection / "approved.json").read_text(encoding="utf-8-sig"))
    approved = {int(photo_id) for photo_id in approved}
    catalog = {item["key"]: item["class_id"] for item in classes[17:]}
    seen = set()
    for row in json.loads((collection / "candidates.json").read_text(encoding="utf-8")):
        if row["photo_id"] not in approved or row["sha256"] in seen:
            continue
        seen.add(row["sha256"])
        # Use the same photographer partition across every iNaturalist class.
        bucket = int.from_bytes(sha256(f"bloom25:28:{row['observer_id']}".encode()).digest()[:4], "big") % 100
        split = "train" if bucket < 66 else "val" if bucket < 82 else "test"
        rows[split].append({**row, "class_id": catalog[row["key"]], "absolute_path": collection / row["path"]})
    summaries = {name: Counter(item["class_id"] for item in group) for name, group in rows.items()}
    for item in classes[17:]:
        counts = [summaries[name][item["class_id"]] for name in rows]
        if min(counts) < 4 or counts[0] < 14:
            raise ValueError(f"{item['key']} needs more reviewed photos. Train/val/test: {counts}.")
    return rows


@torch.no_grad()
def embeddings(model, rows, transform, device):
    batches = DataLoader(Photos(rows, transform), batch_size=32, shuffle=False)
    features = []
    labels = []
    for images, targets in batches:
        feature_map = model.features(images.to(device))
        features.append(model.classifier[:-1](model.avgpool(feature_map).flatten(1)))
        labels.append(targets.to(device))
    return torch.cat(features), torch.cat(labels)


@torch.no_grad()
def scores(head, data, classes):
    features, labels = data
    rank = head(features).topk(3, dim=1).indices
    first = rank[:, 0].eq(labels)
    result = {}
    for item in classes:
        mask = labels == item["class_id"]
        result[item["key"]] = {"count": int(mask.sum()), "correct": int(first[mask].sum()),
                               "top3_correct": int(rank[mask].eq(labels[mask, None]).any(dim=1).sum())}
    return result


def macro(result):
    return sum(row["correct"] / row["count"] for row in result.values()) / len(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("collection", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    torch.manual_seed(20261120)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    teacher, original = load_model(CHECKPOINT)
    teacher.to(device)
    previous = teacher.classifier[-1]
    classes = expanded_classes()
    rows = datasets(args.runtime, args.collection, classes)
    print({name: dict(sorted(Counter(item["class_id"] for item in group).items())) for name, group in rows.items()}, flush=True)
    print(f"Frozen Bloom features on {device}", flush=True)
    views = [embeddings(teacher, rows["train"], transform, device) for transform in (PREPROCESS, AUGMENT, AUGMENT)]
    train_x = torch.cat([view[0] for view in views])
    train_y = torch.cat([view[1] for view in views])
    validation = embeddings(teacher, rows["val"], PREPROCESS, device)
    test = embeddings(teacher, rows["test"], PREPROCESS, device)
    teacher_logits = previous(train_x).detach()
    original_mask = train_y < len(original)
    counts = torch.bincount(train_y)
    weights = (counts.float().mean() / counts).sqrt()
    head = nn.Linear(previous.in_features, len(classes), device=device)
    with torch.no_grad():
        head.weight[:len(original)].copy_(previous.weight)
        head.bias[:len(original)].copy_(previous.bias)
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.002)
    best = None
    history = []
    for epoch in range(1, 25):
        for indices in torch.randperm(len(train_y), device=device).split(128):
            labels = train_y[indices]
            logits = head(train_x[indices])
            old = original_mask[indices]
            loss = F.cross_entropy(logits, labels, weight=weights)
            if old.any():
                distillation = F.kl_div(F.log_softmax(logits[old, :len(original)] / 2, dim=1),
                                        F.softmax(teacher_logits[indices][old] / 2, dim=1), reduction="batchmean")
                loss = loss + distillation * 2
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        validation_scores = scores(head, validation, classes)
        value = macro(validation_scores)
        history.append({"epoch": epoch, "validation_macro_top1": value})
        if best is None or value > best[0]:
            best = value, epoch, {key: tensor.detach().clone() for key, tensor in head.state_dict().items()}
        print(f"epoch {epoch}: validation macro top-1 {value:.3%}", flush=True)

    head.load_state_dict(best[2])
    comparison = test[0][test[1] < len(original)], test[1][test[1] < len(original)]
    results = {"model": "Floralia Bloom 25", "base_checksum": CHECKPOINT_SHA256, "training_device": str(device),
               "selected_epoch": best[1], "history": history,
               "validation": scores(head, validation, classes), "test": scores(head, test, classes),
               "original_test_baseline": scores(previous, comparison, original)}
    args.output.mkdir(parents=True, exist_ok=True)
    teacher.classifier[-1] = head
    checkpoint = args.output / "best.pt"
    torch.save({"architecture": "mobilenet_v3_small", "classes": classes,
                "state_dict": teacher.cpu().state_dict(), "base_checksum": CHECKPOINT_SHA256}, checkpoint)
    checkpoint.with_suffix(".sha256").write_text(sha256(checkpoint.read_bytes()).hexdigest() + "\n", encoding="ascii")
    (args.output / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (args.output / "splits.json").write_text(json.dumps({name: [{key: value for key, value in item.items()
        if key != "absolute_path"} for item in group] for name, group in rows.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results["test"], indent=2), flush=True)


if __name__ == "__main__":
    main()
