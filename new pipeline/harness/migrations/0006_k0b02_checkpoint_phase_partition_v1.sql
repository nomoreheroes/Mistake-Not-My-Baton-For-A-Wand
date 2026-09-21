PRAGMA foreign_keys=ON;

CREATE TABLE k0b02_phase_bindings (
  phase_id TEXT PRIMARY KEY,
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64),
  phase_order INTEGER NOT NULL UNIQUE CHECK(phase_order IN (1,2)),
  predecessor_phase_id TEXT REFERENCES k0b02_phase_bindings(phase_id),
  runtime_enabled INTEGER NOT NULL CHECK(runtime_enabled=0)
) STRICT;

CREATE TABLE k0b02_outbox_phase_bindings (
  outbox_id TEXT PRIMARY KEY REFERENCES k0b02_projection_outbox(outbox_id),
  phase_id TEXT NOT NULL REFERENCES k0b02_phase_bindings(phase_id),
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64)
) STRICT;

CREATE TABLE k0b02_publication_phase_bindings (
  publication_id TEXT PRIMARY KEY REFERENCES k0b02_publication_intents(publication_id),
  phase_id TEXT NOT NULL REFERENCES k0b02_phase_bindings(phase_id),
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64)
) STRICT;

CREATE TABLE k0b02_phase_counters (
  phase_id TEXT PRIMARY KEY REFERENCES k0b02_phase_bindings(phase_id),
  cumulative_full_snapshot_bytes INTEGER NOT NULL DEFAULT 0 CHECK(cumulative_full_snapshot_bytes>=0),
  publication_count INTEGER NOT NULL DEFAULT 0 CHECK(publication_count>=0),
  batch_publications INTEGER NOT NULL DEFAULT 0 CHECK(batch_publications>=0 AND batch_publications<=12),
  model_calls INTEGER NOT NULL DEFAULT 0 CHECK(model_calls>=0),
  boundary_trigger_count INTEGER NOT NULL DEFAULT 0 CHECK(boundary_trigger_count>=0)
) STRICT;

CREATE TABLE k0b02_phase_seals (
  seal_id TEXT PRIMARY KEY,
  phase_id TEXT NOT NULL UNIQUE REFERENCES k0b02_phase_bindings(phase_id),
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64),
  predecessor_seal_id TEXT REFERENCES k0b02_phase_seals(seal_id),
  terminal_checkpoint_publication_id TEXT NOT NULL REFERENCES k0b02_publication_results(publication_id),
  terminal_checkpoint_sha256 TEXT NOT NULL CHECK(length(terminal_checkpoint_sha256)=64),
  ready_pair_set_sha256 TEXT NOT NULL CHECK(length(ready_pair_set_sha256)=64),
  outbox_high_water INTEGER NOT NULL CHECK(outbox_high_water>=0),
  cumulative_full_bytes INTEGER NOT NULL CHECK(cumulative_full_bytes>=0),
  publication_count INTEGER NOT NULL CHECK(publication_count>=0),
  authorities_json TEXT NOT NULL CHECK(json_valid(authorities_json)),
  all_admitted_members_terminal INTEGER NOT NULL CHECK(all_admitted_members_terminal=1),
  no_unresolved_begun_effects INTEGER NOT NULL CHECK(no_unresolved_begun_effects=1),
  result TEXT NOT NULL CHECK(result='sealed'),
  created_at TEXT NOT NULL
) STRICT;

CREATE TRIGGER k0b02_phase_seals_immutable_update BEFORE UPDATE ON k0b02_phase_seals BEGIN SELECT RAISE(ABORT,'k0b02_phase_seals immutable'); END;
CREATE TRIGGER k0b02_phase_seals_immutable_delete BEFORE DELETE ON k0b02_phase_seals BEGIN SELECT RAISE(ABORT,'k0b02_phase_seals immutable'); END;
