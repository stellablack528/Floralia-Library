"""A bounded, local background queue for single-page PDF imports."""

import hashlib
import json
import logging
import tempfile
from collections import OrderedDict
from pathlib import Path
from subprocess import TimeoutExpired
from threading import Lock, Thread
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from knowledge_store import open_store
from parse_document import parse


MAX_PDF_BYTES = 40 * 1024 * 1024
MAX_EXCERPT = 2400
MAX_PREVIEW = 100_000
CACHE_PAGES = 6
MAX_JOBS = 8


class ImportBusy(RuntimeError):
    pass


class DocumentImports:
    def __init__(self, database, parser=parse):
        self.database = database
        self.parser = parser
        self.lock = Lock()
        self.jobs = OrderedDict()
        self.cache = OrderedDict()
        self.active = False

    def submit(self, stream, size, filename, page, tier):
        with self.lock:
            if self.active:
                raise ImportBusy("已有一份 PDF 正在处理，请稍后再试。")
            self.active = True
        temporary = None
        worker_started = False
        job_id = uuid4().hex
        try:
            temporary = tempfile.TemporaryDirectory(prefix="floralia-import-")
            path = Path(temporary.name) / "input.pdf"
            digest = hashlib.sha256()
            with path.open("wb") as output:
                first = stream.read(min(size, 1024))
                if b"%PDF-" not in first:
                    raise ValueError("文件内容不是有效的 PDF。")
                digest.update(first)
                output.write(first)
                remaining = size - len(first)
                while remaining:
                    chunk = stream.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise ValueError("PDF 上传未完成，请重试。")
                    output.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            key = (digest.hexdigest(), page, tier)
            with self.lock:
                cached = self.cache.get(key)
                if cached:
                    self.cache.move_to_end(key)
                    self.jobs[job_id] = {**cached, "state": "ready", "filename": filename, "cached": True, "seconds": 0}
                else:
                    self.jobs[job_id] = {"state": "queued", "filename": filename, "page": page, "tier": tier}
                while len(self.jobs) > MAX_JOBS:
                    self.jobs.popitem(last=False)
            if not cached:
                Thread(target=self._run, args=(job_id, temporary, path, key), daemon=True).start()
                worker_started = True
                return job_id
        except Exception:
            with self.lock:
                self.jobs.pop(job_id, None)
            raise
        finally:
            # The worker owns its temporary directory as soon as it starts.
            if not worker_started:
                self._finish(temporary)
        return job_id

    def _finish(self, temporary, job_id=None, outcome=None):
        try:
            if temporary is not None:
                temporary.cleanup()
        except OSError:
            logging.exception("Could not clean the temporary PDF directory")
        finally:
            with self.lock:
                if outcome is not None:
                    self.jobs[job_id].update(outcome)
                self.active = False

    def _run(self, job_id, temporary, path, key):
        started = perf_counter()
        _, page, tier = key
        self._patch(job_id, state="parsing")
        outcome = {"state": "failed", "error": "解析结果无法读取，请重试。"}
        try:
            folder = self.parser(path, tier, "cpu", path.parent / "parsed", page, timeout=240)
            metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            preview = (folder / "markdown.md").read_text(encoding="utf-8").strip()
            if not preview:
                raise ValueError("这一页没有可选文字。扫描版 PDF 可尝试 Basic（OCR）。")
            if len(preview) > MAX_PREVIEW:
                raise ValueError("这页提取的文本过大，无法在网页中预览。")
            if metadata["sha256"] != key[0] or metadata["selected_pdf_page"] != page:
                raise ValueError("解析结果与上传文献不一致。")
            result = {"page": page, "tier": tier, "preview": preview, "metadata": metadata,
                      "output_ref": f"web-import:{job_id}"}
            with self.lock:
                self.cache[key] = result
                if len(self.cache) > CACHE_PAGES:
                    self.cache.popitem(last=False)
            outcome = {**result, "state": "ready", "cached": False, "seconds": round(perf_counter() - started, 2)}
        except TimeoutExpired:
            outcome["error"] = "MinerU 解析超时，请检查 PDF 或改选一页。"
        except (ValueError, OSError, KeyError, RuntimeError) as exc:
            logging.warning("PDF import failed: %s", type(exc).__name__)
            message = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else (
                "MinerU 解析失败。请确认页码有效、PDF 能打开，并确认本机已安装 MinerU。"
            )
            outcome["error"] = message
        except Exception:
            logging.exception("PDF import job failed")
        finally:
            self._finish(temporary, job_id, outcome)

    def _patch(self, job_id, **fields):
        with self.lock:
            self.jobs[job_id].update(fields)

    def status(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            return {key: value for key, value in job.items() if key not in {"metadata", "output_ref"}}

    def save(self, job_id, class_key, topic, excerpt, summary, source_url):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["state"] != "ready":
                raise ValueError("预览已失效或尚未完成，请重新解析。")
            job = job.copy()
        if not excerpt or len(excerpt) > MAX_EXCERPT or excerpt not in job["preview"]:
            raise ValueError("请从预览选取不超过 2400 字符的连续原文。")
        if not topic or len(topic) > 120 or len(summary) > 2400:
            raise ValueError("请填写不超过 120 字的摘录标题，中文整理最多 2400 字符。")
        if source_url:
            uri = urlsplit(source_url)
            if (len(source_url) > 2048 or uri.scheme not in ("http", "https") or not uri.hostname
                    or uri.username or uri.password or any(char.isspace() for char in source_url)):
                raise ValueError("请填写有效的 PDF 来源网址，或留空。")
        metadata = {**job["metadata"], "original_name": job["filename"], "source_path": ""}
        with open_store(self.database) as store:
            store.db.execute("BEGIN IMMEDIATE")
            registered = store.register_parse(metadata, [job["page"]], job["output_ref"])
            document = store.get("documents", registered["document_id"])
            if source_url and not document["source_url"]:
                store.update("documents", registered["document_id"], source_url=source_url)
            existing = store.rows(
                """SELECT e.evidence_id, e.review_status FROM document_evidence e
                   JOIN document_parses p USING (parse_id)
                   WHERE p.document_id = ? AND e.page_number = ? AND e.class_key = ?
                     AND e.origin = 'source_statement' AND e.excerpt = ?
                   ORDER BY e.evidence_id LIMIT 1""",
                (registered["document_id"], job["page"], class_key, excerpt)
            )
            if existing:
                return {**existing[0], "duplicate": True}
            evidence_id = store.add("document_evidence", class_key=class_key, parse_id=registered["parse_id"],
                                    page_number=job["page"], topic=topic, excerpt=excerpt,
                                    content=summary or "待补充", origin="source_statement")
            return {"evidence_id": evidence_id, "review_status": "pending", "duplicate": False}
