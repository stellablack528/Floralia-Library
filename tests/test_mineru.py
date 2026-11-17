"""Small end-to-end check; uses the local one-page PDF, no flower model."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from parse_document import parse  # noqa: E402


class MinerUIntegrationTest(unittest.TestCase):
    def test_flash_pdf_exports_markdown_json_and_source(self):
        sample = ROOT / "documents" / "samples" / "flower_sample.pdf"
        with tempfile.TemporaryDirectory() as temp:
            dest = parse(sample, "flash", "cpu", Path(temp))
            self.assertIn("Daffodil field notes", (dest / "markdown.md").read_text(encoding="utf-8"))
            middle = json.loads((dest / "middle_json.json").read_text(encoding="utf-8"))
            self.assertIn("pages", middle)
            self.assertTrue((dest / "structured_content.json").is_file())
            metadata = json.loads((dest / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["original_name"], sample.name)
            self.assertEqual(metadata["fact_review_status"], "unreviewed")

    def test_missing_document_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "文档不存在"):
                parse(Path(temp) / "missing.pdf", "flash", "cpu", Path(temp))


if __name__ == "__main__":
    unittest.main()
