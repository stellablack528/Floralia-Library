BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS flower_classes (
    class_key TEXT PRIMARY KEY,
    class_id INTEGER NOT NULL UNIQUE CHECK (class_id BETWEEN 0 AND 16),
    name_zh TEXT NOT NULL,
    name_en TEXT NOT NULL,
    scientific_name TEXT,
    scientific_name_note TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS botanical_profiles (
    class_key TEXT PRIMARY KEY REFERENCES flower_classes(class_key),
    representative_name TEXT NOT NULL,
    family TEXT NOT NULL,
    genus TEXT NOT NULL,
    traits_json TEXT NOT NULL CHECK (
        CASE WHEN json_valid(traits_json)
             THEN json_type(traits_json) = 'array' AND json_array_length(traits_json) > 0
             ELSE 0 END
    ),
    habitat TEXT NOT NULL,
    flowering TEXT NOT NULL,
    scope TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE CHECK (length(url) > 8 AND substr(url, 1, 8) = 'https://'),
    title TEXT NOT NULL,
    publisher TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS botanical_sources (
    class_key TEXT NOT NULL REFERENCES botanical_profiles(class_key) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    PRIMARY KEY (class_key, source_id)
) STRICT;

CREATE TABLE IF NOT EXISTS cultural_entries (
    entry_id INTEGER PRIMARY KEY,
    class_key TEXT NOT NULL REFERENCES flower_classes(class_key),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    kind TEXT NOT NULL,
    theme TEXT NOT NULL,
    creator TEXT NOT NULL,
    locator TEXT NOT NULL,
    summary TEXT NOT NULL,
    scope TEXT NOT NULL,
    checked_on TEXT NOT NULL,
    UNIQUE (class_key, source_id, locator)
) STRICT;

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    original_name TEXT NOT NULL CHECK (length(trim(original_name)) > 0),
    local_path TEXT NOT NULL,
    title TEXT,
    author TEXT,
    publication_year INTEGER,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE IF NOT EXISTS document_parses (
    parse_id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    parsed_at TEXT NOT NULL,
    mineru_version TEXT NOT NULL,
    tier TEXT NOT NULL,
    device TEXT NOT NULL,
    output_dir TEXT NOT NULL UNIQUE,
    UNIQUE (document_id, parsed_at, tier)
) STRICT;

CREATE TABLE IF NOT EXISTS document_pages (
    parse_id INTEGER NOT NULL REFERENCES document_parses(parse_id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number >= 1),
    PRIMARY KEY (parse_id, page_number)
) STRICT;

CREATE TABLE IF NOT EXISTS document_evidence (
    evidence_id INTEGER PRIMARY KEY,
    class_key TEXT NOT NULL REFERENCES flower_classes(class_key),
    parse_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    topic TEXT NOT NULL CHECK (length(trim(topic)) > 0),
    excerpt TEXT NOT NULL CHECK (length(trim(excerpt)) > 0),
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    origin TEXT NOT NULL CHECK (origin IN ('source_statement', 'inference')),
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'verified', 'rejected')),
    FOREIGN KEY (parse_id, page_number)
        REFERENCES document_pages(parse_id, page_number) ON DELETE CASCADE
) STRICT;

CREATE INDEX IF NOT EXISTS botanical_sources_by_source ON botanical_sources(source_id);
CREATE INDEX IF NOT EXISTS cultural_entries_by_source ON cultural_entries(source_id);
CREATE INDEX IF NOT EXISTS document_evidence_by_class ON document_evidence(class_key, review_status, origin);
CREATE INDEX IF NOT EXISTS document_evidence_by_page ON document_evidence(parse_id, page_number);

PRAGMA user_version = 1;
COMMIT;
