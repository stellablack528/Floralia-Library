import hashlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from document_import import DocumentImports, ImportBusy
from knowledge_store import initialize, open_store


class DocumentImportTest(unittest.TestCase):
    def test_pending_selection_deduplication_cache_and_temporary_cleanup(self):
        raw = b"%PDF-1.7\nexample"
        excerpt = "the Cape jasmine"
        class_key = "gardenia"
        block = Event()
        paths = []

        def parser(pdf, tier, device, output, page, *, timeout):
            paths.append(pdf)
            if not block.wait(5):
                raise RuntimeError("Test parser timed out")
            output.mkdir()
            metadata = {"original_name": pdf.name, "source_path": str(pdf), "selected_pdf_page": page,
                        "sha256": hashlib.sha256(raw).hexdigest(), "parsed_at_utc": "2026-11-20T00:00:00+00:00",
                        "mineru_version": "4.2.3", "mineru_tier": tier, "onnx_device": device}
            (output / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (output / "markdown.md").write_text(f"Text about {excerpt}.", encoding="utf-8")
            return output

        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "knowledge.sqlite3"
            initialize(db)
            with open_store(db) as store:
                store.seed()
            imports = DocumentImports(db, parser)
            with self.assertRaises(ValueError):
                imports.submit(io.BytesIO(b"not a pdf"), 9, "example.pdf", 4, "basic")
            job = imports.submit(io.BytesIO(raw), len(raw), "example.pdf", 4, "basic")
            try:
                with self.assertRaises(ImportBusy):
                    imports.submit(io.BytesIO(raw), len(raw), "example.pdf", 4, "basic")
            finally:
                block.set()
            deadline = time.monotonic() + 5
            while imports.status(job)["state"] not in ("ready", "failed") and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual("ready", imports.status(job)["state"])
            self.assertFalse(paths[0].exists())
            self.assertNotIn("metadata", imports.status(job))
            cached = imports.submit(io.BytesIO(raw), len(raw), "renamed.pdf", 4, "basic")
            self.assertTrue(imports.status(cached)["cached"])
            self.assertEqual(1, len(paths))
            with self.assertRaises(ValueError):
                imports.save(job, class_key, "Gardenia", "Invented text", "", "")
            with self.assertRaises(ValueError):
                imports.save(job, class_key, "Gardenia", excerpt, "", "javascript:alert(1)")
            source = "https://example.org/example.pdf"
            result = imports.save(job, class_key, "Gardenia", excerpt, "", source)
            duplicate = imports.save(cached, class_key, "Gardenia", excerpt, "Different notes", source)
            self.assertFalse(result["duplicate"])
            self.assertTrue(duplicate["duplicate"])
            self.assertEqual(result["evidence_id"], duplicate["evidence_id"])
            with open_store(db) as store:
                self.assertFalse(store.source_evidence(class_key))
                record, = store.source_evidence(class_key, "pending")
                self.assertEqual((excerpt, 4, source), (record["excerpt"], record["page_number"], record["source_url"]))
                document, = store.list_documents()
                self.assertEqual("", document["local_path"])
                self.assertEqual(1, document["parse_count"])
                self.assertTrue(store.update("document_evidence", result["evidence_id"], review_status="verified"))
                self.assertEqual(excerpt, store.source_evidence(class_key)[0]["excerpt"])
