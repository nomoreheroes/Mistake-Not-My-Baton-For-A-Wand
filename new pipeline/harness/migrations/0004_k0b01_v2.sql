-- k0b01: create.runs
CREATE TABLE runs__k0b01_new (
    run_id TEXT PRIMARY KEY CHECK (length(run_id) > 0),
    profile TEXT NOT NULL CHECK (profile IN ('F00', 'Alpha0')),
    pipeline_commit TEXT NOT NULL
        CHECK (length(pipeline_commit) = 40 AND pipeline_commit = lower(pipeline_commit) AND pipeline_commit NOT GLOB '*[^0-9a-f]*'),
    fixture_commit TEXT NOT NULL
        CHECK (length(fixture_commit) = 40 AND fixture_commit = lower(fixture_commit) AND fixture_commit NOT GLOB '*[^0-9a-f]*'),
    fixture_tree TEXT NOT NULL
        CHECK (length(fixture_tree) = 40 AND fixture_tree = lower(fixture_tree) AND fixture_tree NOT GLOB '*[^0-9a-f]*'),
    state TEXT NOT NULL CHECK (state IN (
        'created', 'running', 'completed', 'blocked_input', 'blocked_policy',
        'failed_invocation', 'failed_validation', 'failed_persistence',
        'waiting', 'completing', 'reconciliation_required', 'reconciling', 'aborting', 'aborted', 'blocked', 'blocked_over_limit'
    )),
    state_revision INTEGER NOT NULL DEFAULT 0 CHECK (state_revision >= 0),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0)
) STRICT;

-- k0b01: create.events
CREATE TABLE events__k0b01_new (
    event_id TEXT PRIMARY KEY CHECK (length(event_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'command.received', 'run.started', 'artifact.version_created', 'handoff.ready', 'run.completed', 'run.blocked', 'run.abort_requested', 'run.aborted', 'artifact.published', 'projection.requested', 'projection.written', 'projection.failed', 'revision.requested', 'gate.passed', 'approval.requested', 'approval.granted', 'approval.rejected', 'error.schema_mismatch', 'error.tool_failure', 'error.security_policy', 'meta.incident_detected'
    )),
    event_version INTEGER NOT NULL CHECK (event_version = 1),
    initiated_by_invocation_id TEXT,
    artifact_version_id TEXT,
    caused_by_event_id TEXT,
    correlation_id TEXT NOT NULL CHECK (length(correlation_id) > 0),
    schema_id TEXT NOT NULL CHECK (length(schema_id) > 0),
    schema_version TEXT NOT NULL CHECK (length(schema_version) > 0),
    schema_sha256 TEXT NOT NULL
        CHECK (length(schema_sha256) = 64 AND schema_sha256 = lower(schema_sha256) AND schema_sha256 NOT GLOB '*[^0-9a-f]*'),
    payload_json TEXT NOT NULL CHECK (typeof(payload_json) = 'text' AND json_valid(payload_json)),
    payload_sha256 TEXT NOT NULL
        CHECK (length(payload_sha256) = 64 AND payload_sha256 = lower(payload_sha256) AND payload_sha256 NOT GLOB '*[^0-9a-f]*'),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) > 0),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (run_id, idempotency_key),
    UNIQUE (event_id, run_id),
    FOREIGN KEY (initiated_by_invocation_id, run_id)
        REFERENCES physical_invocations(invocation_id, run_id),
    FOREIGN KEY (artifact_version_id, run_id)
        REFERENCES artifact_versions(artifact_version_id, run_id),
    FOREIGN KEY (caused_by_event_id, run_id)
        REFERENCES events(event_id, run_id),
    CHECK (
        (
            event_type IN ('artifact.version_created', 'handoff.ready', 'artifact.published')
            AND artifact_version_id IS NOT NULL
            AND initiated_by_invocation_id IS NOT NULL
        )
        OR
        (
            event_type NOT IN ('artifact.version_created', 'handoff.ready', 'artifact.published')
            AND artifact_version_id IS NULL
        )
    )
) STRICT;

