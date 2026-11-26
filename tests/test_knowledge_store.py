import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from knowledge_store import SCHEMA, TRANSLATION_SCHEMA, initialize, open_store


class KnowledgeStoreTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "knowledge.sqlite3"
        initialize(self.path)
        with open_store(self.path) as store:
            self.assertTrue(store.seed())

    def make_parse(self, name: str, timestamp: str) -> Path:
        directory = self.root / name
        directory.mkdir()
        metadata = {
            "sha256": "a" * 64,
            "original_name": "botany.pdf",
            "source_path": str(self.root / "botany.pdf"),
            "parsed_at_utc": timestamp,
            "mineru_tier": "flash",
            "onnx_device": "cpu",
            "mineru_version": "4.2.3",
        }
        (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (directory / "middle_json.json").write_text(json.dumps({"pages": [{"page_idx": 0}, {"page_idx": 2}]}), encoding="utf-8")
        (directory / "markdown.md").write_text("Test text", encoding="utf-8")
        (directory / "structured_content.json").write_text("{}", encoding="utf-8")
        return directory

    def test_seed_coverage_and_edits_survive_reinitialization(self):
        with open_store(self.path) as store:
            self.assertEqual(list(range(30)), [row["class_id"] for row in store.list_flowers()])
            for row in store.list_flowers():
                flower = store.flower(row["class_key"])
                self.assertTrue(flower["botanical_profile"]["sources"])
                self.assertTrue(flower["culture"])
            self.assertEqual("snowdrop", store.list_flowers("Galanthus nivalis")[0]["class_key"])
            self.assertTrue(store.update("botanical_profiles", "snowdrop", habitat="已核对的修订"))
        initialize(self.path)
        with open_store(self.path) as store:
            self.assertFalse(store.seed())
            self.assertEqual("已核对的修订", store.flower("snowdrop")["botanical_profile"]["habitat"])

    def test_version_two_migration_preserves_existing_document_review(self):
        old = self.root / "existing.sqlite3"
        with closing(sqlite3.connect(old)) as db, db:
            db.executescript(SCHEMA.read_text(encoding="utf-8"))
            db.executescript(TRANSLATION_SCHEMA.read_text(encoding="utf-8"))
            db.execute("INSERT INTO flower_classes VALUES ('daffodil', 0, '黄水仙', 'Daffodil', NULL, 'edited note')")
            db.execute("INSERT INTO documents (document_id, sha256, original_name, local_path) VALUES (1, ?, 'old.pdf', '')",
                       ("d" * 64,))
            db.execute("""INSERT INTO document_parses (parse_id, document_id, parsed_at, mineru_version, tier, device, output_dir)
                          VALUES (1, 1, '2026-11-18', '4.2.3', 'flash', 'cpu', 'test')""")
            db.execute("INSERT INTO document_pages VALUES (1, 1)")
            db.execute("""INSERT INTO document_evidence VALUES
                          (1, 'daffodil', 1, 1, 'flower', 'old source', 'old summary', 'source_statement', 'verified')""")
            db.execute("INSERT INTO evidence_translations VALUES (1, 'old source', '已有译文', 'Hy-MT2', 'verified')")
        initialize(old)
        with open_store(old) as store:
            self.assertTrue(store.seed())
            self.assertFalse(store.seed())
            self.assertEqual("edited note", store.list_flowers()[0]["scientific_name_note"])
            self.assertEqual("已有译文", store.source_evidence("daffodil")[0]["translation"])
            self.assertEqual("Ipomoea nil", store.flower("ivy-leaved-morning-glory")["scientific_name"])
            self.assertFalse(store.rows("PRAGMA foreign_key_check"))

    def test_document_versions_page_constraint_review_and_delete(self):
        first_dir = self.make_parse("first", "2026-11-18T00:00:00+00:00")
        next_dir = self.make_parse("second", "2026-11-18T00:01:00+00:00")
        with open_store(self.path) as store:
            first = store.import_mineru(first_dir)
            self.assertEqual(first, store.import_mineru(first_dir))
            second = store.import_mineru(next_dir)
            document_id = first["document_id"]
            self.assertEqual(document_id, second["document_id"])
            self.assertNotEqual(first["parse_id"], second["parse_id"])
            self.assertEqual([1, 3], first["page_numbers"])
            self.assertEqual(2, len(store.parses(document_id)))
            self.assertTrue(store.update("documents", document_id, title="植物图鉴"))
            self.assertEqual(2, store.list_documents("图鉴")[0]["parse_count"])

            values = dict(class_key="snowdrop", parse_id=first["parse_id"], topic="花期", excerpt="原文摘录", content="一条整理结果")
            with self.assertRaises(sqlite3.IntegrityError):
                store.add("document_evidence", **values, page_number=2, origin="source_statement")
            fact = store.add("document_evidence", **values, page_number=3, origin="source_statement")
            inference = store.add("document_evidence", **values, page_number=1, origin="inference", review_status="verified")
            self.assertEqual([fact], [entry["evidence_id"] for entry in store.source_evidence("snowdrop", "pending")])
            self.assertEqual("植物图鉴", store.source_evidence("snowdrop", "pending")[0]["title"])
            self.assertEqual([], store.flower("snowdrop")["document_evidence"])
            self.assertTrue(store.update("document_evidence", fact, review_status="verified"))
            self.assertEqual([], store.source_evidence("snowdrop", "pending"))
            self.assertEqual([fact], [entry["evidence_id"] for entry in store.flower("snowdrop")["document_evidence"]])
            self.assertEqual("inference", store.get("document_evidence", inference)["origin"])
            self.assertTrue(store.update("document_evidence", fact, content="修订后的整理结果"))
            self.assertEqual([], store.flower("snowdrop")["document_evidence"])

            self.assertTrue(store.delete("documents", document_id))
            self.assertEqual([], store.evidence("snowdrop"))
            self.assertEqual([], store.parses(document_id))
            self.assertTrue((first_dir / "markdown.md").exists())

    def test_invalid_reference_and_transaction_rollback(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with open_store(self.path) as store:
                store.update("botanical_profiles", "snowdrop", habitat="应回滚的内容")
                store.delete("sources", store.flower("snowdrop")["botanical_profile"]["sources"][0]["source_id"])
        with open_store(self.path) as store:
            self.assertNotEqual("应回滚的内容", store.flower("snowdrop")["botanical_profile"]["habitat"])
            self.assertFalse(store.rows("PRAGMA foreign_key_check"))

    def test_translation_migration_and_independent_review(self):
        parse_dir = self.make_parse("translate", "2026-11-19T00:00:00+00:00")
        with open_store(self.path) as store:
            page = store.import_mineru(parse_dir)
            evidence = store.add("document_evidence", class_key="snowdrop", parse_id=page["parse_id"],
                                 page_number=1, topic="garden", excerpt="garden variety", content="整理",
                                 origin="source_statement", review_status="verified")
            store.db.execute("DROP TABLE evidence_translations")
            store.db.execute("PRAGMA user_version = 1")
        initialize(self.path)
        initialize(self.path)
        with open_store(self.path) as store:
            store.save_translation_draft(evidence, "garden variety", "机器初稿", "Hy-MT2")
            self.assertIsNone(store.source_evidence("snowdrop")[0]["translation"])
            self.assertEqual("机器初稿", store.source_evidence("snowdrop", "translations")[0]["translation"])
            store.review_translation(evidence, "verified", "园艺品种")
            self.assertEqual("园艺品种", store.source_evidence("snowdrop")[0]["translation"])
            store.save_translation_draft(evidence, "garden variety", "重复草稿", "Hy-MT2")
            self.assertEqual([], store.source_evidence("snowdrop", "translations"))
            store.update("document_evidence", evidence, excerpt="other excerpt", review_status="verified")
            self.assertIsNone(store.source_evidence("snowdrop")[0]["translation"])
            store.delete("document_evidence", evidence)
            self.assertEqual([], store.rows("SELECT * FROM evidence_translations"))


if __name__ == "__main__":
    unittest.main()
