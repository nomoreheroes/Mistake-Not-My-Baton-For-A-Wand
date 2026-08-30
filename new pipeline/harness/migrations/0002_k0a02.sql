CREATE TABLE actor_proposals (
    proposal_id TEXT PRIMARY KEY CHECK (length(proposal_id) > 0),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    delivery_id TEXT NOT NULL,
    invocation_id TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('synthetic_Layer0', 'fixture_worker')),
    raw_output_text TEXT NOT NULL CHECK (typeof(raw_output_text) = 'text'),
    raw_output_sha256 TEXT NOT NULL
        CHECK (length(raw_output_sha256) = 64 AND raw_output_sha256 = lower(raw_output_sha256) AND raw_output_sha256 NOT GLOB '*[^0-9a-f]*'),
    result_type TEXT NOT NULL CHECK (result_type IN (
        'synthetic_layer0_invocation_proposal',
        'fixture_worker_publication_proposal',
        'malformed_or_forbidden'
    )),
    validation_disposition TEXT NOT NULL CHECK (validation_disposition IN ('accepted', 'rejected')),
    terminal_state TEXT CHECK (terminal_state IS NULL OR terminal_state = 'failed_validation'),
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    FOREIGN KEY (delivery_id, run_id) REFERENCES deliveries(delivery_id, run_id),
    FOREIGN KEY (invocation_id, delivery_id, run_id)
        REFERENCES physical_invocations(invocation_id, delivery_id, run_id),
    CHECK (
        (
            validation_disposition = 'accepted'
            AND terminal_state IS NULL
            AND (
                (role = 'synthetic_Layer0' AND result_type = 'synthetic_layer0_invocation_proposal')
                OR
                (role = 'fixture_worker' AND result_type = 'fixture_worker_publication_proposal')
            )
        )
        OR
        (
            validation_disposition = 'rejected'
            AND terminal_state = 'failed_validation'
        )
    )
) STRICT;

CREATE TABLE actor_proposal_consumptions (
    consumption_id TEXT PRIMARY KEY CHECK (length(consumption_id) > 0),
    proposal_id TEXT NOT NULL UNIQUE REFERENCES actor_proposals(proposal_id),
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    downstream_invocation_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL CHECK (length(created_at) > 0),
    FOREIGN KEY (downstream_invocation_id, run_id)
        REFERENCES physical_invocations(invocation_id, run_id)
) STRICT;

CREATE TABLE sink_acceptances (
    sink_acceptance_id TEXT PRIMARY KEY CHECK (length(sink_acceptance_id) > 0),
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id),
    event_delivery_id TEXT NOT NULL UNIQUE REFERENCES event_deliveries(event_delivery_id),
    handoff_event_id TEXT NOT NULL UNIQUE,
    artifact_version_id TEXT NOT NULL UNIQUE,
    profile TEXT NOT NULL CHECK (profile = 'F00'),
    artifact_type TEXT NOT NULL CHECK (artifact_type = 'bootstrap.synthetic_result'),
    logical_owner TEXT NOT NULL CHECK (logical_owner = 'fixture.bootstrap_worker'),
    media_type TEXT NOT NULL CHECK (media_type = 'text/plain'),
    content_text TEXT NOT NULL CHECK (typeof(content_text) = 'text'),
    content_sha256 TEXT NOT NULL
        CHECK (length(content_sha256) = 64 AND content_sha256 = lower(content_sha256) AND content_sha256 NOT GLOB '*[^0-9a-f]*'),
    accepted_at TEXT NOT NULL CHECK (length(accepted_at) > 0),
    FOREIGN KEY (handoff_event_id, run_id) REFERENCES events(event_id, run_id),
    FOREIGN KEY (artifact_version_id, run_id) REFERENCES artifact_versions(artifact_version_id, run_id)
) STRICT;

CREATE TABLE readback_gates (
    readback_gate_id TEXT PRIMARY KEY CHECK (length(readback_gate_id) > 0),
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id),
    command_event_id TEXT NOT NULL,
    started_event_id TEXT NOT NULL,
    version_created_event_id TEXT NOT NULL,
    handoff_event_id TEXT NOT NULL,
    s0_invocation_id TEXT NOT NULL,
    layer0_invocation_id TEXT NOT NULL,
    worker_invocation_id TEXT NOT NULL,
    publication_transaction_id TEXT NOT NULL UNIQUE REFERENCES publication_transactions(publication_transaction_id),
    artifact_version_id TEXT NOT NULL UNIQUE,
    sink_acceptance_id TEXT NOT NULL UNIQUE REFERENCES sink_acceptances(sink_acceptance_id),
    graph_json TEXT NOT NULL CHECK (typeof(graph_json) = 'text' AND json_valid(graph_json) AND json_type(graph_json) = 'object'),
    graph_sha256 TEXT NOT NULL
        CHECK (length(graph_sha256) = 64 AND graph_sha256 = lower(graph_sha256) AND graph_sha256 NOT GLOB '*[^0-9a-f]*'),
    status TEXT NOT NULL CHECK (status = 'passed'),
    checked_at TEXT NOT NULL CHECK (length(checked_at) > 0),
    FOREIGN KEY (command_event_id, run_id) REFERENCES events(event_id, run_id),
    FOREIGN KEY (started_event_id, run_id) REFERENCES events(event_id, run_id),
    FOREIGN KEY (version_created_event_id, run_id) REFERENCES events(event_id, run_id),
    FOREIGN KEY (handoff_event_id, run_id) REFERENCES events(event_id, run_id),
    FOREIGN KEY (s0_invocation_id, run_id) REFERENCES physical_invocations(invocation_id, run_id),
    FOREIGN KEY (layer0_invocation_id, run_id) REFERENCES physical_invocations(invocation_id, run_id),
    FOREIGN KEY (worker_invocation_id, run_id) REFERENCES physical_invocations(invocation_id, run_id),
    FOREIGN KEY (artifact_version_id, run_id) REFERENCES artifact_versions(artifact_version_id, run_id)
) STRICT;

