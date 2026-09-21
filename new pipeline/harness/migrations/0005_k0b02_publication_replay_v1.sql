PRAGMA foreign_keys=ON;

CREATE TABLE k0b02_source_sequences (
  run_id TEXT PRIMARY KEY,
  next_source_seq INTEGER NOT NULL CHECK(next_source_seq>=1),
  receipt_high_water INTEGER NOT NULL DEFAULT 0 CHECK(receipt_high_water>=0)
) STRICT;

CREATE TABLE k0b02_decision_versions (
  decision_version_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  phase_id TEXT NOT NULL,
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64),
  source_seq INTEGER NOT NULL CHECK(source_seq>=1),
  canonical_sha256 TEXT NOT NULL CHECK(length(canonical_sha256)=64),
  canonical_json TEXT NOT NULL CHECK(json_valid(canonical_json)),
  created_at TEXT NOT NULL,
  UNIQUE(run_id,source_seq),
  UNIQUE(run_id,canonical_sha256)
) STRICT;

CREATE TABLE k0b02_projection_outbox (
  outbox_id TEXT PRIMARY KEY,
  decision_version_id TEXT NOT NULL UNIQUE REFERENCES k0b02_decision_versions(decision_version_id),
  run_id TEXT NOT NULL,
  source_seq INTEGER NOT NULL CHECK(source_seq>=1),
  projection_profile_sha256 TEXT NOT NULL CHECK(length(projection_profile_sha256)=64),
  pair_stem TEXT NOT NULL CHECK(pair_stem='fixture-decision'),
  requested_event_json TEXT NOT NULL CHECK(json_valid(requested_event_json)),
  status TEXT NOT NULL CHECK(status IN ('pending','claimed','written','failed')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_projection_attempts (
  attempt_id TEXT PRIMARY KEY,
  outbox_id TEXT NOT NULL REFERENCES k0b02_projection_outbox(outbox_id),
  attempt_no INTEGER NOT NULL CHECK(attempt_no>=1),
  status TEXT NOT NULL CHECK(status IN ('begun','written','failed')),
  evidence_ref TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(outbox_id,attempt_no)
) STRICT;

CREATE TABLE k0b02_projection_pairs (
  projection_id TEXT PRIMARY KEY,
  outbox_id TEXT NOT NULL UNIQUE REFERENCES k0b02_projection_outbox(outbox_id),
  decision_version_id TEXT NOT NULL REFERENCES k0b02_decision_versions(decision_version_id),
  run_id TEXT NOT NULL,
  source_seq INTEGER NOT NULL CHECK(source_seq>=1),
  pair_stem TEXT NOT NULL CHECK(pair_stem='fixture-decision'),
  projection_profile_sha256 TEXT NOT NULL CHECK(length(projection_profile_sha256)=64),
  yaml_sha256 TEXT NOT NULL CHECK(length(yaml_sha256)=64),
  markdown_sha256 TEXT NOT NULL CHECK(length(markdown_sha256)=64),
  ready INTEGER NOT NULL CHECK(ready IN (0,1)),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_projection_results (
  result_id TEXT PRIMARY KEY,
  outbox_id TEXT NOT NULL UNIQUE REFERENCES k0b02_projection_outbox(outbox_id),
  projection_id TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('written','failed')),
  event_json TEXT NOT NULL CHECK(json_valid(event_json)),
  receipt_seq INTEGER NOT NULL CHECK(receipt_seq>=1),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_publication_intents (
  publication_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  phase_id TEXT NOT NULL,
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64),
  source_seq INTEGER NOT NULL CHECK(source_seq>=1),
  receipt_high_water INTEGER NOT NULL CHECK(receipt_high_water>=0),
  outbox_high_water INTEGER NOT NULL CHECK(outbox_high_water>=0),
  ready_pair_set_sha256 TEXT NOT NULL CHECK(length(ready_pair_set_sha256)=64),
  expected_git_parent TEXT NOT NULL,
  predecessor_publication_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('begun','committed','blocked')),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_publication_attempts (
  attempt_id TEXT PRIMARY KEY,
  publication_id TEXT NOT NULL REFERENCES k0b02_publication_intents(publication_id),
  boundary TEXT NOT NULL,
  durable_marker_sha256 TEXT,
  effect_commit TEXT,
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_publication_results (
  publication_id TEXT PRIMARY KEY REFERENCES k0b02_publication_intents(publication_id),
  snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
  snapshot_bytes INTEGER NOT NULL CHECK(snapshot_bytes>0),
  git_commit TEXT NOT NULL,
  git_tree TEXT NOT NULL,
  predecessor_commit TEXT,
  result TEXT NOT NULL CHECK(result='committed'),
  receipt_seq INTEGER NOT NULL CHECK(receipt_seq>=1),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_replay_envelopes (
  envelope_id TEXT PRIMARY KEY,
  envelope_sha256 TEXT NOT NULL UNIQUE CHECK(length(envelope_sha256)=64),
  envelope_json TEXT NOT NULL CHECK(json_valid(envelope_json)),
  run_chain_identity TEXT NOT NULL,
  partition_digest TEXT NOT NULL CHECK(length(partition_digest)=64),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_replay_results (
  replay_id TEXT PRIMARY KEY,
  envelope_id TEXT NOT NULL REFERENCES k0b02_replay_envelopes(envelope_id),
  publication_id TEXT NOT NULL REFERENCES k0b02_publication_results(publication_id),
  new_restore_target TEXT NOT NULL,
  verified_content_digest TEXT NOT NULL CHECK(length(verified_content_digest)=64),
  reproducibility_gap TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('pass','blocked')),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE k0b02_compiler_bindings (
  binding_id TEXT PRIMARY KEY,
  integrated_manifest_sha256 TEXT NOT NULL CHECK(length(integrated_manifest_sha256)=64),
  output_hashes_json TEXT NOT NULL CHECK(json_valid(output_hashes_json)),
  output_count INTEGER NOT NULL CHECK(output_count=9),
  runtime_enabled INTEGER NOT NULL CHECK(runtime_enabled=0),
  created_at TEXT NOT NULL
) STRICT;

CREATE TRIGGER k0b02_decision_versions_immutable_update BEFORE UPDATE ON k0b02_decision_versions BEGIN SELECT RAISE(ABORT,'k0b02_decision_versions immutable'); END;
CREATE TRIGGER k0b02_decision_versions_immutable_delete BEFORE DELETE ON k0b02_decision_versions BEGIN SELECT RAISE(ABORT,'k0b02_decision_versions immutable'); END;
CREATE TRIGGER k0b02_projection_results_immutable_update BEFORE UPDATE ON k0b02_projection_results BEGIN SELECT RAISE(ABORT,'k0b02_projection_results immutable'); END;
CREATE TRIGGER k0b02_projection_results_immutable_delete BEFORE DELETE ON k0b02_projection_results BEGIN SELECT RAISE(ABORT,'k0b02_projection_results immutable'); END;
CREATE TRIGGER k0b02_publication_results_immutable_update BEFORE UPDATE ON k0b02_publication_results BEGIN SELECT RAISE(ABORT,'k0b02_publication_results immutable'); END;
CREATE TRIGGER k0b02_publication_results_immutable_delete BEFORE DELETE ON k0b02_publication_results BEGIN SELECT RAISE(ABORT,'k0b02_publication_results immutable'); END;
CREATE TRIGGER k0b02_replay_envelopes_immutable_update BEFORE UPDATE ON k0b02_replay_envelopes BEGIN SELECT RAISE(ABORT,'k0b02_replay_envelopes immutable'); END;
CREATE TRIGGER k0b02_replay_envelopes_immutable_delete BEFORE DELETE ON k0b02_replay_envelopes BEGIN SELECT RAISE(ABORT,'k0b02_replay_envelopes immutable'); END;