-- k0b01: create.run_state_transitions
CREATE TABLE run_state_transitions__k0b01_new (
    transition_id TEXT PRIMARY KEY CHECK (length(transition_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    from_state TEXT,
    to_state TEXT NOT NULL CHECK (to_state IN (
        'created', 'running', 'completed', 'blocked_input', 'blocked_policy',
        'failed_invocation', 'failed_validation', 'failed_persistence',
        'waiting', 'completing', 'reconciliation_required', 'reconciling', 'aborting', 'aborted', 'blocked', 'blocked_over_limit'
    )),
    from_revision INTEGER,
    to_revision INTEGER NOT NULL CHECK (to_revision >= 0),
    occurred_at TEXT NOT NULL CHECK (length(occurred_at) > 0),
    CHECK (
        (from_state IS NULL AND from_revision IS NULL AND to_state = 'created' AND to_revision = 0)
        OR
        (from_state IS NOT NULL AND from_revision IS NOT NULL AND to_revision = from_revision + 1)
    )
) STRICT;

-- k0b01: create.event_deliveries
CREATE TABLE event_deliveries__k0b01_new (
    event_delivery_id TEXT PRIMARY KEY CHECK (length(event_delivery_id) > 0),
    event_id TEXT NOT NULL REFERENCES events(event_id),
    subscriber_id TEXT NOT NULL CHECK (subscriber_id IN (
        'bootstrap_readback', 'bootstrap_sink', 'alpha_observation', 'artifact_event.projector', 'control.abort_coordinator', 'control.approval_coordinator', 'control.artifact_lifecycle', 'control.gate_delivery', 'control.handoff_delivery', 'control.projection_reconciliation', 'control.run_lifecycle', 'human_approval_queue', 'human_blocker_queue', 's.revision_coordinator', 's0_control_delivery', 'w5_incident_queue'
    )),
    terminal_policy TEXT NOT NULL CHECK (terminal_policy IN (
        'approval_delivery', 'artifact_delivery', 'block_run_and_enqueue_human', 'control_delivery', 'fixture_terminal', 'gate_delivery', 'human_approval_wait', 'observational_terminal', 'persist_incident_and_enqueue_W5', 'projection_delivery', 's_revision_delivery'
    )),
    state TEXT NOT NULL CHECK (state IN (
        'pending', 'accepted_terminal', 'rejected_terminal', 'observed_terminal'
    )),
    fields_read_json TEXT NOT NULL CHECK (typeof(fields_read_json) = 'text' AND json_valid(fields_read_json)),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (event_id, subscriber_id)
) STRICT;

-- k0b01: copy.runs
INSERT INTO runs__k0b01_new (run_id, profile, pipeline_commit, fixture_commit, fixture_tree, state, state_revision, created_at) SELECT run_id, profile, pipeline_commit, fixture_commit, fixture_tree, state, state_revision, created_at FROM runs;

-- k0b01: copy.events
INSERT INTO events__k0b01_new (event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, idempotency_key, created_at) SELECT event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, idempotency_key, created_at FROM events;

-- k0b01: copy.run_state_transitions
INSERT INTO run_state_transitions__k0b01_new (transition_id, run_id, from_state, to_state, from_revision, to_revision, occurred_at) SELECT transition_id, run_id, from_state, to_state, from_revision, to_revision, occurred_at FROM run_state_transitions;

-- k0b01: copy.event_deliveries
INSERT INTO event_deliveries__k0b01_new (event_delivery_id, event_id, subscriber_id, terminal_policy, state, fields_read_json, created_at) SELECT event_delivery_id, event_id, subscriber_id, terminal_policy, state, fields_read_json, created_at FROM event_deliveries;

-- k0b01: drop.event_deliveries
DROP TABLE event_deliveries;

-- k0b01: drop.run_state_transitions
DROP TABLE run_state_transitions;

-- k0b01: drop.events
DROP TABLE events;

-- k0b01: drop.runs
DROP TABLE runs;

-- k0b01: rename.runs
ALTER TABLE runs__k0b01_new RENAME TO runs;

-- k0b01: rename.events
ALTER TABLE events__k0b01_new RENAME TO events;

-- k0b01: rename.run_state_transitions
ALTER TABLE run_state_transitions__k0b01_new RENAME TO run_state_transitions;

-- k0b01: rename.event_deliveries
ALTER TABLE event_deliveries__k0b01_new RENAME TO event_deliveries;

-- k0b01: object.events_run_type_idx
CREATE INDEX events_run_type_idx ON events(run_id, event_type);

-- k0b01: object.event_deliveries_immutable_delete
CREATE TRIGGER event_deliveries_immutable_delete
BEFORE DELETE ON event_deliveries BEGIN SELECT RAISE(ABORT, 'event deliveries are immutable'); END;

-- k0b01: object.event_delivery_snapshot_immutable
CREATE TRIGGER event_delivery_snapshot_immutable
BEFORE UPDATE OF event_delivery_id, event_id, subscriber_id, terminal_policy, fields_read_json, created_at ON event_deliveries
BEGIN SELECT RAISE(ABORT, 'event delivery subscriber snapshot is immutable'); END;

-- k0b01: object.event_delivery_state_transition_is_exact
CREATE TRIGGER event_delivery_state_transition_is_exact
BEFORE UPDATE OF state ON event_deliveries
WHEN NOT (
    OLD.subscriber_id = 'bootstrap_sink'
    AND OLD.terminal_policy = 'fixture_terminal'
    AND OLD.state = 'pending'
    AND NEW.state = 'accepted_terminal'
) AND NOT (
    OLD.state = 'pending' AND NEW.state = 'accepted_terminal'
    AND OLD.subscriber_id NOT IN ('bootstrap_sink', 'bootstrap_readback')
    AND EXISTS (SELECT 1 FROM events AS event JOIN runs AS run ON run.run_id = event.run_id WHERE event.event_id = OLD.event_id AND run.profile = 'Alpha0')
)
BEGIN SELECT RAISE(ABORT, 'event delivery state transition is forbidden or terminal'); END;

-- k0b01: object.events_immutable_delete
CREATE TRIGGER events_immutable_delete
BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;

-- k0b01: object.events_immutable_update
CREATE TRIGGER events_immutable_update
BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;

-- k0b01: object.run_completed_event_requires_gate
CREATE TRIGGER run_completed_event_requires_gate
BEFORE INSERT ON events
WHEN NEW.event_type = 'run.completed' AND NOT EXISTS (
    SELECT 1 FROM runs AS run
    WHERE run.run_id = NEW.run_id AND run.state = 'completed' AND (
        (run.profile = 'F00' AND EXISTS (SELECT 1 FROM readback_gates AS gate WHERE gate.run_id = run.run_id AND gate.status = 'passed'))
        OR (run.profile = 'Alpha0' AND EXISTS (SELECT 1 FROM events AS gate WHERE gate.run_id = run.run_id AND gate.event_type = 'gate.passed' AND json_extract(gate.payload_json, '$.gate_id') IS NOT NULL))
    )
)
BEGIN SELECT RAISE(ABORT, 'run.completed requires completed gated run'); END;

-- k0b01: object.run_identity_immutable
CREATE TRIGGER run_identity_immutable
BEFORE UPDATE OF run_id, profile, pipeline_commit, fixture_commit, fixture_tree, created_at ON runs
BEGIN SELECT RAISE(ABORT, 'run identity and pins are immutable'); END;

-- k0b01: object.run_state_transitions_immutable_delete
CREATE TRIGGER run_state_transitions_immutable_delete
BEFORE DELETE ON run_state_transitions BEGIN SELECT RAISE(ABORT, 'run state transitions are immutable'); END;

-- k0b01: object.run_state_transitions_immutable_update
CREATE TRIGGER run_state_transitions_immutable_update
BEFORE UPDATE ON run_state_transitions BEGIN SELECT RAISE(ABORT, 'run state transitions are immutable'); END;

-- k0b01: object.runs_k0a02_blocks_completed_insert
CREATE TRIGGER runs_k0a02_blocks_completed_insert
BEFORE INSERT ON runs
WHEN NEW.state = 'completed'
BEGIN SELECT RAISE(ABORT, 'K0a-02 completed run cannot be inserted directly'); END;

-- k0b01: object.runs_k0a02_requires_completion_gate
CREATE TRIGGER runs_k0a02_requires_completion_gate
BEFORE UPDATE OF state ON runs
WHEN NEW.state = 'completed' AND NOT (
    (NEW.profile = 'F00' AND EXISTS (SELECT 1 FROM readback_gates AS gate WHERE gate.run_id = NEW.run_id AND gate.status = 'passed'))
    OR (NEW.profile = 'Alpha0' AND EXISTS (SELECT 1 FROM events AS gate WHERE gate.run_id = NEW.run_id AND gate.event_type = 'gate.passed' AND json_extract(gate.payload_json, '$.gate_id') IS NOT NULL))
)
BEGIN SELECT RAISE(ABORT, 'K0a-02 completion requires accepted sink and gate-bearing readback'); END;

-- k0b01: object.alpha_contract_bindings
CREATE TABLE alpha_contract_bindings (binding_id TEXT PRIMARY KEY, contract_id TEXT NOT NULL, contract_version TEXT NOT NULL, contract_sha256 TEXT NOT NULL, profile_id TEXT NOT NULL, UNIQUE(contract_id, contract_version, profile_id), CHECK(length(binding_id)>0), CHECK(length(contract_id)>0), CHECK(length(contract_sha256)=64 AND contract_sha256=lower(contract_sha256) AND contract_sha256 NOT GLOB '*[^0-9a-f]*'), CHECK(length(profile_id)>0)) STRICT;

-- k0b01: object.alpha_contract_bindings_immutable_update
CREATE TRIGGER alpha_contract_bindings_immutable_update BEFORE UPDATE ON alpha_contract_bindings BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_contract_bindings_immutable_delete
CREATE TRIGGER alpha_contract_bindings_immutable_delete BEFORE DELETE ON alpha_contract_bindings BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_source_profiles
CREATE TABLE alpha_source_profiles (source_profile_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL, source_json TEXT NOT NULL CHECK(json_valid(source_json)), runtime_enabled INTEGER NOT NULL CHECK(runtime_enabled=0), CHECK(length(source_profile_id)>0), CHECK(length(source_sha256)=64 AND source_sha256=lower(source_sha256) AND source_sha256 NOT GLOB '*[^0-9a-f]*')) STRICT;

-- k0b01: object.alpha_source_profiles_immutable_update
CREATE TRIGGER alpha_source_profiles_immutable_update BEFORE UPDATE ON alpha_source_profiles BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_source_profiles_immutable_delete
CREATE TRIGGER alpha_source_profiles_immutable_delete BEFORE DELETE ON alpha_source_profiles BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiled_profiles
CREATE TABLE alpha_compiled_profiles (compiled_profile_id TEXT PRIMARY KEY, source_profile_id TEXT NOT NULL REFERENCES alpha_source_profiles(source_profile_id), compiled_sha256 TEXT NOT NULL, compiled_json TEXT NOT NULL CHECK(json_valid(compiled_json)), runtime_enabled INTEGER NOT NULL CHECK(runtime_enabled=0), CHECK(length(compiled_profile_id)>0), CHECK(length(source_profile_id)>0), CHECK(length(compiled_sha256)=64 AND compiled_sha256=lower(compiled_sha256) AND compiled_sha256 NOT GLOB '*[^0-9a-f]*')) STRICT;

-- k0b01: object.alpha_compiled_profiles_immutable_update
CREATE TRIGGER alpha_compiled_profiles_immutable_update BEFORE UPDATE ON alpha_compiled_profiles BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiled_profiles_immutable_delete
CREATE TRIGGER alpha_compiled_profiles_immutable_delete BEFORE DELETE ON alpha_compiled_profiles BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiler_receipts
CREATE TABLE alpha_compiler_receipts (receipt_id TEXT PRIMARY KEY, compiled_profile_id TEXT NOT NULL REFERENCES alpha_compiled_profiles(compiled_profile_id), compiler_id TEXT NOT NULL, compiler_sha256 TEXT NOT NULL, receipt_sha256 TEXT NOT NULL, result TEXT NOT NULL CHECK(result='pass'), CHECK(length(receipt_id)>0), CHECK(length(compiled_profile_id)>0), CHECK(length(compiler_id)>0), CHECK(length(compiler_sha256)=64 AND compiler_sha256=lower(compiler_sha256) AND compiler_sha256 NOT GLOB '*[^0-9a-f]*'), CHECK(length(receipt_sha256)=64 AND receipt_sha256=lower(receipt_sha256) AND receipt_sha256 NOT GLOB '*[^0-9a-f]*')) STRICT;

-- k0b01: object.alpha_compiler_receipts_immutable_update
CREATE TRIGGER alpha_compiler_receipts_immutable_update BEFORE UPDATE ON alpha_compiler_receipts BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiler_receipts_immutable_delete
CREATE TRIGGER alpha_compiler_receipts_immutable_delete BEFORE DELETE ON alpha_compiler_receipts BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiled_output_families
CREATE TABLE alpha_compiled_output_families (output_id TEXT PRIMARY KEY, receipt_id TEXT NOT NULL REFERENCES alpha_compiler_receipts(receipt_id), family TEXT NOT NULL, payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), UNIQUE(receipt_id, family), CHECK(length(output_id)>0), CHECK(length(receipt_id)>0), CHECK(length(payload_sha256)=64 AND payload_sha256=lower(payload_sha256) AND payload_sha256 NOT GLOB '*[^0-9a-f]*')) STRICT;

-- k0b01: object.alpha_compiled_output_families_immutable_update
CREATE TRIGGER alpha_compiled_output_families_immutable_update BEFORE UPDATE ON alpha_compiled_output_families BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_compiled_output_families_immutable_delete
CREATE TRIGGER alpha_compiled_output_families_immutable_delete BEFORE DELETE ON alpha_compiled_output_families BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_human_terminal_queue
CREATE TABLE alpha_human_terminal_queue (queue_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id), terminal_policy TEXT NOT NULL CHECK(terminal_policy IN ('block_run_and_enqueue_human','human_approval_wait')), evidence_ref TEXT NOT NULL CHECK(length(evidence_ref)>0), status TEXT NOT NULL CHECK(status='pending_human'), CHECK(length(queue_id)>0), CHECK(length(event_id)>0)) STRICT;