CREATE TRIGGER actor_proposals_require_current_after_replay
BEFORE INSERT ON actor_proposals
WHEN NOT EXISTS (
    SELECT 1
    FROM physical_invocations AS invocation
    JOIN deliveries AS delivery ON delivery.delivery_id = invocation.delivery_id
    JOIN invocation_telemetry AS telemetry ON telemetry.invocation_id = invocation.invocation_id
    JOIN replay_points AS replay
      ON replay.invocation_id = invocation.invocation_id AND replay.position = 'after'
    WHERE invocation.invocation_id = NEW.invocation_id
      AND invocation.run_id = NEW.run_id
      AND invocation.delivery_id = NEW.delivery_id
      AND invocation.state = 'replay_after_committed'
      AND invocation.fenced = 0
      AND invocation.response_accepted = 1
      AND delivery.current_physical_invocation_id = invocation.invocation_id
      AND delivery.role = NEW.role
      AND telemetry.response_text = NEW.raw_output_text
      AND telemetry.response_sha256 = NEW.raw_output_sha256
)
BEGIN SELECT RAISE(ABORT, 'actor proposal requires exact current after-replay response'); END;

CREATE TRIGGER actor_proposal_consumption_requires_validated_layer0
BEFORE INSERT ON actor_proposal_consumptions
WHEN NOT EXISTS (
    SELECT 1
    FROM actor_proposals AS proposal
    JOIN physical_invocations AS downstream
      ON downstream.invocation_id = NEW.downstream_invocation_id
    JOIN deliveries AS downstream_delivery
      ON downstream_delivery.delivery_id = downstream.delivery_id
    WHERE proposal.proposal_id = NEW.proposal_id
      AND proposal.run_id = NEW.run_id
      AND proposal.role = 'synthetic_Layer0'
      AND proposal.result_type = 'synthetic_layer0_invocation_proposal'
      AND proposal.validation_disposition = 'accepted'
      AND downstream.run_id = NEW.run_id
      AND downstream_delivery.role = 'fixture_worker'
)
BEGIN SELECT RAISE(ABORT, 'only a validated Layer0 proposal may schedule fixture_worker'); END;

CREATE TRIGGER publication_requires_validated_worker_proposal
BEFORE INSERT ON publication_transactions
WHEN NOT EXISTS (
    SELECT 1
    FROM actor_proposals AS proposal
    JOIN physical_invocations AS invocation ON invocation.invocation_id = proposal.invocation_id
    JOIN deliveries AS delivery ON delivery.delivery_id = invocation.delivery_id
    WHERE proposal.invocation_id = NEW.invocation_id
      AND proposal.run_id = NEW.run_id
      AND proposal.delivery_id = invocation.delivery_id
      AND proposal.role = 'fixture_worker'
      AND proposal.result_type = 'fixture_worker_publication_proposal'
      AND proposal.validation_disposition = 'accepted'
      AND proposal.terminal_state IS NULL
      AND invocation.state = 'replay_after_committed'
      AND invocation.fenced = 0
      AND invocation.response_accepted = 1
      AND delivery.current_physical_invocation_id = invocation.invocation_id
      AND delivery.role = 'fixture_worker'
      AND delivery.state = 'result_validated'
)
BEGIN SELECT RAISE(ABORT, 'publication requires the accepted fixture-worker proposal'); END;

