"""Serve the Floralia Web client and Bloom inference from a loopback address."""

import argparse
import base64
import hashlib
import io
import json
import logging
import mimetypes
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit

from document_import import MAX_PDF_BYTES, DocumentImports, ImportBusy
from document_translation import DEFAULT_PORT, MAX_TRANSLATION, MODEL as TRANSLATION_MODEL, TranslationError, translate
from floralia_model import MAX_UPLOAD_BYTES, ROOT, InvalidPhoto, grad_cam, identify, load_model, model_identity, original_classes
from knowledge_store import DEFAULT_DB, initialize, open_store


MARKER = "<!-- floralia-local-model -->"
EVIDENCE_PATH = "/api/evidence/"
IMPORT_PATH = "/api/document-imports"


def png_data_uri(image):
    with io.BytesIO() as buffer:
        image.save(buffer, "PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def evidence_version(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()


def handler_for(web, model, classes, port, knowledge_db=DEFAULT_DB, translation_port=DEFAULT_PORT):
    index = (web / "index.html").read_text(encoding="utf-8")
    if index.count(MARKER) != 1:
        raise ValueError("Local model configuration marker is missing from index.html.")
    model_id, model_name = model_identity(classes)
    config = {"name": model_name, "maxBytes": MAX_UPLOAD_BYTES, "classKeys": [flower["key"] for flower in classes]}
    page = index.replace(MARKER, f"<script>window.FF_LOCAL_MODEL = {json.dumps(config)};</script>").encode("utf-8")
    lock = Lock()
    translation_lock = Lock()
    imports = DocumentImports(knowledge_db)
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    flower_keys = {flower["key"] for flower in original_classes()}

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

        def import_pdf(self, query):
            options = parse_qs(query)
            size = self.headers.get("Content-Length", "")
            if not size.isascii() or not size.isdecimal() or len(size) > 9 or int(size) < 5:
                self.json_reply(400, {"error": "请选择一份 PDF 文件。"})
                return
            if int(size) > MAX_PDF_BYTES:
                self.json_reply(413, {"error": "请选择不超过 40 MB 的 PDF。"})
                return
            if self.headers.get_content_type() != "application/pdf":
                self.json_reply(415, {"error": "请选择 PDF 文件。"})
                return
            filename, page, tier = (options.get(key, [""])[0] for key in ("filename", "page", "tier"))
            if (not filename.casefold().endswith(".pdf") or len(filename) > 240
                    or any(char in filename for char in "/\\") or not filename.isprintable()
                    or not page.isascii() or not page.isdecimal() or len(page) > 5 or not 1 <= int(page) <= 10000
                    or tier not in ("flash", "basic")):
                self.json_reply(400, {"error": "请填写有效的 PDF 文件名、页码和解析方式。"})
                return
            self.connection.settimeout(15)
            try:
                job = imports.submit(self.rfile, int(size), filename, int(page), tier)
            except ImportBusy as exc:
                self.json_reply(429, {"error": str(exc)})
                return
            except ValueError as exc:
                self.json_reply(400, {"error": str(exc)})
                return
            except OSError:
                self.json_reply(503, {"error": "暂时无法接收上传，请重试。"})
                return
            self.json_reply(202, {"job": job})

        def save_import(self, job):
            length = self.headers.get("Content-Length", "")
            if (self.headers.get_content_type() != "application/json" or not length.isascii()
                    or not length.isdecimal() or len(length) > 5 or not 0 < int(length) <= 32768):
                self.json_reply(400, {"error": "摘录数据格式有误。"})
                return
            self.connection.settimeout(15)
            try:
                raw = self.rfile.read(int(length))
                payload = json.loads(raw)
                keys = ("class_key", "topic", "excerpt", "summary", "source_url")
                if (len(raw) != int(length) or not isinstance(payload, dict)
                        or any(not isinstance(payload.get(key), str) for key in keys)):
                    raise ValueError("请填写摘录资料。")
                class_key, *fields = (payload[key].strip() for key in keys)
                if class_key not in flower_keys:
                    raise ValueError("请选择有效的花卉书页。")
                result = imports.save(job, class_key, *fields)
            except (json.JSONDecodeError, UnicodeError, TimeoutError):
                self.json_reply(400, {"error": "摘录数据格式有误。"})
                return
            except ValueError as exc:
                self.json_reply(400, {"error": str(exc)})
                return
            except sqlite3.Error:
                logging.exception("Could not save imported excerpt")
                self.json_reply(503, {"error": "暂时无法将摘录入库。"})
                return
            self.json_reply(200, result)

        def get_evidence(self, class_key, query):
            if class_key not in flower_keys:
                self.json_reply(404, {"error": "找不到这页花卉资料。"})
                return
            status = parse_qs(query, keep_blank_values=True).get("status", ["verified"])
            if status not in (["verified"], ["pending"], ["translations"]):
                self.json_reply(400, {"error": "请选择有效的审核状态。"})
                return
            try:
                records = []
                if knowledge_db.is_file():
                    with open_store(knowledge_db) as store:
                        records = store.source_evidence(class_key, status[0])
                if status != ["verified"]:
                    records = [{**record, "version": evidence_version(record)} for record in records]
            except (sqlite3.Error, ValueError):
                logging.exception("Could not read the knowledge database")
                self.json_reply(503, {"error": "暂时无法读取文献证据。"})
                return
            self.json_reply(200, {"records": records})

        def evidence_request(self, class_key):
            if self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
                self.json_reply(403, {"error": "审核只能在本机书页发起。"})
                return
            if class_key not in flower_keys:
                self.json_reply(404, {"error": "找不到这页花卉资料。"})
                return
            length = self.headers.get("Content-Length", "")
            if (self.headers.get_content_type() != "application/json" or not length.isascii()
                    or not length.isdecimal() or len(length) > 5 or not 0 < int(length) <= 16384):
                self.json_reply(400, {"error": "审核请求格式有误。"})
                return
            self.connection.settimeout(15)
            try:
                raw = self.rfile.read(int(length))
                if len(raw) != int(length):
                    raise ValueError
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError
                record_id = payload.get("evidence_id")
                if type(record_id) is not int or not 0 < record_id < 2**63:
                    raise ValueError
            except (TimeoutError, ValueError):
                self.json_reply(400, {"error": "审核请求格式有误。"})
                return
            return payload

        def review_evidence(self, class_key):
            payload = self.evidence_request(class_key)
            if payload is None:
                return
            record_id, decision, version = (payload.get(key) for key in ("evidence_id", "decision", "version"))
            if decision not in ("verified", "rejected") or not isinstance(version, str) or len(version) != 64:
                self.json_reply(400, {"error": "审核请求格式有误。"})
                return

            try:
                with open_store(knowledge_db) as store:
                    # Check the displayed version and write the decision in one transaction.
                    store.db.execute("BEGIN IMMEDIATE")
                    matching = next((record for record in store.source_evidence(class_key, "pending")
                                     if record["evidence_id"] == record_id), None)
                    updated = matching is not None and evidence_version(matching) == version
                    if updated:
                        store.update("document_evidence", record_id, review_status=decision)
            except (sqlite3.Error, ValueError):
                logging.exception("Could not save the evidence review")
                self.json_reply(503, {"error": "暂时无法保存审核结果。"})
                return
            if not updated:
                self.json_reply(409, {"error": "这条摘录已更新，请重新读取后核对。"})
                return
            self.json_reply(200, {"evidence_id": record_id, "review_status": decision})

        def translate_evidence(self, class_key):
            payload = self.evidence_request(class_key)
            if payload is None:
                return
            record_id = payload["evidence_id"]
            if not translation_lock.acquire(blocking=False):
                self.json_reply(429, {"error": "翻译服务正在处理另一条摘录，请稍后再试。"})
                return
            try:
                with open_store(knowledge_db) as store:
                    target = store.translation_target(class_key, record_id)
                if target is None:
                    self.json_reply(404, {"error": "找不到可翻译的原文摘录。"})
                    return
                if target["status"] in ("pending", "verified"):
                    self.json_reply(200, {"status": target["status"]})
                    return
                excerpt = target["excerpt"]
                draft = translate(excerpt, translation_port)
                with open_store(knowledge_db) as store:
                    store.db.execute("BEGIN IMMEDIATE")
                    current = store.translation_target(class_key, record_id)
                    if not current or current["excerpt"] != excerpt:
                        self.json_reply(409, {"error": "原文已更新，请重新读取后翻译。"})
                        return
                    store.save_translation_draft(record_id, excerpt, draft, TRANSLATION_MODEL)
                    status = store.translation_target(class_key, record_id)["status"]
                self.json_reply(200, {"status": status})
            except TranslationError as exc:
                self.json_reply(503, {"error": str(exc)})
            except (sqlite3.Error, ValueError):
                logging.exception("Could not save translation draft")
                self.json_reply(503, {"error": "暂时无法保存译文。"})
            finally:
                translation_lock.release()

        def review_translation(self, class_key):
            payload = self.evidence_request(class_key)
            if payload is None:
                return
            record_id, decision, version = (payload.get(key) for key in ("evidence_id", "decision", "version"))
            translation = payload.get("translation")
            if (decision not in ("verified", "rejected") or not isinstance(version, str) or len(version) != 64
                    or (decision == "verified" and
                        (not isinstance(translation, str) or not 0 < len(translation.strip()) <= MAX_TRANSLATION))):
                self.json_reply(400, {"error": "请选择审核结果，通过时请保留译文。"})
                return
            try:
                with open_store(knowledge_db) as store:
                    store.db.execute("BEGIN IMMEDIATE")
                    row = next((item for item in store.source_evidence(class_key, "translations")
                                if item["evidence_id"] == record_id), None)
                    valid = row is not None and evidence_version(row) == version
                    if valid:
                        text = translation.strip() if decision == "verified" else None
                        store.review_translation(record_id, decision, text)
            except (sqlite3.Error, ValueError):
                logging.exception("Could not save translation review")
                self.json_reply(503, {"error": "暂时无法保存译文审核结果。"})
                return
            if not valid:
                self.json_reply(409, {"error": "原文或译文已更新，请重新核对。"})
                return
            self.json_reply(200, {"status": decision})

        def do_GET(self):
            if self.headers.get("Host") not in allowed_hosts:
                self.json_reply(403, {"error": "识别服务仅限本机访问。"})
                return
            route = urlsplit(self.path)
            path = unquote(route.path)
            if path in {"/", "/index.html"}:
                self.reply(200, page, "text/html; charset=utf-8")
                return
            if path == "/api/model":
                self.json_reply(200, {"model_id": model_id, "model_name": model_name, "class_count": len(classes)})
                return
            if path.startswith(EVIDENCE_PATH):
                self.get_evidence(path.removeprefix(EVIDENCE_PATH), route.query)
                return
            if path.startswith(IMPORT_PATH + "/"):
                job = imports.status(path.removeprefix(IMPORT_PATH + "/"))
                if job is None:
                    self.json_reply(404, {"error": "解析预览已过期，请重新上传。"})
                else:
                    self.json_reply(200, job)
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
            evidence_path = unquote(route.path)
            import_path = evidence_path == IMPORT_PATH or evidence_path.startswith(IMPORT_PATH + "/")
            if (route.path not in {"/api/identify", "/api/grad-cam"}
                    and not evidence_path.startswith(EVIDENCE_PATH) and not import_path):
                self.send_error(404)
                return
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in allowed_hosts or (origin and origin not in allowed_origins):
                self.json_reply(403, {"error": "识别服务仅限本机访问。"})
                return
            if import_path:
                if origin != f"http://{self.headers.get('Host')}":
                    self.json_reply(403, {"error": "请从本机网页提交 PDF。"})
                elif evidence_path == IMPORT_PATH:
                    self.import_pdf(route.query)
                else:
                    job, _, action = evidence_path.removeprefix(IMPORT_PATH + "/").partition("/")
                    if action == "evidence":
                        self.save_import(job)
                    else:
                        self.json_reply(404, {"error": "找不到此操作。"})
                return
            if evidence_path.startswith(EVIDENCE_PATH):
                key, _, action = evidence_path.removeprefix(EVIDENCE_PATH).partition("/")
                actions = {"": self.review_evidence, "translate": self.translate_evidence,
                           "review-translation": self.review_translation}
                if action in actions:
                    actions[action](key)
                else:
                    self.json_reply(404, {"error": "找不到此操作。"})
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
                    result = {"model_id": model_id, "class_id": class_id, "name_zh": classes[class_id]["name_zh"],
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
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--knowledge-db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--translation-port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口应在 1 到 65535 之间。")
    if not 1 <= args.translation_port <= 65535 or args.translation_port == args.port:
        parser.error("翻译服务需要独立的有效端口。")
    web = ROOT / "web" if (ROOT / "web/index.html").is_file() else ROOT
    model, classes = load_model(args.checkpoint)
    initialize(args.knowledge_db)
    with open_store(args.knowledge_db) as store:
        store.seed()
    with ThreadingHTTPServer(("127.0.0.1", args.port),
                             handler_for(web, model, classes, args.port, args.knowledge_db, args.translation_port)) as server:
        print(f"{model_identity(classes)[1]} · http://127.0.0.1:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