-- k0b01: object.alpha_human_terminal_queue_immutable_update
CREATE TRIGGER alpha_human_terminal_queue_immutable_update BEFORE UPDATE ON alpha_human_terminal_queue BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_human_terminal_queue_immutable_delete
CREATE TRIGGER alpha_human_terminal_queue_immutable_delete BEFORE DELETE ON alpha_human_terminal_queue BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_w5_terminal_queue
CREATE TABLE alpha_w5_terminal_queue (queue_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id), terminal_policy TEXT NOT NULL CHECK(terminal_policy='persist_incident_and_enqueue_W5'), evidence_ref TEXT NOT NULL CHECK(length(evidence_ref)>0), status TEXT NOT NULL CHECK(status='pending_W5'), CHECK(length(queue_id)>0), CHECK(length(event_id)>0)) STRICT;

-- k0b01: object.alpha_w5_terminal_queue_immutable_update
CREATE TRIGGER alpha_w5_terminal_queue_immutable_update BEFORE UPDATE ON alpha_w5_terminal_queue BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;

-- k0b01: object.alpha_w5_terminal_queue_immutable_delete
CREATE TRIGGER alpha_w5_terminal_queue_immutable_delete BEFORE DELETE ON alpha_w5_terminal_queue BEGIN SELECT RAISE(ABORT, 'Alpha definitions and terminal evidence are immutable'); END;
