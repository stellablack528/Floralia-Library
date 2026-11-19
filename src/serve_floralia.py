"""Serve the Floralia Web client and Bloom inference from a loopback address."""

import argparse
import base64
import io
import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit

from floralia_model import CHECKPOINT, MAX_UPLOAD_BYTES, MODEL_ID, MODEL_NAME, ROOT, InvalidPhoto, grad_cam, identify, load_model


MARKER = "<!-- floralia-local-model -->"


def png_data_uri(image):
    with io.BytesIO() as buffer:
        image.save(buffer, "PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def handler_for(web, model, classes, port):
    index = (web / "index.html").read_text(encoding="utf-8")
    if index.count(MARKER) != 1:
        raise ValueError("Local model configuration marker is missing from index.html.")
    config = {"name": MODEL_NAME, "maxBytes": MAX_UPLOAD_BYTES}
    page = index.replace(MARKER, f"<script>window.FF_LOCAL_MODEL = {json.dumps(config)};</script>").encode("utf-8")
    lock = Lock()
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, body, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def json_reply(self, code, value):
            self.reply(code, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.headers.get("Host") not in allowed_hosts:
                self.json_reply(403, {"error": "识别服务仅限本机访问。"})
                return
            path = unquote(urlsplit(self.path).path)
            if path in {"/", "/index.html"}:
                self.reply(200, page, "text/html; charset=utf-8")
                return
            if path == "/api/model":
                self.json_reply(200, {"model_id": MODEL_ID, "model_name": MODEL_NAME, "class_count": len(classes)})
                return
            parts = path.removeprefix("/").split("/")
            if not parts or parts[0] not in {"assets", "css", "js"} or any(not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts):
                self.send_error(404)
                return
            asset_root = (web / parts[0]).resolve()
            local = web.joinpath(*parts).resolve()
            if not local.is_relative_to(asset_root) or not local.is_file():
                self.send_error(404)
                return
            kind = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
            if local.suffix == ".js":
                kind = "text/javascript; charset=utf-8"
            self.reply(200, local.read_bytes(), kind)

        def do_POST(self):
            route = urlsplit(self.path)
            if route.path not in {"/api/identify", "/api/grad-cam"}:
                self.send_error(404)
                return
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in allowed_hosts or (origin and origin not in allowed_origins):
                self.json_reply(403, {"error": "识别服务仅限本机访问。"})
                return
            size = self.headers.get("Content-Length", "")
            if not size.isascii() or not size.isdecimal() or len(size) > 9 or int(size) == 0:
                self.json_reply(400, {"error": "请选择一张照片。"})
                return
            if int(size) > MAX_UPLOAD_BYTES:
                self.json_reply(413, {"error": "请选择一张不超过 10 MB 的照片。"})
                return
            if self.headers.get_content_type() not in {"image/jpeg", "image/png", "image/webp"}:
                self.json_reply(415, {"error": "请选择 JPG、PNG 或 WebP 照片。"})
                return
            class_id = None
            if route.path == "/api/grad-cam":
                target = parse_qs(route.query, keep_blank_values=True).get("class_id", [])
                if len(target) != 1 or target[0] not in {str(i) for i in range(len(classes))}:
                    self.json_reply(400, {"error": "请选择有效的解释类别。"})
                    return
                class_id = int(target[0])
            self.connection.settimeout(15)
            try:
                raw = self.rfile.read(int(size))
                if len(raw) != int(size):
                    raise InvalidPhoto("照片上传未完成，请重试。")
                with lock:
                    if class_id is None:
                        result = identify(raw, model, classes)
                    else:
                        crop, overlay = grad_cam(raw, model, class_id)
                if class_id is not None:
                    result = {"model_id": MODEL_ID, "class_id": class_id, "name_zh": classes[class_id]["name_zh"],
                              "input_image": png_data_uri(crop), "overlay_image": png_data_uri(overlay)}
            except TimeoutError:
                self.json_reply(408, {"error": "读取照片超时，请重试。"})
                return
            except InvalidPhoto as exc:
                self.json_reply(400, {"error": str(exc)})
                return
            except RuntimeError:
                logging.exception("Local model request failed for %s", route.path)
                message = "本次热力图生成失败，请重试。" if class_id is not None else "本次识别失败，请重试。"
                self.json_reply(500, {"error": message})
                return
            self.json_reply(200, result)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口应在 1 到 65535 之间。")
    web = ROOT / "web" if (ROOT / "web/index.html").is_file() else ROOT
    model, classes = load_model(args.checkpoint)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(web, model, classes, args.port)) as server:
        print(f"{MODEL_NAME} · http://127.0.0.1:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
