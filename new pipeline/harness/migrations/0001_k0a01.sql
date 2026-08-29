CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL
        CHECK (length(sha256) = 64 AND sha256 = lower(sha256) AND sha256 NOT GLOB '*[^0-9a-f]*')
) STRICT;

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY CHECK (length(run_id) > 0),
    profile TEXT NOT NULL CHECK (profile = 'F00'),
    pipeline_commit TEXT NOT NULL
        CHECK (length(pipeline_commit) = 40 AND pipeline_commit = lower(pipeline_commit) AND pipeline_commit NOT GLOB '*[^0-9a-f]*'),
    fixture_commit TEXT NOT NULL
        CHECK (length(fixture_commit) = 40 AND fixture_commit = lower(fixture_commit) AND fixture_commit NOT GLOB '*[^0-9a-f]*'),
    fixture_tree TEXT NOT NULL
        CHECK (length(fixture_tree) = 40 AND fixture_tree = lower(fixture_tree) AND fixture_tree NOT GLOB '*[^0-9a-f]*'),
    state TEXT NOT NULL CHECK (state IN (
        'created', 'running', 'completed', 'blocked_input', 'blocked_policy',
        'failed_invocation', 'failed_validation', 'failed_persistence'
    )),
    state_revision INTEGER NOT NULL DEFAULT 0 CHECK (state_revision >= 0),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0)
) STRICT;

