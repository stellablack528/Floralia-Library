"""Render three documented Grad-CAM cases from the locked Floralia model."""

import argparse
import io
from pathlib import Path

import matplotlib
from PIL import ImageEnhance
from scipy.io import loadmat

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from floralia_model import ROOT, grad_cam, identify, load_model, read_photo
from prepare_flower17 import IMAGES, SPLITS


INK = "#16372D"
MUTED = "#526660"


def choose_cases(model, classes):
    test_ids = list(map(int, loadmat(SPLITS, variable_names=["tst1"])["tst1"].ravel()))
    members = set(test_ids)
    if (len(test_ids) != 340 or len(members) != 340 or min(members) < 1 or max(members) > 1360
            or not {84, 724} <= members
            or any(sum(start < image_id <= start + 80 for image_id in members) != 20
                   for start in range(0, 1360, 80))):
        raise ValueError("Expected the 340 official partition 1 test images, with 20 per class.")

    normal = (IMAGES / "image_0084.jpg").read_bytes()
    result = identify(normal, model, classes)
    if result["candidates"][0]["key"] != "snowdrop":
        raise RuntimeError("The correct-recognition example did not reproduce.")

    wrong = None
    # Rank the official test errors by the final model's own first-place score.
    for image_id in sorted(members):
        label = (image_id - 1) // 80
        raw = (IMAGES / f"image_{image_id:04d}.jpg").read_bytes()
        reply = identify(raw, model, classes)
        answer = reply["candidates"][0]
        if answer["class_id"] != label and (wrong is None or answer["score"] > wrong[0]):
            wrong = (answer["score"], raw, image_id, classes[label]["name_zh"])
    if wrong is None or wrong[0] < .5:
        raise RuntimeError("Expected at least one high-score test error.")

    dark_original = (IMAGES / "image_0724.jpg").read_bytes()
    with io.BytesIO() as buffer:
        ImageEnhance.Brightness(read_photo(dark_original)).enhance(.45).save(buffer, "PNG")
        dark = buffer.getvalue()
    return [("正确识别", 84, "雪滴花", normal), ("高分错判", wrong[2], wrong[3], wrong[1]),
            ("模拟低光", 724, "向日葵", dark)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, nargs="?", default=ROOT / "reports/figures/floralia_bloom_grad_cam.png")
    args = parser.parse_args()
    model, classes = load_model()
    cases = choose_cases(model, classes)
    font = Path("C:/Windows/Fonts/msyh.ttc")
    if font.is_file():
        font_manager.fontManager.addfont(font)
        matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({"font.size": 11, "text.color": INK, "figure.facecolor": "#F4F7F4"})
    fig, grid = plt.subplots(3, 3, figsize=(10.8, 10.5))
    fig.subplots_adjust(left=.24, right=.94, bottom=.09, top=.795, wspace=.17, hspace=.28)
    fig.text(.075, .953, "Floralia Bloom 1.0 识花热力图", fontsize=25, fontweight="bold")
    fig.text(.075, .900, "同一张照片选不同候选，模型关注的区域会随之变化。", color=MUTED)
    for axis, title in zip(grid[0], ("模型输入", "第一候选的 Grad-CAM", "第二候选的 Grad-CAM")):
        axis.set_title(title, fontsize=12, fontweight="bold", pad=12)
    for index, (kind, image_id, truth, raw) in enumerate(cases):
        first, second = identify(raw, model, classes)["candidates"][:2]
        original, primary = grad_cam(raw, model, first["class_id"])
        same_input, alternate = grad_cam(raw, model, second["class_id"])
        if original.tobytes() != same_input.tobytes() or primary.tobytes() == alternate.tobytes():
            raise RuntimeError(f"Expected aligned views and distinct heatmaps for {image_id}.")
        first_axis = grid[index, 0]
        first_axis.text(-.29, .66, kind, ha="right", transform=first_axis.transAxes, fontweight="bold", fontsize=12)
        first_axis.text(-.29, .45, f"图 {image_id:04d}\n真实类别 {truth}", ha="right", transform=first_axis.transAxes,
                        color=MUTED, fontsize=9, linespacing=1.6)
        for axis, image in zip(grid[index], (original, primary, alternate)):
            axis.imshow(image)
            axis.set_axis_off()
        for axis, candidate in zip(grid[index, 1:], (first, second)):
            axis.text(.5, -.045, f"{candidate['name_zh']} · {candidate['score']:.2%}", va="top", ha="center", transform=axis.transAxes,
                      color=MUTED, fontsize=10)
        print(image_id, truth, first["name_zh"], first["score"], second["name_zh"], flush=True)
    fig.text(.075, .038, "暖色标出支持所选类别的区域线索。图像为 224×224 裁剪视图，百分比为模型预测分数。", color=MUTED, fontsize=9)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.destination, dpi=175)
    plt.close(fig)


if __name__ == "__main__":
    main()
