"""Local MinerU 4.x adapter. Run this as a separate process (e.g. QProcess)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = Path(os.environ.get("FLORALIA_MINERU_KIT", ROOT / ".venv-mineru" / "Scripts" / "mineru-kit.exe"))
OUTPUT = ROOT / "documents" / "parsed"
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def parse(input_path: Path, tier: str, device: str, output_root: Path) -> Path:
    if not input_path.is_file():
        raise ValueError(f"文档不存在：{input_path}")
    if input_path.suffix.lower() not in ALLOWED:
        raise ValueError(f"不支持的格式：{input_path.suffix}")
    if not CLI.is_file():
        raise RuntimeError("MinerU 尚未安装；请先按 docs/mineru.md 建立 .venv-mineru。")

    hasher = hashlib.sha256()
    with input_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    dest = output_root / f"{input_path.stem}-{digest[:10]}-{tier}"
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / "result.zip"
    command = [str(CLI), "parse", str(input_path), "-o", str(archive), "--format", "zip", "--tier", tier]
    env = os.environ.copy()
    env["MINERU_MODEL_ONNX_DEVICE"] = device
    print(f"Parsing locally: {input_path.name} ({tier}, {device})", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"MinerU 解析失败（退出码 {result.returncode}）：\n{detail[-3000:]}")
    if not archive.is_file():
        raise RuntimeError("MinerU 已退出，但没有生成结果包。")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        required = {"markdown.md", "middle_json.json", "structured_content.json"}
        if not required.issubset(names):
            raise RuntimeError(f"结果包缺少必要文件：{sorted(required - set(names))}")
        for member in package.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(dest.resolve()):
                raise RuntimeError("结果包包含不安全路径。")
        package.extractall(dest)

    metadata = {
        "original_name": input_path.name,
        "source_path": str(input_path.resolve()),
        "sha256": digest,
        "parsed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mineru_tier": tier,
        "onnx_device": device,
        "mineru_version": "4.2.3",
        "fact_review_status": "unreviewed",
        "ai_inference": False,
        "files": names,
    }
    (dest / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed: {dest}", flush=True)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="使用独立 MinerU 环境本地解析文献")
    parser.add_argument("input", type=Path, help="PDF 或文档图片路径")
    parser.add_argument("--tier", choices=("flash", "basic"), default="flash")
    parser.add_argument("--device", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        parse(args.input, args.tier, args.device, args.output_root)
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print(f"错误：{exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
