CREATE TABLE k0b_contract_profile_bindings (
    binding_id TEXT PRIMARY KEY CHECK (length(binding_id) > 0),
    profile TEXT NOT NULL CHECK (profile = 'Alpha0'),
    package_id TEXT NOT NULL CHECK (package_id = 'pipeline-v2.k0b01.alpha0-kernel-contract-package'),
    package_version TEXT NOT NULL CHECK (package_version = '1.0.0'),
    package_sha256 TEXT NOT NULL CHECK (length(package_sha256) = 64 AND package_sha256 = lower(package_sha256) AND package_sha256 NOT GLOB '*[^0-9a-f]*'),
    event_profile_sha256 TEXT NOT NULL CHECK (length(event_profile_sha256) = 64 AND event_profile_sha256 = lower(event_profile_sha256) AND event_profile_sha256 NOT GLOB '*[^0-9a-f]*'),
    subscription_profile_sha256 TEXT NOT NULL CHECK (length(subscription_profile_sha256) = 64 AND subscription_profile_sha256 = lower(subscription_profile_sha256) AND subscription_profile_sha256 NOT GLOB '*[^0-9a-f]*'),
    routing_profile_sha256 TEXT NOT NULL CHECK (length(routing_profile_sha256) = 64 AND routing_profile_sha256 = lower(routing_profile_sha256) AND routing_profile_sha256 NOT GLOB '*[^0-9a-f]*'),
    resource_policy_sha256 TEXT NOT NULL CHECK (length(resource_policy_sha256) = 64 AND resource_policy_sha256 = lower(resource_policy_sha256) AND resource_policy_sha256 NOT GLOB '*[^0-9a-f]*'),
    reference_cases_sha256 TEXT NOT NULL CHECK (length(reference_cases_sha256) = 64 AND reference_cases_sha256 = lower(reference_cases_sha256) AND reference_cases_sha256 NOT GLOB '*[^0-9a-f]*'),
    implementation_authority_sha256 TEXT NOT NULL CHECK (length(implementation_authority_sha256) = 64 AND implementation_authority_sha256 = lower(implementation_authority_sha256) AND implementation_authority_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (package_id, package_version, package_sha256, event_profile_sha256, subscription_profile_sha256, routing_profile_sha256, resource_policy_sha256, reference_cases_sha256)
) STRICT;

CREATE TABLE k0b_compiled_profile_records (
    compiled_profile_record_id TEXT PRIMARY KEY CHECK (length(compiled_profile_record_id) > 0),
    binding_id TEXT NOT NULL REFERENCES k0b_contract_profile_bindings(binding_id),
    output_family TEXT NOT NULL CHECK (output_family IN (
        'compiled_artifact_event_profile',
        'compiled_event_reachability_graph',
        'compiled_subscription_terminal_snapshot',
        'compiled_s_route_table_v2',
        'compiled_fanout_barrier_profile',
        'compiled_resource_forecast',
        'compiled_checkpoint_phase_partition_v1',
        'compiled_checkpoint_publication_budget_v2'
    )),
    compiler_id TEXT NOT NULL CHECK (compiler_id = 'pipeline-v2.k0b01.registry-routing-compiler'),
    compiler_version TEXT NOT NULL CHECK (compiler_version = '1.0.0'),
    compiler_sha256 TEXT NOT NULL CHECK (length(compiler_sha256) = 64 AND compiler_sha256 = lower(compiler_sha256) AND compiler_sha256 NOT GLOB '*[^0-9a-f]*'),
    compiler_hashes_json TEXT NOT NULL CHECK (typeof(compiler_hashes_json) = 'text' AND json_valid(compiler_hashes_json) AND json_type(compiler_hashes_json) = 'object'),
    source_hashes_json TEXT NOT NULL CHECK (typeof(source_hashes_json) = 'text' AND json_valid(source_hashes_json)),
    output_json TEXT NOT NULL CHECK (typeof(output_json) = 'text' AND json_valid(output_json)),
    output_sha256 TEXT NOT NULL CHECK (length(output_sha256) = 64 AND output_sha256 = lower(output_sha256) AND output_sha256 NOT GLOB '*[^0-9a-f]*'),
    aggregate_digest TEXT NOT NULL CHECK (length(aggregate_digest) = 64 AND aggregate_digest = lower(aggregate_digest) AND aggregate_digest NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (binding_id, output_family),
    UNIQUE (compiled_profile_record_id, binding_id)
) STRICT;

CREATE TABLE k0b_event_type_definitions (
    binding_id TEXT NOT NULL REFERENCES k0b_contract_profile_bindings(binding_id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'command.received', 'run.started', 'artifact.version_created', 'handoff.ready', 'run.completed',
        'run.blocked', 'run.abort_requested', 'run.aborted', 'artifact.published',
        'projection.requested', 'projection.written', 'projection.failed', 'revision.requested',
        'gate.passed', 'approval.requested', 'approval.granted', 'approval.rejected',
        'error.schema_mismatch', 'error.tool_failure', 'error.security_policy', 'meta.incident_detected'
    )),
    event_version INTEGER NOT NULL CHECK (event_version = 1),
    payload_schema_id TEXT NOT NULL CHECK (length(payload_schema_id) > 0),
    payload_schema_version INTEGER NOT NULL CHECK (payload_schema_version = 1),
    payload_schema_sha256 TEXT NOT NULL CHECK (length(payload_schema_sha256) = 64 AND payload_schema_sha256 = lower(payload_schema_sha256) AND payload_schema_sha256 NOT GLOB '*[^0-9a-f]*'),
    producer_owner TEXT NOT NULL CHECK (producer_owner IN (
        'shared_control', 'shared_artifact_event', 'human_operator_or_shared_control',
        'registered_consumer', 'human_project_owner', 'deterministic_validator',
        'security_guard', 'shared_control_or_security_guard'
    )),
    route_ref TEXT NOT NULL CHECK (route_ref IN (
        'alpha0.control.command', 'alpha0.control.run_lifecycle',
        'alpha0.control.artifact_lifecycle', 'alpha0.control.handoff',
        'alpha0.terminal.run_completed', 'alpha0.terminal.blocked_human',
        'alpha0.control.abort', 'alpha0.terminal.run_aborted',
        'alpha0.artifact_event.projection', 'alpha0.control.projection_result',
        'alpha0.control.revision', 'alpha0.control.gate', 'alpha0.human.owner_gate',
        'alpha0.control.approval_result', 'alpha0.terminal.error_human',
        'alpha0.terminal.incident_w5'
    )),
    allowed_subscribers_json TEXT NOT NULL CHECK (typeof(allowed_subscribers_json) = 'text' AND json_valid(allowed_subscribers_json) AND json_type(allowed_subscribers_json) = 'array'),
    terminal_policy TEXT CHECK (terminal_policy IS NULL OR terminal_policy IN (
        'observational_terminal', 'block_run_and_enqueue_human',
        'aborted_terminal', 'persist_incident_and_enqueue_W5'
    )),
    fields_consumed_json TEXT NOT NULL CHECK (typeof(fields_consumed_json) = 'text' AND json_valid(fields_consumed_json) AND json_type(fields_consumed_json) = 'array' AND json_array_length(fields_consumed_json) > 0),
    activation_work_item TEXT NOT NULL CHECK (activation_work_item IN ('K0b-01', 'K0b-02', 'K0b-03')),
    replay_semantics TEXT NOT NULL CHECK (replay_semantics IN (
        'append_once', 'immutable_observation', 'immutable_lineage', 'immutable_delivery',
        'terminal_immutable', 'durable_intent', 'immutable_result',
        'append_once_new_revision', 'durable_human_request', 'immutable_owner_decision'
    )),
    idempotency_scope TEXT NOT NULL CHECK (idempotency_scope = 'run_event_type_key'),
    terminal_disposition TEXT NOT NULL CHECK (terminal_disposition IN (
        'subscriber_snapshot', 'observational_terminal', 'block_run_and_enqueue_human',
        'aborted_terminal', 'persist_incident_and_enqueue_W5'
    )),
    CHECK (
        (terminal_policy IS NULL AND json_array_length(allowed_subscribers_json) > 0 AND terminal_disposition = 'subscriber_snapshot')
        OR
        (terminal_policy IS NOT NULL AND length(terminal_policy) > 0 AND json_array_length(allowed_subscribers_json) = 0 AND terminal_disposition = terminal_policy)
    ),
    PRIMARY KEY (binding_id, event_type, event_version)
) STRICT;

CREATE TABLE k0b_subscription_terminal_definitions (
    binding_id TEXT NOT NULL REFERENCES k0b_contract_profile_bindings(binding_id),
    route_id TEXT NOT NULL CHECK (route_id IN (
        'alpha0.control.command', 'alpha0.control.run_lifecycle',
        'alpha0.control.artifact_lifecycle', 'alpha0.control.handoff',
        'alpha0.terminal.run_completed', 'alpha0.terminal.blocked_human',
        'alpha0.control.abort', 'alpha0.terminal.run_aborted',
        'alpha0.artifact_event.projection', 'alpha0.control.projection_result',
        'alpha0.control.revision', 'alpha0.control.gate', 'alpha0.human.owner_gate',
        'alpha0.control.approval_result', 'alpha0.terminal.error_human',
        'alpha0.terminal.incident_w5'
    )),
    kind TEXT NOT NULL CHECK (kind IN ('subscriber', 'terminal')),
    subscribers_json TEXT NOT NULL CHECK (typeof(subscribers_json) = 'text' AND json_valid(subscribers_json) AND json_type(subscribers_json) = 'array'),
    terminal_policy TEXT CHECK (terminal_policy IS NULL OR terminal_policy IN (
        'observational_terminal', 'block_run_and_enqueue_human',
        'aborted_terminal', 'persist_incident_and_enqueue_W5'
    )),
    fields_read_json TEXT NOT NULL CHECK (typeof(fields_read_json) = 'text' AND json_valid(fields_read_json) AND json_type(fields_read_json) = 'array'),
    activation_work_item TEXT NOT NULL CHECK (activation_work_item IN ('K0b-01', 'K0b-02', 'K0b-03')),
    PRIMARY KEY (binding_id, route_id),
    CHECK (
        (kind = 'subscriber' AND json_array_length(subscribers_json) > 0 AND terminal_policy IS NULL)
        OR
        (kind = 'terminal' AND json_array_length(subscribers_json) = 0 AND terminal_policy IS NOT NULL AND length(terminal_policy) > 0)
    )
) STRICT;

CREATE TABLE k0b_s_route_definitions (
    binding_id TEXT NOT NULL REFERENCES k0b_contract_profile_bindings(binding_id),
    route_id TEXT NOT NULL CHECK (route_id IN (
        's.alpha0.compiled_nominal.v1',
        's.alpha0.layer0_fallback.v1',
        's.alpha0.f04.parallel_review.v1',
        's.alpha0.f05.revision.v1',
        's.alpha0.blocked.v1'
    )),
    route_json TEXT NOT NULL CHECK (typeof(route_json) = 'text' AND json_valid(route_json)),
    route_sha256 TEXT NOT NULL CHECK (length(route_sha256) = 64 AND route_sha256 = lower(route_sha256) AND route_sha256 NOT GLOB '*[^0-9a-f]*'),
    PRIMARY KEY (binding_id, route_id)
) STRICT;

CREATE TABLE k0b_resource_budget_compilations (
    budget_compilation_id TEXT PRIMARY KEY CHECK (length(budget_compilation_id) > 0),
    binding_id TEXT NOT NULL REFERENCES k0b_contract_profile_bindings(binding_id),
    case_id TEXT NOT NULL CHECK (case_id IN (
        'k0a-bootstrap-reference-v1', 'k0b-approved-two-phase-reference-v1'
    )),
    policy_sha256 TEXT NOT NULL CHECK (length(policy_sha256) = 64 AND policy_sha256 = lower(policy_sha256) AND policy_sha256 NOT GLOB '*[^0-9a-f]*'),
    reference_cases_sha256 TEXT NOT NULL CHECK (length(reference_cases_sha256) = 64 AND reference_cases_sha256 = lower(reference_cases_sha256) AND reference_cases_sha256 NOT GLOB '*[^0-9a-f]*'),
    input_sha256 TEXT NOT NULL CHECK (length(input_sha256) = 64 AND input_sha256 = lower(input_sha256) AND input_sha256 NOT GLOB '*[^0-9a-f]*'),
    result_json TEXT NOT NULL CHECK (typeof(result_json) = 'text' AND json_valid(result_json)),
    result_sha256 TEXT NOT NULL CHECK (length(result_sha256) = 64 AND result_sha256 = lower(result_sha256) AND result_sha256 NOT GLOB '*[^0-9a-f]*'),
    equivalence_status TEXT NOT NULL CHECK (equivalence_status = 'exact_field_value_match'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    UNIQUE (binding_id, case_id)
) STRICT;

CREATE TABLE k0b_terminal_queue_items (
    queue_item_id TEXT PRIMARY KEY CHECK (length(queue_item_id) > 0),
    source_event_ref TEXT NOT NULL CHECK (length(source_event_ref) > 0),
    queue_owner TEXT NOT NULL CHECK (queue_owner IN ('human', 'W5')),
    terminal_policy TEXT NOT NULL CHECK (terminal_policy IN ('block_run_and_enqueue_human', 'persist_incident_and_enqueue_W5')),
    payload_refs_json TEXT NOT NULL CHECK (typeof(payload_refs_json) = 'text' AND json_valid(payload_refs_json) AND json_type(payload_refs_json) = 'object'),
    state TEXT NOT NULL CHECK (state = 'pending'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    CHECK (
        (queue_owner = 'human' AND terminal_policy = 'block_run_and_enqueue_human')
        OR
        (queue_owner = 'W5' AND terminal_policy = 'persist_incident_and_enqueue_W5')
    )
) STRICT;

CREATE INDEX k0b_compiled_profiles_binding_idx ON k0b_compiled_profile_records(binding_id, output_family);
CREATE INDEX k0b_events_route_idx ON k0b_event_type_definitions(binding_id, route_ref);
CREATE INDEX k0b_terminal_queue_owner_idx ON k0b_terminal_queue_items(queue_owner, state);

CREATE TRIGGER k0b_contract_profile_bindings_immutable_update
BEFORE UPDATE ON k0b_contract_profile_bindings BEGIN SELECT RAISE(ABORT, 'K0b contract profile bindings are immutable'); END;
CREATE TRIGGER k0b_contract_profile_bindings_immutable_delete
BEFORE DELETE ON k0b_contract_profile_bindings BEGIN SELECT RAISE(ABORT, 'K0b contract profile bindings are immutable'); END;
CREATE TRIGGER k0b_compiled_profile_records_immutable_update
BEFORE UPDATE ON k0b_compiled_profile_records BEGIN SELECT RAISE(ABORT, 'K0b compiled profile records are immutable'); END;
CREATE TRIGGER k0b_compiled_profile_records_immutable_delete
BEFORE DELETE ON k0b_compiled_profile_records BEGIN SELECT RAISE(ABORT, 'K0b compiled profile records are immutable'); END;
CREATE TRIGGER k0b_event_type_definitions_immutable_update
BEFORE UPDATE ON k0b_event_type_definitions BEGIN SELECT RAISE(ABORT, 'K0b event type definitions are immutable'); END;
CREATE TRIGGER k0b_event_type_definitions_immutable_delete
BEFORE DELETE ON k0b_event_type_definitions BEGIN SELECT RAISE(ABORT, 'K0b event type definitions are immutable'); END;
CREATE TRIGGER k0b_subscription_terminal_definitions_immutable_update
BEFORE UPDATE ON k0b_subscription_terminal_definitions BEGIN SELECT RAISE(ABORT, 'K0b subscription definitions are immutable'); END;
CREATE TRIGGER k0b_subscription_terminal_definitions_immutable_delete
BEFORE DELETE ON k0b_subscription_terminal_definitions BEGIN SELECT RAISE(ABORT, 'K0b subscription definitions are immutable'); END;
CREATE TRIGGER k0b_s_route_definitions_immutable_update
BEFORE UPDATE ON k0b_s_route_definitions BEGIN SELECT RAISE(ABORT, 'K0b S route definitions are immutable'); END;
CREATE TRIGGER k0b_s_route_definitions_immutable_delete
BEFORE DELETE ON k0b_s_route_definitions BEGIN SELECT RAISE(ABORT, 'K0b S route definitions are immutable'); END;
CREATE TRIGGER k0b_resource_budget_compilations_immutable_update
BEFORE UPDATE ON k0b_resource_budget_compilations BEGIN SELECT RAISE(ABORT, 'K0b resource budget compilations are immutable'); END;
CREATE TRIGGER k0b_resource_budget_compilations_immutable_delete
BEFORE DELETE ON k0b_resource_budget_compilations BEGIN SELECT RAISE(ABORT, 'K0b resource budget compilations are immutable'); END;
CREATE TRIGGER k0b_terminal_queue_items_immutable_update
BEFORE UPDATE ON k0b_terminal_queue_items BEGIN SELECT RAISE(ABORT, 'K0b terminal queue items are immutable'); END;
CREATE TRIGGER k0b_terminal_queue_items_immutable_delete
BEFORE DELETE ON k0b_terminal_queue_items BEGIN SELECT RAISE(ABORT, 'K0b terminal queue items are immutable'); END;
