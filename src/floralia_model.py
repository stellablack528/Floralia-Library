"""Local inference for Floralia Bloom and its expanded flower classifier."""

import hashlib
import io
import json
from pathlib import Path

import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from torch.nn import functional as F
from torchvision.models import ResNet18_Weights, mobilenet_v3_small
from torchvision.transforms import functional as VF


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "floralia-bloom-v1"
MODEL_NAME = "Floralia Bloom 1.0"
CHECKPOINT = ROOT / "models/experiments/flower17-student-weight-blend-20261119/best.pt"
CHECKPOINT_SHA256 = "a160718d2e5e0422614f72620fe2c7edaa7254a837de7491655792c045dd8884"
EXPANDED_CHECKPOINT = ROOT / "models/experiments/floralia-bloom25/best.pt"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000
LOW_SCORE_THRESHOLD = .5
PREPROCESS = ResNet18_Weights.IMAGENET1K_V1.transforms()


class InvalidPhoto(ValueError):
    pass


def original_classes():
    classes = json.loads((ROOT / "knowledge/classes.json").read_text(encoding="utf-8"))
    if [item["class_id"] for item in classes] != list(range(17)):
        raise ValueError("Expected the 17 Flower17 classes in ID order.")
    return classes


def expanded_classes():
    classes = original_classes()
    extra = json.loads((ROOT / "knowledge/extra_folios.json").read_text(encoding="utf-8"))
    keys = ("camellia", "hydrangea", "plum-blossom", "peach-blossom", "lotus", "osmanthus", "tree-peony", "wisteria")
    for key in keys:
        folio = extra[key]
        classes.append({"class_id": len(classes), "key": key, "name_zh": folio["name_zh"],
                        "name_en": folio["name_en"], "scientific_name": folio["profile"]["representative_name"]})
    return classes


def model_identity(classes):
    return (MODEL_ID, MODEL_NAME) if len(classes) == 17 else ("floralia-bloom-25", "Floralia Bloom 25")


def load_model(checkpoint=None):
    if checkpoint is None:
        checkpoint = EXPANDED_CHECKPOINT if EXPANDED_CHECKPOINT.is_file() else CHECKPOINT
    with checkpoint.open("rb") as file:
        checksum = hashlib.file_digest(file, "sha256").hexdigest()
        original = checksum == CHECKPOINT_SHA256
        if not original:
            checksum_file = checkpoint.with_suffix(".sha256")
            if not checksum_file.is_file() or checksum_file.read_text(encoding="ascii").strip() != checksum:
                raise ValueError("Floralia Bloom checkpoint checksum failed.")
        file.seek(0)
        saved = torch.load(file, map_location="cpu", weights_only=True)
    classes = original_classes() if original else expanded_classes()
    if saved["architecture"] != "mobilenet_v3_small" or saved["classes"] != classes:
        raise ValueError("Floralia Bloom checkpoint has a different architecture or class map.")
    torch.set_num_threads(4)
    model = mobilenet_v3_small(weights=None, num_classes=len(classes))
    model.load_state_dict(saved["state_dict"])
    return model.eval(), classes


def read_photo(raw):
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise InvalidPhoto("请选择一张不超过 10 MB 的照片。")
    try:
        with Image.open(io.BytesIO(raw)) as photo:
            if photo.format not in {"JPEG", "PNG", "WEBP"} or getattr(photo, "n_frames", 1) != 1:
                raise InvalidPhoto("请选择单张 JPG、PNG 或 WebP 照片。")
            if photo.width * photo.height > MAX_PIXELS:
                raise InvalidPhoto("照片像素过多，请缩小后重试。")
            return ImageOps.exif_transpose(photo).convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise InvalidPhoto("照片无法读取，请换一张图片。") from exc


def identify(raw, model, classes):
    tensors = PREPROCESS(read_photo(raw)).unsqueeze(0)
    with torch.inference_mode():
        scores, ids = model(tensors).softmax(dim=1)[0].topk(3)
    if not torch.isfinite(scores).all():
        raise RuntimeError("Floralia Bloom produced nonfinite scores.")
    candidates = [{"class_id": idx, "key": classes[idx]["key"], "name_zh": classes[idx]["name_zh"],
                   "name_en": classes[idx]["name_en"], "score": score}
                  for idx, score in zip(ids.tolist(), scores.tolist())]
    model_id, model_name = model_identity(classes)
    return {"model_id": model_id, "model_name": model_name, "class_count": len(classes),
            "candidates": candidates, "low_score": candidates[0]["score"] < LOW_SCORE_THRESHOLD}


def grad_cam(raw, model, class_id):
    """Return the aligned classifier view and Grad-CAM overlay for one raw class logit."""
    rgb = read_photo(raw)
    resized = VF.resize(rgb, PREPROCESS.resize_size, interpolation=PREPROCESS.interpolation, antialias=PREPROCESS.antialias)
    crop = VF.center_crop(resized, PREPROCESS.crop_size)
    pixels = VF.convert_image_dtype(VF.pil_to_tensor(crop), torch.float32)
    input_tensor = VF.normalize(pixels, PREPROCESS.mean, PREPROCESS.std).unsqueeze(0)

    # The model's last spatial feature map is immediately upstream of average pooling.
    with torch.no_grad():
        activations = model.features(input_tensor)
    with torch.enable_grad():
        activations = activations.detach().requires_grad_(True)
        logits = model.classifier(torch.flatten(model.avgpool(activations), 1))
        gradient, = torch.autograd.grad(logits[0, class_id], activations)
    weights = gradient.mean(dim=(2, 3), keepdim=True)
    mask = (weights * activations.detach()).sum(dim=1, keepdim=True).relu()
    if not torch.isfinite(mask).all():
        raise RuntimeError("Floralia Bloom produced a nonfinite Grad-CAM map.")
    mask = mask - mask.min()
    heat = F.interpolate(mask / mask.max().clamp_min(torch.finfo(mask.dtype).eps),
                         size=(crop.height, crop.width), mode="bilinear", align_corners=False)[0, 0].clamp(0, 1)
    palette = torch.tensor([[.12, .25, .65], [.04, .63, .85], [1., .83, .18], [.89, .12, .09]])
    position = heat * (len(palette) - 1)
    lo = position.long().clamp(max=len(palette) - 2)
    tint = torch.lerp(palette[lo], palette[lo + 1], (position - lo).unsqueeze(-1))
    overlay = torch.lerp(pixels.permute(1, 2, 0), tint, (.65 * heat).unsqueeze(-1))
    rendered = Image.fromarray((overlay * 255).round().to(torch.uint8).numpy())
    return crop, rendered
