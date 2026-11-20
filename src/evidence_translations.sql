BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS evidence_translations (
    evidence_id INTEGER PRIMARY KEY REFERENCES document_evidence(evidence_id) ON DELETE CASCADE,
    source_excerpt TEXT NOT NULL,
    translation TEXT NOT NULL CHECK (length(trim(translation)) BETWEEN 1 AND 4000),
    model_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'verified', 'rejected'))
) STRICT;
PRAGMA user_version = 2;
COMMIT;
