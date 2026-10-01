PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS k0b03_compatibility_evidence (
    evidence_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL CHECK (operation IN ('migrate', 'backup', 'restore', 'quarantine', 'recover', 'resume_check')),
    result TEXT NOT NULL CHECK (result IN ('pass', 'blocked')),
    source_schema_version INTEGER NOT NULL CHECK (source_schema_version >= 0),
    target_schema_version INTEGER NOT NULL CHECK (target_schema_version >= 0),
    evidence_sha256 TEXT NOT NULL CHECK (length(evidence_sha256) = 64),
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS k0b03_effect_intents (
    effect_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('prepared', 'started', 'completed', 'blocked', 'quarantined')),
    envelope_sha256 TEXT NOT NULL CHECK (length(envelope_sha256) = 64),
    result_sha256 TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_k0b03_effect_intents_run_state
ON k0b03_effect_intents (run_id, state);

CREATE TABLE IF NOT EXISTS k0b03_quarantine (
    quarantine_id TEXT PRIMARY KEY,
    effect_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL CHECK (length(evidence_sha256) = 64),
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (effect_id) REFERENCES k0b03_effect_intents(effect_id)
);

PRAGMA user_version = 7;
