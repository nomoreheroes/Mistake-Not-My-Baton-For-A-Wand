CREATE TABLE manual_dispatches (
    dispatch_id TEXT PRIMARY KEY CHECK (length(dispatch_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    invocation_id TEXT NOT NULL UNIQUE,
    delivery_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('S0', 'synthetic_Layer0', 'fixture_worker')),
    executor_key TEXT NOT NULL CHECK (executor_key IN ('chatgpt_gpt_5_6_sol', 'claude_opus_4_6')),
    execution_mode TEXT NOT NULL CHECK (execution_mode = 'manual_extension_handoff_v1'),
    extension_id TEXT NOT NULL CHECK (extension_id IN ('openai.chatgpt', 'anthropic.claude-code')),
    extension_version TEXT NOT NULL CHECK (length(extension_version) > 0),
    provider TEXT NOT NULL CHECK (length(provider) > 0),
    model_profile TEXT NOT NULL CHECK (length(model_profile) > 0),
    model_identifier TEXT NOT NULL CHECK (length(model_identifier) > 0),
    tool_enforcement TEXT NOT NULL CHECK (tool_enforcement IN (
        'contract_forbidden_audited_zero_calls', 'process_flag_disable_all'
    )),
    context_text TEXT NOT NULL CHECK (typeof(context_text) = 'text'),
    context_sha256 TEXT NOT NULL
        CHECK (length(context_sha256) = 64 AND context_sha256 = lower(context_sha256) AND context_sha256 NOT GLOB '*[^0-9a-f]*'),
    before_replay_point_id TEXT NOT NULL UNIQUE REFERENCES replay_points(replay_point_id),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    FOREIGN KEY (invocation_id, delivery_id, run_id)
        REFERENCES physical_invocations(invocation_id, delivery_id, run_id),
    CHECK (
        (executor_key = 'chatgpt_gpt_5_6_sol'
         AND extension_id = 'openai.chatgpt'
         AND provider = 'openai.chatgpt-vscode-extension'
         AND model_identifier = 'gpt-5.6-sol'
         AND tool_enforcement = 'contract_forbidden_audited_zero_calls')
        OR
        (executor_key = 'claude_opus_4_6'
         AND extension_id = 'anthropic.claude-code'
         AND provider = 'anthropic.claude-code-vscode-extension'
         AND model_identifier = 'claude-opus-4-6'
         AND tool_enforcement = 'process_flag_disable_all')
    )
) STRICT;

CREATE TABLE manual_receipts (
    receipt_id TEXT PRIMARY KEY CHECK (length(receipt_id) > 0),
    dispatch_id TEXT NOT NULL UNIQUE REFERENCES manual_dispatches(dispatch_id),
    invocation_id TEXT NOT NULL UNIQUE REFERENCES physical_invocations(invocation_id),
    response_text TEXT NOT NULL CHECK (typeof(response_text) = 'text'),
    response_sha256 TEXT NOT NULL
        CHECK (length(response_sha256) = 64 AND response_sha256 = lower(response_sha256) AND response_sha256 NOT GLOB '*[^0-9a-f]*'),
    transcript_text TEXT NOT NULL CHECK (typeof(transcript_text) = 'text' AND length(transcript_text) > 0),
    transcript_sha256 TEXT NOT NULL
        CHECK (length(transcript_sha256) = 64 AND transcript_sha256 = lower(transcript_sha256) AND transcript_sha256 NOT GLOB '*[^0-9a-f]*'),
    transcript_event_count INTEGER NOT NULL CHECK (transcript_event_count >= 4),
    receipt_source TEXT NOT NULL CHECK (receipt_source = 'extension_jsonl_or_ui_receipt'),
    tool_calls_observed INTEGER NOT NULL CHECK (tool_calls_observed = 0),
    transcript_complete INTEGER NOT NULL CHECK (transcript_complete = 1),
    validation_disposition TEXT NOT NULL CHECK (validation_disposition IN ('accepted', 'rejected')),
    accepted_at TEXT NOT NULL CHECK (length(accepted_at) > 0)
) STRICT;

CREATE TABLE manual_failures (
    failure_receipt_id TEXT PRIMARY KEY CHECK (length(failure_receipt_id) > 0),
    dispatch_id TEXT NOT NULL UNIQUE REFERENCES manual_dispatches(dispatch_id),
    invocation_id TEXT NOT NULL UNIQUE REFERENCES physical_invocations(invocation_id),
    failure_code TEXT NOT NULL CHECK (failure_code IN (
        'transient_unavailable_before_dispatch_ack',
        'timeout_before_accepted_response',
        'non_retriable_provider_failure'
    )),
    receipt_source TEXT NOT NULL CHECK (receipt_source = 'extension_jsonl_or_ui_receipt'),
    tool_calls_observed INTEGER NOT NULL CHECK (tool_calls_observed = 0),
    transcript_complete INTEGER NOT NULL CHECK (transcript_complete = 1),
    recorded_at TEXT NOT NULL CHECK (length(recorded_at) > 0)
) STRICT;

CREATE TRIGGER manual_dispatch_requires_committed_before_replay
BEFORE INSERT ON manual_dispatches
WHEN NOT EXISTS (
    SELECT 1
    FROM physical_invocations AS invocation
    JOIN deliveries AS delivery ON delivery.delivery_id = invocation.delivery_id
    JOIN replay_points AS replay
      ON replay.invocation_id = invocation.invocation_id AND replay.position = 'before'
    WHERE invocation.invocation_id = NEW.invocation_id
      AND invocation.delivery_id = NEW.delivery_id
      AND invocation.run_id = NEW.run_id
      AND invocation.state = 'dispatched'
      AND invocation.fenced = 0
      AND invocation.provider = NEW.provider
      AND invocation.model_profile = NEW.model_profile
      AND invocation.model_identifier = NEW.model_identifier
      AND delivery.role = NEW.role
      AND replay.replay_point_id = NEW.before_replay_point_id
      AND replay.context_text = NEW.context_text
      AND replay.context_sha256 = NEW.context_sha256
)
BEGIN SELECT RAISE(ABORT, 'manual dispatch requires exact committed before-replay and model pins'); END;

CREATE TRIGGER manual_receipt_requires_exact_dispatch_response
BEFORE INSERT ON manual_receipts
WHEN NOT EXISTS (
    SELECT 1
    FROM manual_dispatches AS dispatch
    JOIN physical_invocations AS invocation ON invocation.invocation_id = dispatch.invocation_id
    JOIN invocation_telemetry AS telemetry ON telemetry.invocation_id = invocation.invocation_id
    WHERE dispatch.dispatch_id = NEW.dispatch_id
      AND dispatch.invocation_id = NEW.invocation_id
      AND invocation.state IN ('response_captured', 'validated', 'replay_after_committed')
      AND invocation.response_accepted = 1
      AND telemetry.response_text = NEW.response_text
      AND telemetry.response_sha256 = NEW.response_sha256
)
BEGIN SELECT RAISE(ABORT, 'manual receipt requires exact persisted response telemetry'); END;

CREATE TRIGGER manual_failure_requires_failed_invocation
BEFORE INSERT ON manual_failures
WHEN NOT EXISTS (
    SELECT 1
    FROM manual_dispatches AS dispatch
    JOIN physical_invocations AS invocation ON invocation.invocation_id = dispatch.invocation_id
    WHERE dispatch.dispatch_id = NEW.dispatch_id
      AND dispatch.invocation_id = NEW.invocation_id
      AND invocation.state = 'failed_invocation'
      AND invocation.response_accepted = 0
      AND invocation.failure_code = NEW.failure_code
)
BEGIN SELECT RAISE(ABORT, 'manual failure receipt requires matching failed invocation'); END;

CREATE TRIGGER artifact_publication_requires_manual_receipt_evidence
BEFORE INSERT ON artifacts
WHEN (
    SELECT count(*)
    FROM manual_receipts AS receipt
    JOIN manual_dispatches AS dispatch ON dispatch.dispatch_id = receipt.dispatch_id
    JOIN physical_invocations AS invocation ON invocation.invocation_id = receipt.invocation_id
    JOIN deliveries AS delivery ON delivery.delivery_id = invocation.delivery_id
    JOIN invocation_telemetry AS telemetry ON telemetry.invocation_id = invocation.invocation_id
    WHERE dispatch.run_id = NEW.run_id
      AND dispatch.invocation_id = invocation.invocation_id
      AND delivery.run_id = NEW.run_id
      AND delivery.role IN ('S0', 'synthetic_Layer0', 'fixture_worker')
      AND invocation.state IN ('replay_after_committed', 'published')
      AND invocation.response_accepted = 1
      AND receipt.validation_disposition = 'accepted'
      AND receipt.tool_calls_observed = 0
      AND receipt.transcript_complete = 1
      AND receipt.response_text = telemetry.response_text
      AND receipt.response_sha256 = telemetry.response_sha256
) != 3
OR (
    SELECT count(DISTINCT delivery.role)
    FROM manual_receipts AS receipt
    JOIN manual_dispatches AS dispatch ON dispatch.dispatch_id = receipt.dispatch_id
    JOIN physical_invocations AS invocation ON invocation.invocation_id = receipt.invocation_id
    JOIN deliveries AS delivery ON delivery.delivery_id = invocation.delivery_id
    WHERE dispatch.run_id = NEW.run_id
      AND receipt.validation_disposition = 'accepted'
) != 3
BEGIN SELECT RAISE(ABORT, 'artifact publication requires three accepted manual transcript receipts'); END;

DROP TRIGGER readback_gate_requires_connected_graph;

CREATE TRIGGER readback_gate_requires_connected_retry_graph
BEFORE INSERT ON readback_gates
WHEN NOT EXISTS (
    SELECT 1
    FROM runs AS run
    JOIN events AS command
      ON command.event_id = NEW.command_event_id AND command.run_id = run.run_id
    JOIN events AS started
      ON started.event_id = NEW.started_event_id AND started.run_id = run.run_id
    JOIN events AS version_created
      ON version_created.event_id = NEW.version_created_event_id AND version_created.run_id = run.run_id
    JOIN events AS handoff
      ON handoff.event_id = NEW.handoff_event_id AND handoff.run_id = run.run_id
    JOIN physical_invocations AS s0
      ON s0.invocation_id = NEW.s0_invocation_id AND s0.run_id = run.run_id
    JOIN deliveries AS s0_delivery ON s0_delivery.delivery_id = s0.delivery_id
    JOIN physical_invocations AS layer0
      ON layer0.invocation_id = NEW.layer0_invocation_id AND layer0.run_id = run.run_id
    JOIN deliveries AS layer0_delivery ON layer0_delivery.delivery_id = layer0.delivery_id
    JOIN physical_invocations AS worker
      ON worker.invocation_id = NEW.worker_invocation_id AND worker.run_id = run.run_id
    JOIN deliveries AS worker_delivery ON worker_delivery.delivery_id = worker.delivery_id
    JOIN publication_transactions AS publication
      ON publication.publication_transaction_id = NEW.publication_transaction_id
     AND publication.run_id = run.run_id
    JOIN artifact_versions AS version
      ON version.artifact_version_id = NEW.artifact_version_id AND version.run_id = run.run_id
    JOIN sink_acceptances AS sink
       ON sink.sink_acceptance_id = NEW.sink_acceptance_id AND sink.run_id = run.run_id
    JOIN manual_dispatches AS s0_dispatch ON s0_dispatch.invocation_id = s0.invocation_id
    JOIN manual_receipts AS s0_receipt ON s0_receipt.invocation_id = s0.invocation_id
    JOIN manual_dispatches AS layer0_dispatch ON layer0_dispatch.invocation_id = layer0.invocation_id
    JOIN manual_receipts AS layer0_receipt ON layer0_receipt.invocation_id = layer0.invocation_id
    JOIN manual_dispatches AS worker_dispatch ON worker_dispatch.invocation_id = worker.invocation_id
    JOIN manual_receipts AS worker_receipt ON worker_receipt.invocation_id = worker.invocation_id
    JOIN event_deliveries AS sink_delivery
      ON sink_delivery.event_delivery_id = sink.event_delivery_id
     AND sink_delivery.event_id = handoff.event_id
    WHERE run.run_id = NEW.run_id
      AND run.state = 'running'
      AND command.event_type = 'command.received'
      AND command.caused_by_event_id IS NULL
      AND started.event_type = 'run.started'
      AND started.caused_by_event_id = command.event_id
      AND version_created.event_type = 'artifact.version_created'
      AND version_created.caused_by_event_id = started.event_id
      AND version_created.artifact_version_id = version.artifact_version_id
      AND handoff.event_type = 'handoff.ready'
      AND handoff.caused_by_event_id = version_created.event_id
      AND handoff.artifact_version_id = version.artifact_version_id
      AND s0_delivery.role = 'S0'
      AND layer0_delivery.role = 'synthetic_Layer0'
      AND worker_delivery.role = 'fixture_worker'
      AND s0_dispatch.run_id = run.run_id
      AND layer0_dispatch.run_id = run.run_id
      AND worker_dispatch.run_id = run.run_id
      AND s0_receipt.validation_disposition = 'accepted'
      AND layer0_receipt.validation_disposition = 'accepted'
      AND worker_receipt.validation_disposition = 'accepted'
      AND s0_receipt.tool_calls_observed = 0
      AND layer0_receipt.tool_calls_observed = 0
      AND worker_receipt.tool_calls_observed = 0
      AND s0_receipt.transcript_complete = 1
      AND layer0_receipt.transcript_complete = 1
      AND worker_receipt.transcript_complete = 1
      AND s0_receipt.response_text = (SELECT response_text FROM invocation_telemetry WHERE invocation_id = s0.invocation_id)
      AND layer0_receipt.response_text = (SELECT response_text FROM invocation_telemetry WHERE invocation_id = layer0.invocation_id)
      AND worker_receipt.response_text = (SELECT response_text FROM invocation_telemetry WHERE invocation_id = worker.invocation_id)
      AND s0.state = 'published'
      AND layer0.state = 'published'
      AND worker.state = 'published'
      AND publication.invocation_id = worker.invocation_id
      AND publication.artifact_version_id = version.artifact_version_id
      AND publication.version_created_event_id = version_created.event_id
      AND publication.handoff_event_id = handoff.event_id
      AND sink.handoff_event_id = handoff.event_id
      AND sink.artifact_version_id = version.artifact_version_id
      AND sink_delivery.subscriber_id = 'bootstrap_sink'
      AND sink_delivery.terminal_policy = 'fixture_terminal'
      AND sink_delivery.state = 'accepted_terminal'
      AND (SELECT count(*) FROM replay_points WHERE invocation_id = s0.invocation_id) = 2
      AND (SELECT count(*) FROM replay_points WHERE invocation_id = layer0.invocation_id) = 2
      AND (SELECT count(*) FROM replay_points WHERE invocation_id = worker.invocation_id) = 2
      AND EXISTS (
          SELECT 1
          FROM route_proposals AS route
          JOIN route_proposal_consumptions AS consumption ON consumption.proposal_id = route.proposal_id
          JOIN physical_invocations AS consumed
            ON consumed.invocation_id = consumption.downstream_invocation_id
          WHERE route.invocation_id = s0.invocation_id
            AND route.validation_disposition = 'accepted'
            AND route.persisted_output_type = 'validated_route_proposal'
            AND consumed.delivery_id = layer0.delivery_id
      )
      AND EXISTS (
          SELECT 1
          FROM actor_proposals AS proposal
          JOIN actor_proposal_consumptions AS consumption ON consumption.proposal_id = proposal.proposal_id
          JOIN physical_invocations AS consumed
            ON consumed.invocation_id = consumption.downstream_invocation_id
          WHERE proposal.invocation_id = layer0.invocation_id
            AND proposal.validation_disposition = 'accepted'
            AND proposal.result_type = 'synthetic_layer0_invocation_proposal'
            AND consumed.delivery_id = worker.delivery_id
      )
      AND EXISTS (
          SELECT 1
          FROM actor_proposals AS proposal
          WHERE proposal.invocation_id = worker.invocation_id
            AND proposal.delivery_id = worker.delivery_id
            AND proposal.run_id = run.run_id
            AND proposal.role = 'fixture_worker'
            AND proposal.result_type = 'fixture_worker_publication_proposal'
            AND proposal.validation_disposition = 'accepted'
            AND proposal.terminal_state IS NULL
      )
)
BEGIN SELECT RAISE(ABORT, 'pre-completion retry graph is incomplete or disconnected'); END;

CREATE TRIGGER manual_dispatches_immutable_update
BEFORE UPDATE ON manual_dispatches BEGIN SELECT RAISE(ABORT, 'manual dispatches are immutable'); END;
CREATE TRIGGER manual_dispatches_immutable_delete
BEFORE DELETE ON manual_dispatches BEGIN SELECT RAISE(ABORT, 'manual dispatches are immutable'); END;
CREATE TRIGGER manual_receipts_immutable_update
BEFORE UPDATE ON manual_receipts BEGIN SELECT RAISE(ABORT, 'manual receipts are immutable'); END;
CREATE TRIGGER manual_receipts_immutable_delete
BEFORE DELETE ON manual_receipts BEGIN SELECT RAISE(ABORT, 'manual receipts are immutable'); END;
CREATE TRIGGER manual_failures_immutable_update
BEFORE UPDATE ON manual_failures BEGIN SELECT RAISE(ABORT, 'manual failures are immutable'); END;
CREATE TRIGGER manual_failures_immutable_delete
BEFORE DELETE ON manual_failures BEGIN SELECT RAISE(ABORT, 'manual failures are immutable'); END;