CREATE TABLE run_state_transitions (
    transition_id TEXT PRIMARY KEY CHECK (length(transition_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    from_state TEXT,
    to_state TEXT NOT NULL CHECK (to_state IN (
        'created', 'running', 'completed', 'blocked_input', 'blocked_policy',
        'failed_invocation', 'failed_validation', 'failed_persistence'
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

CREATE TABLE deliveries (
    delivery_id TEXT PRIMARY KEY CHECK (length(delivery_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    delivery_key TEXT NOT NULL CHECK (length(delivery_key) > 0),
    role TEXT NOT NULL CHECK (role IN ('S0', 'synthetic_Layer0', 'fixture_worker')),
    triggering_event_id TEXT,
    state TEXT NOT NULL CHECK (state IN (
        'pending_preflight', 'preflight_passed', 'evaluating', 'result_validated',
        'retry_pending', 'published', 'failed_validation', 'failed_invocation'
    )),
    current_physical_invocation_id TEXT,
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (run_id, delivery_key),
    UNIQUE (delivery_id, run_id),
    FOREIGN KEY (triggering_event_id, run_id)
        REFERENCES events(event_id, run_id),
    FOREIGN KEY (current_physical_invocation_id, delivery_id, run_id)
        REFERENCES physical_invocations(invocation_id, delivery_id, run_id)
        DEFERRABLE INITIALLY DEFERRED
) STRICT;

CREATE TABLE physical_invocations (
    invocation_id TEXT PRIMARY KEY CHECK (length(invocation_id) > 0),
    delivery_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number IN (1, 2)),
    state TEXT NOT NULL CHECK (state IN (
        'prepared', 'replay_before_committed', 'dispatched', 'response_captured',
        'validated', 'replay_after_committed', 'published', 'failed_invocation'
    )),
    prompt_id TEXT NOT NULL CHECK (length(prompt_id) > 0),
    prompt_version TEXT NOT NULL CHECK (length(prompt_version) > 0),
    prompt_sha256 TEXT NOT NULL
        CHECK (length(prompt_sha256) = 64 AND prompt_sha256 = lower(prompt_sha256) AND prompt_sha256 NOT GLOB '*[^0-9a-f]*'),
    contract_id TEXT NOT NULL CHECK (length(contract_id) > 0),
    contract_version TEXT NOT NULL CHECK (length(contract_version) > 0),
    contract_sha256 TEXT NOT NULL
        CHECK (length(contract_sha256) = 64 AND contract_sha256 = lower(contract_sha256) AND contract_sha256 NOT GLOB '*[^0-9a-f]*'),
    result_schema_id TEXT NOT NULL CHECK (length(result_schema_id) > 0),
    result_schema_version TEXT NOT NULL CHECK (length(result_schema_version) > 0),
    result_schema_sha256 TEXT NOT NULL
        CHECK (length(result_schema_sha256) = 64 AND result_schema_sha256 = lower(result_schema_sha256) AND result_schema_sha256 NOT GLOB '*[^0-9a-f]*'),
    registry_sha256 TEXT NOT NULL
        CHECK (length(registry_sha256) = 64 AND registry_sha256 = lower(registry_sha256) AND registry_sha256 NOT GLOB '*[^0-9a-f]*'),
    provider TEXT NOT NULL CHECK (length(provider) > 0),
    model_profile TEXT NOT NULL CHECK (length(model_profile) > 0),
    model_identifier TEXT,
    parameters_json TEXT NOT NULL CHECK (typeof(parameters_json) = 'text' AND json_valid(parameters_json)),
    context_limit_tokens INTEGER NOT NULL CHECK (context_limit_tokens > 0),
    response_accepted INTEGER NOT NULL DEFAULT 0 CHECK (response_accepted IN (0, 1)),
    fenced INTEGER NOT NULL DEFAULT 0 CHECK (fenced IN (0, 1)),
    failure_code TEXT CHECK (failure_code IN (
        'transient_unavailable_before_dispatch_ack',
        'timeout_before_accepted_response',
        'non_retriable_provider_failure'
    )),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (delivery_id, attempt_number),
    UNIQUE (invocation_id, delivery_id),
    UNIQUE (invocation_id, run_id),
    UNIQUE (invocation_id, delivery_id, run_id),
    FOREIGN KEY (delivery_id, run_id) REFERENCES deliveries(delivery_id, run_id),
    CHECK (
        (state = 'failed_invocation' AND failure_code IS NOT NULL AND response_accepted = 0)
        OR
        (state <> 'failed_invocation' AND failure_code IS NULL)
    )
) STRICT;

CREATE TABLE invocation_state_transitions (
    transition_id TEXT PRIMARY KEY CHECK (length(transition_id) > 0),
    invocation_id TEXT NOT NULL REFERENCES physical_invocations(invocation_id),
    from_state TEXT,
    to_state TEXT NOT NULL CHECK (to_state IN (
        'prepared', 'replay_before_committed', 'dispatched', 'response_captured',
        'validated', 'replay_after_committed', 'published', 'failed_invocation'
    )),
    occurred_at TEXT NOT NULL CHECK (length(occurred_at) > 0)
) STRICT;

CREATE TABLE invocation_telemetry (
    telemetry_id TEXT PRIMARY KEY CHECK (length(telemetry_id) > 0),
    invocation_id TEXT NOT NULL UNIQUE REFERENCES physical_invocations(invocation_id),
    provider TEXT NOT NULL CHECK (length(provider) > 0),
    model_profile TEXT NOT NULL CHECK (length(model_profile) > 0),
    model_identifier TEXT,
    parameters_json TEXT NOT NULL CHECK (typeof(parameters_json) = 'text' AND json_valid(parameters_json)),
    response_text TEXT NOT NULL CHECK (typeof(response_text) = 'text'),
    response_sha256 TEXT NOT NULL
        CHECK (length(response_sha256) = 64 AND response_sha256 = lower(response_sha256) AND response_sha256 NOT GLOB '*[^0-9a-f]*'),
    started_at TEXT NOT NULL CHECK (length(started_at) > 0),
    completed_at TEXT NOT NULL CHECK (length(completed_at) > 0),
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    monotonic_started_ns INTEGER NOT NULL CHECK (monotonic_started_ns >= 0),
    monotonic_completed_ns INTEGER NOT NULL CHECK (monotonic_completed_ns >= monotonic_started_ns),
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    total_tokens INTEGER NOT NULL CHECK (total_tokens = input_tokens + output_tokens),
    usage_json TEXT NOT NULL CHECK (
        typeof(usage_json) = 'text'
        AND json_valid(usage_json)
        AND json_type(usage_json) = 'object'
        AND json_type(usage_json, '$.input_tokens') = 'integer'
        AND json_type(usage_json, '$.output_tokens') = 'integer'
        AND json_type(usage_json, '$.total_tokens') = 'integer'
    ),
    finish_reason TEXT,
    UNIQUE (telemetry_id, invocation_id, response_text, response_sha256),
    CHECK (duration_ms = CAST((monotonic_completed_ns - monotonic_started_ns) / 1000000 AS INTEGER))
) STRICT;

CREATE TABLE replay_points (
    replay_point_id TEXT PRIMARY KEY CHECK (length(replay_point_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    delivery_id TEXT NOT NULL,
    invocation_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number IN (1, 2)),
    position TEXT NOT NULL CHECK (position IN ('before', 'after')),
    sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
    pipeline_commit TEXT NOT NULL,
    fixture_commit TEXT NOT NULL,
    fixture_tree TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    contract_sha256 TEXT NOT NULL,
    result_schema_id TEXT NOT NULL,
    result_schema_version TEXT NOT NULL,
    result_schema_sha256 TEXT NOT NULL,
    registry_sha256 TEXT NOT NULL,
    context_text TEXT NOT NULL CHECK (typeof(context_text) = 'text'),
    context_sha256 TEXT NOT NULL
        CHECK (length(context_sha256) = 64 AND context_sha256 = lower(context_sha256) AND context_sha256 NOT GLOB '*[^0-9a-f]*'),
    context_fragments_json TEXT NOT NULL CHECK (
        typeof(context_fragments_json) = 'text'
        AND json_valid(context_fragments_json)
        AND json_type(context_fragments_json) = 'array'
        AND json_array_length(context_fragments_json) > 0
    ),
    fragment_count INTEGER NOT NULL CHECK (fragment_count > 0),
    provider TEXT NOT NULL,
    model_profile TEXT NOT NULL,
    model_identifier TEXT,
    parameters_json TEXT NOT NULL CHECK (typeof(parameters_json) = 'text' AND json_valid(parameters_json)),
    capabilities_json TEXT NOT NULL CHECK (
        typeof(capabilities_json) = 'text'
        AND json_valid(capabilities_json)
        AND json_type(capabilities_json) = 'object'
        AND json_type(capabilities_json, '$.policy_version') = 'text'
        AND json_type(capabilities_json, '$.model_channel') = 'text'
        AND json_type(capabilities_json, '$.filesystem_roots') = 'array'
        AND json_type(capabilities_json, '$.tools') = 'array'
    ),
    environment_json TEXT NOT NULL CHECK (
        typeof(environment_json) = 'text'
        AND json_valid(environment_json)
        AND json_type(environment_json) = 'object'
        AND json_type(environment_json, '$.os') = 'text'
        AND json_type(environment_json, '$.architecture') = 'text'
        AND json_type(environment_json, '$.locale') = 'text'
        AND json_type(environment_json, '$.timezone') = 'text'
        AND json_type(environment_json, '$.harness_version') = 'text'
        AND json_type(environment_json, '$.adapter_version') = 'text'
        AND json_type(environment_json, '$.tool_registry_version') = 'text'
        AND json_type(environment_json, '$.clock_binding') = 'text'
        AND json_type(environment_json, '$.random_seed') IN ('integer', 'null')
        AND json_type(environment_json, '$.dependency_lock_sha256') = 'text'
        AND json_type(environment_json, '$.config_sha256') = 'text'
    ),
    capture_completeness TEXT NOT NULL CHECK (capture_completeness IN ('complete_harness_visible', 'typed_gap')),
    gap_code TEXT,
    result_text TEXT CHECK (result_text IS NULL OR typeof(result_text) = 'text'),
    result_sha256 TEXT,
    telemetry_id TEXT,
    envelope_json TEXT NOT NULL CHECK (typeof(envelope_json) = 'text' AND json_valid(envelope_json)),
    envelope_sha256 TEXT NOT NULL
        CHECK (length(envelope_sha256) = 64 AND envelope_sha256 = lower(envelope_sha256) AND envelope_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (invocation_id, position),
    UNIQUE (run_id, sequence_number),
    FOREIGN KEY (delivery_id, run_id) REFERENCES deliveries(delivery_id, run_id),
    FOREIGN KEY (invocation_id, delivery_id, run_id)
        REFERENCES physical_invocations(invocation_id, delivery_id, run_id),
    FOREIGN KEY (telemetry_id, invocation_id, result_text, result_sha256)
        REFERENCES invocation_telemetry(telemetry_id, invocation_id, response_text, response_sha256),
    CHECK (
        (capture_completeness = 'complete_harness_visible' AND gap_code IS NULL)
        OR
        (capture_completeness = 'typed_gap' AND gap_code IS NOT NULL)
    ),
    CHECK (
        (position = 'before' AND result_text IS NULL AND result_sha256 IS NULL AND telemetry_id IS NULL)
        OR
        (position = 'after' AND result_text IS NOT NULL AND result_sha256 IS NOT NULL AND telemetry_id IS NOT NULL)
    ),
    CHECK (fragment_count = json_array_length(context_fragments_json))
) STRICT;

CREATE TABLE replay_context_fragments (
    replay_point_id TEXT NOT NULL REFERENCES replay_points(replay_point_id),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    role TEXT NOT NULL CHECK (role IN ('system', 'developer', 'user', 'assistant', 'tool')),
    content_text TEXT NOT NULL CHECK (typeof(content_text) = 'text'),
    content_sha256 TEXT NOT NULL
        CHECK (length(content_sha256) = 64 AND content_sha256 = lower(content_sha256) AND content_sha256 NOT GLOB '*[^0-9a-f]*'),
    PRIMARY KEY (replay_point_id, ordinal)
) STRICT;

CREATE TABLE route_proposals (
    proposal_id TEXT PRIMARY KEY CHECK (length(proposal_id) > 0),
    delivery_id TEXT NOT NULL REFERENCES deliveries(delivery_id),
    invocation_id TEXT NOT NULL UNIQUE,
    raw_output_type TEXT NOT NULL CHECK (raw_output_type IN (
        's0_route_proposal', 'semantic_blocker', 'abstention', 'malformed_or_forbidden'
    )),
    raw_output_text TEXT NOT NULL CHECK (typeof(raw_output_text) = 'text'),
    raw_output_sha256 TEXT NOT NULL
        CHECK (length(raw_output_sha256) = 64 AND raw_output_sha256 = lower(raw_output_sha256) AND raw_output_sha256 NOT GLOB '*[^0-9a-f]*'),
    validation_disposition TEXT NOT NULL CHECK (validation_disposition IN ('accepted', 'rejected')),
    persisted_output_type TEXT,
    terminal_state TEXT,
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    FOREIGN KEY (invocation_id, delivery_id)
        REFERENCES physical_invocations(invocation_id, delivery_id),
    CHECK (
        (
            raw_output_type = 's0_route_proposal'
            AND validation_disposition = 'accepted'
            AND persisted_output_type = 'validated_route_proposal'
            AND terminal_state IS NULL
        )
        OR
        (
            validation_disposition = 'rejected'
            AND persisted_output_type IS NULL
            AND terminal_state = 'failed_validation'
        )
    )
) STRICT;

CREATE TABLE route_proposal_consumptions (
    consumption_id TEXT PRIMARY KEY CHECK (length(consumption_id) > 0),
    proposal_id TEXT NOT NULL UNIQUE REFERENCES route_proposals(proposal_id),
    downstream_invocation_id TEXT NOT NULL UNIQUE REFERENCES physical_invocations(invocation_id),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0)
) STRICT;

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY CHECK (length(artifact_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    artifact_type TEXT NOT NULL CHECK (artifact_type = 'bootstrap.synthetic_result'),
    logical_owner TEXT NOT NULL CHECK (logical_owner = 'fixture.bootstrap_worker'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (artifact_id, run_id)
) STRICT;

CREATE TABLE artifact_versions (
    artifact_version_id TEXT PRIMARY KEY CHECK (length(artifact_version_id) > 0),
    artifact_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    producing_invocation_id TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK (media_type IN ('text/plain', 'application/json')),
    encoding TEXT NOT NULL CHECK (encoding = 'utf-8'),
    schema_id TEXT NOT NULL CHECK (length(schema_id) > 0),
    schema_version TEXT NOT NULL CHECK (length(schema_version) > 0),
    schema_sha256 TEXT NOT NULL
        CHECK (length(schema_sha256) = 64 AND schema_sha256 = lower(schema_sha256) AND schema_sha256 NOT GLOB '*[^0-9a-f]*'),
    hash_profile_id TEXT NOT NULL CHECK (hash_profile_id = 'sha256-utf8-v1'),
    content_text TEXT NOT NULL CHECK (typeof(content_text) = 'text'),
    content_sha256 TEXT NOT NULL
        CHECK (length(content_sha256) = 64 AND content_sha256 = lower(content_sha256) AND content_sha256 NOT GLOB '*[^0-9a-f]*'),
    content_size_bytes INTEGER NOT NULL CHECK (content_size_bytes >= 0),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) > 0),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (run_id, idempotency_key),
    UNIQUE (artifact_version_id, run_id),
    FOREIGN KEY (artifact_id, run_id) REFERENCES artifacts(artifact_id, run_id),
    FOREIGN KEY (producing_invocation_id, run_id)
        REFERENCES physical_invocations(invocation_id, run_id),
    CHECK (length(CAST(content_text AS BLOB)) = content_size_bytes)
) STRICT;

CREATE TABLE artifact_version_lineage (
    lineage_id TEXT PRIMARY KEY CHECK (length(lineage_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    child_artifact_version_id TEXT NOT NULL,
    parent_ref_kind TEXT NOT NULL CHECK (parent_ref_kind IN ('artifact_version', 'fixture_input')),
    parent_artifact_version_id TEXT,
    parent_external_ref TEXT,
    relation TEXT NOT NULL CHECK (relation IN ('derived_from', 'produced_from')),
    FOREIGN KEY (child_artifact_version_id, run_id)
        REFERENCES artifact_versions(artifact_version_id, run_id),
    FOREIGN KEY (parent_artifact_version_id, run_id)
        REFERENCES artifact_versions(artifact_version_id, run_id),
    CHECK (
        (parent_ref_kind = 'artifact_version' AND parent_artifact_version_id IS NOT NULL AND parent_external_ref IS NULL)
        OR
        (parent_ref_kind = 'fixture_input' AND parent_artifact_version_id IS NULL AND parent_external_ref IS NOT NULL)
    )
) STRICT;

CREATE TABLE events (
    event_id TEXT PRIMARY KEY CHECK (length(event_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'command.received', 'run.started', 'artifact.version_created', 'handoff.ready', 'run.completed'
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
            event_type IN ('artifact.version_created', 'handoff.ready')
            AND artifact_version_id IS NOT NULL
            AND initiated_by_invocation_id IS NOT NULL
        )
        OR
        (
            event_type NOT IN ('artifact.version_created', 'handoff.ready')
            AND artifact_version_id IS NULL
        )
    )
) STRICT;

CREATE TABLE event_deliveries (
    event_delivery_id TEXT PRIMARY KEY CHECK (length(event_delivery_id) > 0),
    event_id TEXT NOT NULL REFERENCES events(event_id),
    subscriber_id TEXT NOT NULL CHECK (subscriber_id IN (
        's0_control_delivery', 'bootstrap_readback', 'bootstrap_sink'
    )),
    terminal_policy TEXT NOT NULL CHECK (terminal_policy IN (
        'control_delivery', 'observational_terminal', 'fixture_terminal'
    )),
    state TEXT NOT NULL CHECK (state IN (
        'pending', 'accepted_terminal', 'rejected_terminal', 'observed_terminal'
    )),
    fields_read_json TEXT NOT NULL CHECK (typeof(fields_read_json) = 'text' AND json_valid(fields_read_json)),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (event_id, subscriber_id)
) STRICT;

CREATE TABLE publication_transactions (
    publication_transaction_id TEXT PRIMARY KEY CHECK (length(publication_transaction_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    invocation_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) > 0),
    request_sha256 TEXT NOT NULL
        CHECK (length(request_sha256) = 64 AND request_sha256 = lower(request_sha256) AND request_sha256 NOT GLOB '*[^0-9a-f]*'),
    artifact_version_id TEXT NOT NULL UNIQUE,
    version_created_event_id TEXT NOT NULL UNIQUE,
    handoff_event_id TEXT NOT NULL UNIQUE,
    expected_run_revision INTEGER NOT NULL CHECK (expected_run_revision >= 0),
    committed_run_revision INTEGER NOT NULL CHECK (committed_run_revision = expected_run_revision + 1),
    committed_at TEXT NOT NULL CHECK (length(committed_at) > 0),
    FOREIGN KEY (invocation_id, run_id)
        REFERENCES physical_invocations(invocation_id, run_id),
    FOREIGN KEY (artifact_version_id, run_id)
        REFERENCES artifact_versions(artifact_version_id, run_id),
    FOREIGN KEY (version_created_event_id, run_id)
        REFERENCES events(event_id, run_id),
    FOREIGN KEY (handoff_event_id, run_id)
        REFERENCES events(event_id, run_id)
) STRICT;

CREATE INDEX replay_points_run_sequence_idx ON replay_points(run_id, sequence_number);
CREATE INDEX events_run_type_idx ON events(run_id, event_type);
CREATE INDEX artifact_versions_run_idx ON artifact_versions(run_id, artifact_version_id);
CREATE INDEX invocation_delivery_attempt_idx ON physical_invocations(delivery_id, attempt_number);

CREATE TRIGGER replay_points_immutable_update
BEFORE UPDATE ON replay_points BEGIN SELECT RAISE(ABORT, 'replay_points are immutable'); END;
CREATE TRIGGER replay_points_immutable_delete
BEFORE DELETE ON replay_points BEGIN SELECT RAISE(ABORT, 'replay_points are immutable'); END;
CREATE TRIGGER replay_context_fragments_immutable_update
BEFORE UPDATE ON replay_context_fragments BEGIN SELECT RAISE(ABORT, 'replay context fragments are immutable'); END;
CREATE TRIGGER replay_context_fragments_immutable_delete
BEFORE DELETE ON replay_context_fragments BEGIN SELECT RAISE(ABORT, 'replay context fragments are immutable'); END;
CREATE TRIGGER invocation_telemetry_immutable_update
BEFORE UPDATE ON invocation_telemetry BEGIN SELECT RAISE(ABORT, 'invocation_telemetry is immutable'); END;
CREATE TRIGGER invocation_telemetry_immutable_delete
BEFORE DELETE ON invocation_telemetry BEGIN SELECT RAISE(ABORT, 'invocation_telemetry is immutable'); END;
CREATE TRIGGER route_proposals_immutable_update
BEFORE UPDATE ON route_proposals BEGIN SELECT RAISE(ABORT, 'route_proposals are immutable'); END;
CREATE TRIGGER route_proposals_immutable_delete
BEFORE DELETE ON route_proposals BEGIN SELECT RAISE(ABORT, 'route_proposals are immutable'); END;
CREATE TRIGGER route_consumption_requires_validated_route
BEFORE INSERT ON route_proposal_consumptions
WHEN NOT EXISTS (
    SELECT 1
    FROM route_proposals AS proposal
    JOIN deliveries AS source_delivery ON source_delivery.delivery_id = proposal.delivery_id
    JOIN physical_invocations AS downstream ON downstream.invocation_id = NEW.downstream_invocation_id
    JOIN deliveries AS downstream_delivery ON downstream_delivery.delivery_id = downstream.delivery_id
    WHERE proposal.proposal_id = NEW.proposal_id
      AND proposal.validation_disposition = 'accepted'
      AND proposal.persisted_output_type = 'validated_route_proposal'
      AND source_delivery.role = 'S0'
      AND downstream_delivery.role = 'synthetic_Layer0'
      AND source_delivery.run_id = downstream_delivery.run_id
)
BEGIN SELECT RAISE(ABORT, 'only validated_route_proposal may schedule synthetic Layer0'); END;
CREATE TRIGGER route_proposal_consumptions_immutable_update
BEFORE UPDATE ON route_proposal_consumptions BEGIN SELECT RAISE(ABORT, 'route proposal consumptions are immutable'); END;
CREATE TRIGGER route_proposal_consumptions_immutable_delete
BEFORE DELETE ON route_proposal_consumptions BEGIN SELECT RAISE(ABORT, 'route proposal consumptions are immutable'); END;
CREATE TRIGGER artifacts_immutable_update
BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
CREATE TRIGGER artifacts_immutable_delete
BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
CREATE TRIGGER artifact_versions_immutable_update
BEFORE UPDATE ON artifact_versions BEGIN SELECT RAISE(ABORT, 'artifact_versions are immutable'); END;
CREATE TRIGGER artifact_versions_immutable_delete
BEFORE DELETE ON artifact_versions BEGIN SELECT RAISE(ABORT, 'artifact_versions are immutable'); END;
CREATE TRIGGER artifact_lineage_immutable_update
BEFORE UPDATE ON artifact_version_lineage BEGIN SELECT RAISE(ABORT, 'artifact lineage is immutable'); END;
CREATE TRIGGER artifact_lineage_immutable_delete
BEFORE DELETE ON artifact_version_lineage BEGIN SELECT RAISE(ABORT, 'artifact lineage is immutable'); END;
CREATE TRIGGER events_immutable_update
BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
CREATE TRIGGER events_immutable_delete
BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
CREATE TRIGGER publication_transactions_immutable_update
BEFORE UPDATE ON publication_transactions BEGIN SELECT RAISE(ABORT, 'publication_transactions are immutable'); END;
CREATE TRIGGER publication_transactions_immutable_delete
BEFORE DELETE ON publication_transactions BEGIN SELECT RAISE(ABORT, 'publication_transactions are immutable'); END;
CREATE TRIGGER schema_migrations_immutable_update
BEFORE UPDATE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'schema migrations are immutable'); END;
CREATE TRIGGER schema_migrations_immutable_delete
BEFORE DELETE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'schema migrations are immutable'); END;
CREATE TRIGGER run_identity_immutable
BEFORE UPDATE OF run_id, profile, pipeline_commit, fixture_commit, fixture_tree, created_at ON runs
BEGIN SELECT RAISE(ABORT, 'run identity and pins are immutable'); END;
CREATE TRIGGER run_state_transitions_immutable_update
BEFORE UPDATE ON run_state_transitions BEGIN SELECT RAISE(ABORT, 'run state transitions are immutable'); END;
CREATE TRIGGER run_state_transitions_immutable_delete
BEFORE DELETE ON run_state_transitions BEGIN SELECT RAISE(ABORT, 'run state transitions are immutable'); END;
CREATE TRIGGER delivery_identity_immutable
BEFORE UPDATE OF delivery_id, run_id, delivery_key, role, triggering_event_id, created_at ON deliveries
BEGIN SELECT RAISE(ABORT, 'delivery identity is immutable'); END;
CREATE TRIGGER invocation_identity_and_pins_immutable
BEFORE UPDATE OF invocation_id, delivery_id, run_id, attempt_number, prompt_id, prompt_version, prompt_sha256,
    contract_id, contract_version, contract_sha256, result_schema_id, result_schema_version,
    result_schema_sha256, registry_sha256, provider, model_profile, model_identifier,
    parameters_json, context_limit_tokens, created_at ON physical_invocations
BEGIN SELECT RAISE(ABORT, 'physical invocation identity and pins are immutable'); END;
CREATE TRIGGER invocation_state_transitions_immutable_update
BEFORE UPDATE ON invocation_state_transitions BEGIN SELECT RAISE(ABORT, 'invocation state transitions are immutable'); END;
CREATE TRIGGER invocation_state_transitions_immutable_delete
BEFORE DELETE ON invocation_state_transitions BEGIN SELECT RAISE(ABORT, 'invocation state transitions are immutable'); END;
CREATE TRIGGER event_delivery_snapshot_immutable
BEFORE UPDATE OF event_delivery_id, event_id, subscriber_id, terminal_policy, fields_read_json, created_at ON event_deliveries
BEGIN SELECT RAISE(ABORT, 'event delivery subscriber snapshot is immutable'); END;
CREATE TRIGGER event_deliveries_immutable_delete
BEFORE DELETE ON event_deliveries BEGIN SELECT RAISE(ABORT, 'event deliveries are immutable'); END;
