"""SQLite schema, CRUD, and imports for the Floralia knowledge base."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing, contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "knowledge" / "floralia.sqlite3"
KNOWLEDGE_DIR = ROOT / "knowledge"
SCHEMA = Path(__file__).with_name("knowledge_schema.sql")
TRANSLATION_SCHEMA = Path(__file__).with_name("evidence_translations.sql")
SCHEMA_VERSION = 2

# SQL identifiers only come from these definitions. Values are bound separately.
# Primary keys stay stable when records are edited.
EDITABLE = {
    "botanical_profiles": (
        "class_key",
        "representative_name family genus traits_json habitat flowering scope",
    ),
    "sources": ("source_id", "url title publisher"),
    "cultural_entries": (
        "entry_id", "class_key source_id kind theme creator locator summary scope checked_on",
    ),
    "documents": ("document_id", "original_name local_path title author publication_year source_url"),
    "document_evidence": ("evidence_id", "class_key parse_id page_number topic excerpt content origin review_status"),
}


def connect(path: Path, *, create: bool = False) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + ("?mode=rwc" if create else "?mode=rw")
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize(path: Path = DEFAULT_DB) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path, create=True)) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            existing = db.execute("SELECT name FROM sqlite_schema WHERE type = 'table'").fetchone()
            if existing:
                raise ValueError("当前文件已有 SQLite 表，请使用 Floralia 知识库专用的数据库路径")
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(SCHEMA.read_text(encoding="utf-8"))
            version = 1
        if version == 1:
            db.executescript(TRANSLATION_SCHEMA.read_text(encoding="utf-8"))
        elif version != SCHEMA_VERSION:
            raise ValueError(f"当前数据库版本 {version}，需要版本 {SCHEMA_VERSION}")


@contextmanager
def open_store(path: Path = DEFAULT_DB):
    """Commit on successful exit, roll back on exception, then close."""
    with closing(connect(path)) as db, db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise ValueError(f"当前数据库版本 {version}，需要版本 {SCHEMA_VERSION}")
        yield KnowledgeStore(db)


class KnowledgeStore:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def rows(self, sql: str, parameters: tuple = ()) -> list[dict]:
        return [dict(row) for row in self.db.execute(sql, parameters)]

    def add(self, table: str, **values) -> int | str:
        key, fields = EDITABLE[table]
        allowed = set(fields.split())
        if table == "botanical_profiles":
            allowed.add(key)
        if table == "documents":
            allowed.add("sha256")
        if not values or values.keys() - allowed:
            raise ValueError(f"无法添加这些字段到 {table}")
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        cursor = self.db.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values())
        )
        return values[key] if table == "botanical_profiles" else cursor.lastrowid

    def get(self, table: str, record_id: int | str) -> dict | None:
        key, _ = EDITABLE[table]
        return next(iter(self.rows(f"SELECT * FROM {table} WHERE {key} = ?", (record_id,))), None)

    def update(self, table: str, record_id: int | str, **values) -> bool:
        key, fields = EDITABLE[table]
        if not values or values.keys() - set(fields.split()):
            raise ValueError(f"无法修改 {table} 的这些字段")
        if table == "document_evidence" and values.keys() - {"review_status"}:
            values.setdefault("review_status", "pending")
        assignments = ", ".join(f"{field} = ?" for field in values)
        return self.db.execute(
            f"UPDATE {table} SET {assignments} WHERE {key} = ?", (*values.values(), record_id)
        ).rowcount == 1

    def delete(self, table: str, record_id: int | str) -> bool:
        key, _ = EDITABLE[table]
        return self.db.execute(f"DELETE FROM {table} WHERE {key} = ?", (record_id,)).rowcount == 1

    def set_botanical_sources(self, class_key: str, source_ids: list[int]) -> None:
        if self.get("botanical_profiles", class_key) is None:
            raise ValueError(f"植物档案不存在：{class_key}")
        source_ids = list(dict.fromkeys(source_ids))
        for source_id in source_ids:
            if self.get("sources", source_id) is None:
                raise ValueError(f"资料来源不存在：{source_id}")
        self.db.execute("DELETE FROM botanical_sources WHERE class_key = ?", (class_key,))
        self.db.executemany(
            "INSERT INTO botanical_sources (class_key, source_id) VALUES (?, ?)",
            ((class_key, source_id) for source_id in source_ids),
        )

    def list_flowers(self, query: str = "") -> list[dict]:
        return self.rows(
            """SELECT f.*, b.representative_name
               FROM flower_classes f LEFT JOIN botanical_profiles b USING (class_key)
               WHERE instr(lower(f.name_zh || ' ' || f.name_en || ' ' || f.class_key || ' '
                                 || coalesce(b.representative_name, '')), lower(?)) > 0
               ORDER BY f.class_id""",
            (query.strip(),),
        )

    def flower(self, class_key: str) -> dict | None:
        flower = next(iter(self.rows("SELECT * FROM flower_classes WHERE class_key = ?", (class_key,))), None)
        if flower is None:
            return None
        flower["botanical_profile"] = self.get("botanical_profiles", class_key)
        if flower["botanical_profile"] is not None:
            profile = flower["botanical_profile"]
            profile["traits"] = json.loads(profile.pop("traits_json"))
            profile["sources"] = self.rows(
                """SELECT s.* FROM botanical_sources b JOIN sources s USING (source_id)
                   WHERE b.class_key = ? ORDER BY s.source_id""", (class_key,)
            )
        flower["culture"] = self.rows(
            """SELECT e.*, s.url, s.title, s.publisher
               FROM cultural_entries e JOIN sources s USING (source_id)
               WHERE e.class_key = ? ORDER BY e.entry_id""", (class_key,)
        )
        flower["document_evidence"] = self.source_evidence(class_key)
        return flower

    def source_evidence(self, class_key: str, review_status: str = "verified") -> list[dict]:
        return self.rows(
            """SELECT e.*, d.document_id, d.original_name, d.title, d.author,
                      d.publication_year, d.source_url,
                      CASE WHEN t.status = 'verified' OR ? = 'translations' THEN t.translation END AS translation,
                      CASE WHEN t.status = 'verified' OR ? = 'translations' THEN t.model_id END AS translation_model
               FROM document_evidence e JOIN document_parses p USING (parse_id)
               JOIN documents d USING (document_id)
               LEFT JOIN evidence_translations t ON t.evidence_id = e.evidence_id AND t.source_excerpt = e.excerpt
               WHERE e.class_key = ? AND e.origin = 'source_statement'
                 AND (e.review_status = ? OR
                      (? = 'translations' AND t.status = 'pending' AND e.review_status IN ('pending', 'verified')))
               ORDER BY e.evidence_id""", (review_status, review_status, class_key, review_status, review_status)
        )

    def translation_target(self, class_key, evidence_id):
        return next(iter(self.rows(
            """SELECT e.excerpt, t.status
               FROM document_evidence e LEFT JOIN evidence_translations t
                   ON t.evidence_id = e.evidence_id AND t.source_excerpt = e.excerpt
               WHERE e.evidence_id = ? AND e.class_key = ? AND e.origin = 'source_statement'
                 AND e.review_status IN ('pending', 'verified')""", (evidence_id, class_key)
        )), None)

    def save_translation_draft(self, evidence_id, excerpt, translation, model_id):
        self.db.execute(
            """INSERT INTO evidence_translations VALUES (?, ?, ?, ?, 'pending')
               ON CONFLICT(evidence_id) DO UPDATE SET source_excerpt = excluded.source_excerpt,
                   translation = excluded.translation, model_id = excluded.model_id, status = 'pending'
               WHERE status = 'rejected' OR source_excerpt <> excluded.source_excerpt""",
            (evidence_id, excerpt, translation, model_id)
        )

    def review_translation(self, evidence_id, decision, translation):
        self.db.execute(
            """UPDATE evidence_translations SET status = ?, translation = coalesce(?, translation)
               WHERE evidence_id = ? AND status = 'pending'""", (decision, translation, evidence_id)
        )

    def list_documents(self, query: str = "") -> list[dict]:
        return self.rows(
            """SELECT d.*, count(p.parse_id) AS parse_count
               FROM documents d LEFT JOIN document_parses p USING (document_id)
               WHERE instr(lower(d.original_name || ' ' || coalesce(d.title, '') || ' '
                                 || coalesce(d.author, '')), lower(?)) > 0
               GROUP BY d.document_id ORDER BY d.document_id DESC""",
            (query.strip(),),
        )

    def parses(self, document_id: int) -> list[dict]:
        return self.rows(
            "SELECT * FROM document_parses WHERE document_id = ? ORDER BY parsed_at DESC, parse_id DESC",
            (document_id,),
        )

    def evidence(self, class_key: str, review_status: str | None = None) -> list[dict]:
        return self.rows(
            """SELECT * FROM document_evidence
               WHERE class_key = ? AND (? IS NULL OR review_status = ?) ORDER BY evidence_id""",
            (class_key, review_status, review_status),
        )

    def seed(self, folder: Path = KNOWLEDGE_DIR) -> bool:
        classes = load_json(folder / "classes.json")
        expected = [(item["class_id"], item["key"]) for item in classes]
        class_keys = {key for _, key in expected}
        if [number for number, _ in expected] != list(range(17)) or len(class_keys) != 17:
            raise ValueError("初始化数据必须包含 Flower17 的 17 个固定类别")
        if not self.db.in_transaction:
            self.db.execute("BEGIN IMMEDIATE")
        existing = self.rows("SELECT class_id, class_key FROM flower_classes ORDER BY class_id")
        if existing:
            if [(row["class_id"], row["class_key"]) for row in existing] != expected:
                raise ValueError("数据库的类别映射与初始化数据不一致")
            return False

        profiles = load_json(folder / "botanical_profiles.json")
        culture = load_json(folder / "cultural_sources.json")["verified_items"]
        if profiles.keys() != class_keys or {entry["class_key"] for entry in culture} != class_keys:
            raise ValueError("初始档案和文化资料必须覆盖全部 17 类")
        self.db.executemany(
            """INSERT INTO flower_classes
               (class_id, class_key, name_zh, name_en, scientific_name, scientific_name_note)
               VALUES (:class_id, :key, :name_zh, :name_en, :scientific_name, :scientific_name_note)""",
            classes,
        )
        for class_key, profile in profiles.items():
            values = {key: profile[key] for key in EDITABLE["botanical_profiles"][1].split() if key != "traits_json"}
            self.add("botanical_profiles", class_key=class_key, traits_json=json.dumps(profile["traits"], ensure_ascii=False), **values)
            self.set_botanical_sources(class_key, [self._source_id(ref) for ref in profile["references"]])
        for entry in culture:
            self.add(
                "cultural_entries", class_key=entry["class_key"], source_id=self._source_id(entry),
                kind=entry["kind"], theme=entry["theme"], creator=entry["creator"],
                locator=entry["locator"], summary=entry["our_summary"], scope=entry["scope"], checked_on=entry["checked_on"],
            )
        return True

    def _source_id(self, reference: dict) -> int:
        self.db.execute(
            "INSERT INTO sources (url, title, publisher) VALUES (:url, :title, :publisher) ON CONFLICT(url) DO NOTHING",
            reference,
        )
        return self.db.execute("SELECT source_id FROM sources WHERE url = ?", (reference["url"],)).fetchone()[0]

    def import_mineru(self, folder: Path) -> dict:
        folder = folder.resolve()
        for filename in ("metadata.json", "middle_json.json", "markdown.md", "structured_content.json"):
            if not (folder / filename).is_file():
                raise ValueError(f"解析目录缺少 {filename}")
        metadata = load_json(folder / "metadata.json")
        indices = [page["page_idx"] for page in load_json(folder / "middle_json.json")["pages"]]
        if not indices or any(type(index) is not int or index < 0 for index in indices) or len(indices) != len(set(indices)):
            raise ValueError("MinerU 页码必须为互不重复的非负整数")
        page_numbers = sorted(index + 1 for index in indices)
        return self.register_parse(metadata, page_numbers, str(folder))

    def register_parse(self, metadata: dict, page_numbers: list[int], output_ref: str) -> dict:
        digest = metadata["sha256"].lower()
        self.db.execute(
            """INSERT INTO documents (sha256, original_name, local_path) VALUES (?, ?, ?)
               ON CONFLICT(sha256) DO NOTHING""",
            (digest, metadata["original_name"], metadata["source_path"]),
        )
        document_id = self.db.execute("SELECT document_id FROM documents WHERE sha256 = ?", (digest,)).fetchone()[0]
        self.db.execute(
            """INSERT INTO document_parses (document_id, parsed_at, mineru_version, tier, device, output_dir)
               VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(document_id, parsed_at, tier) DO NOTHING""",
            (document_id, metadata["parsed_at_utc"], metadata["mineru_version"], metadata["mineru_tier"],
             metadata["onnx_device"], output_ref),
        )
        parse = self.db.execute(
            "SELECT parse_id, output_dir FROM document_parses WHERE document_id = ? AND parsed_at = ? AND tier = ?",
            (document_id, metadata["parsed_at_utc"], metadata["mineru_tier"]),
        ).fetchone()
        if parse["output_dir"] != output_ref:
            raise ValueError(f"同一次解析已从其它目录登记：{parse['output_dir']}")
        parse_id = parse["parse_id"]
        self.db.executemany(
            "INSERT INTO document_pages (parse_id, page_number) VALUES (?, ?) ON CONFLICT DO NOTHING",
            ((parse_id, page_number) for page_number in page_numbers),
        )
        return {"document_id": document_id, "parse_id": parse_id, "page_numbers": page_numbers}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Floralia SQLite 知识库")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="创建数据库并首次导入现有知识库")
    commands.add_parser("flowers", help="列出所有 Flower17 类别").add_argument("--query", default="")
    commands.add_parser("flower", help="读取已关联的书页内容").add_argument("class_key")
    commands.add_parser("documents", help="列出已入库文献").add_argument("--query", default="")
    commands.add_parser("import-mineru", help="登记一次已完成的 MinerU 解析").add_argument("folder", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize(args.db)
        with open_store(args.db) as store:
            if args.command == "init":
                result = {"database": str(args.db.resolve()), "seeded": store.seed(), "flower_count": len(store.list_flowers())}
            elif args.command == "flowers":
                result = store.list_flowers(args.query)
            elif args.command == "flower":
                result = store.flower(args.class_key)
                if result is None:
                    raise ValueError(f"类别不存在：{args.class_key}")
            elif args.command == "documents":
                result = store.list_documents(args.query)
            else:
                result = store.import_mineru(args.folder)
    except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"知识库操作失败：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