CREATE TRIGGER sink_acceptance_requires_exact_handoff
BEFORE INSERT ON sink_acceptances
WHEN NOT EXISTS (
    SELECT 1
    FROM events AS event
    JOIN event_deliveries AS delivery ON delivery.event_id = event.event_id
    JOIN artifact_versions AS version
      ON version.artifact_version_id = event.artifact_version_id AND version.run_id = event.run_id
    JOIN artifacts AS artifact
      ON artifact.artifact_id = version.artifact_id AND artifact.run_id = version.run_id
    WHERE event.event_id = NEW.handoff_event_id
      AND event.run_id = NEW.run_id
      AND event.event_type = 'handoff.ready'
      AND event.artifact_version_id = NEW.artifact_version_id
      AND json_extract(event.payload_json, '$.profile') = NEW.profile
      AND json_extract(event.payload_json, '$.artifact_version_id') = NEW.artifact_version_id
      AND delivery.event_delivery_id = NEW.event_delivery_id
      AND delivery.subscriber_id = 'bootstrap_sink'
      AND delivery.terminal_policy = 'fixture_terminal'
      AND delivery.state = 'pending'
      AND artifact.artifact_type = NEW.artifact_type
      AND artifact.logical_owner = NEW.logical_owner
      AND version.media_type = NEW.media_type
      AND version.encoding = 'utf-8'
      AND version.content_text = NEW.content_text
      AND version.content_sha256 = NEW.content_sha256
)
BEGIN SELECT RAISE(ABORT, 'sink acceptance does not match exact handoff artifact/content/profile'); END;

CREATE TRIGGER event_delivery_state_transition_is_exact
BEFORE UPDATE OF state ON event_deliveries
WHEN NOT (
    OLD.subscriber_id = 'bootstrap_sink'
    AND OLD.terminal_policy = 'fixture_terminal'
    AND OLD.state = 'pending'
    AND NEW.state = 'accepted_terminal'
)
BEGIN SELECT RAISE(ABORT, 'event delivery state transition is forbidden or terminal'); END;

CREATE TRIGGER readback_gate_requires_connected_graph
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
          WHERE route.invocation_id = s0.invocation_id
            AND route.validation_disposition = 'accepted'
            AND route.persisted_output_type = 'validated_route_proposal'
            AND consumption.downstream_invocation_id = layer0.invocation_id
      )
      AND EXISTS (
          SELECT 1
          FROM actor_proposals AS proposal
          JOIN actor_proposal_consumptions AS consumption ON consumption.proposal_id = proposal.proposal_id
          WHERE proposal.invocation_id = layer0.invocation_id
            AND proposal.validation_disposition = 'accepted'
            AND proposal.result_type = 'synthetic_layer0_invocation_proposal'
            AND consumption.downstream_invocation_id = worker.invocation_id
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
BEGIN SELECT RAISE(ABORT, 'pre-completion readback graph is incomplete or disconnected'); END;

DROP TRIGGER runs_k0a01_blocks_completion;
DROP TRIGGER runs_k0a01_blocks_completed_insert;

CREATE TRIGGER runs_k0a02_requires_completion_gate
BEFORE UPDATE OF state ON runs
WHEN NEW.state = 'completed' AND NOT EXISTS (
    SELECT 1 FROM readback_gates AS gate
    WHERE gate.run_id = NEW.run_id AND gate.status = 'passed'
)
BEGIN SELECT RAISE(ABORT, 'K0a-02 completion requires accepted sink and gate-bearing readback'); END;

CREATE TRIGGER runs_k0a02_blocks_completed_insert
BEFORE INSERT ON runs
WHEN NEW.state = 'completed'
BEGIN SELECT RAISE(ABORT, 'K0a-02 completed run cannot be inserted directly'); END;

CREATE TRIGGER run_completed_event_requires_gate
BEFORE INSERT ON events
WHEN NEW.event_type = 'run.completed' AND NOT EXISTS (
    SELECT 1 FROM runs AS run
    JOIN readback_gates AS gate ON gate.run_id = run.run_id AND gate.status = 'passed'
    WHERE run.run_id = NEW.run_id AND run.state = 'completed'
)
BEGIN SELECT RAISE(ABORT, 'run.completed requires completed gated run'); END;

CREATE TRIGGER actor_proposals_immutable_update
BEFORE UPDATE ON actor_proposals BEGIN SELECT RAISE(ABORT, 'actor proposals are immutable'); END;
CREATE TRIGGER actor_proposals_immutable_delete
BEFORE DELETE ON actor_proposals BEGIN SELECT RAISE(ABORT, 'actor proposals are immutable'); END;
CREATE TRIGGER actor_proposal_consumptions_immutable_update
BEFORE UPDATE ON actor_proposal_consumptions BEGIN SELECT RAISE(ABORT, 'actor proposal consumptions are immutable'); END;
CREATE TRIGGER actor_proposal_consumptions_immutable_delete
BEFORE DELETE ON actor_proposal_consumptions BEGIN SELECT RAISE(ABORT, 'actor proposal consumptions are immutable'); END;
CREATE TRIGGER sink_acceptances_immutable_update
BEFORE UPDATE ON sink_acceptances BEGIN SELECT RAISE(ABORT, 'sink acceptances are immutable'); END;
CREATE TRIGGER sink_acceptances_immutable_delete
BEFORE DELETE ON sink_acceptances BEGIN SELECT RAISE(ABORT, 'sink acceptances are immutable'); END;
CREATE TRIGGER readback_gates_immutable_update
BEFORE UPDATE ON readback_gates BEGIN SELECT RAISE(ABORT, 'readback gates are immutable'); END;
CREATE TRIGGER readback_gates_immutable_delete
BEFORE DELETE ON readback_gates BEGIN SELECT RAISE(ABORT, 'readback gates are immutable'); END;
