from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a01 import (  # noqa: E402
    ArtifactPublication,
    IdempotencyConflict,
    IntegrityConflict,
    InvocationSpec,
    InvocationTelemetry,
    K0a01Store,
    LineageRef,
    MigrationError,
    ReplayPoint,
    StaleState,
    TextPolicyError,
)


H_A = "a" * 64
H_B = "b" * 64
H_C = "c" * 64
PIPELINE_COMMIT = "de8c24a5a745ca8f200071c5e8589dd0de7fcbd9"
FIXTURE_COMMIT = "192a5b1e9e312b78c310184cde0fc3377c51ab1b"
FIXTURE_TREE = "93a9b120c6284bb4b094ab1efd3784582597452d"
T0 = "2026-08-28T18:00:00Z"
T1 = "2026-08-28T18:00:01Z"
T2 = "2026-08-28T18:00:02Z"
T3 = "2026-08-28T18:00:03Z"
T4 = "2026-08-28T18:00:04Z"
RESPONSE = '{"result":"ok"}'


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


CONTEXT_FRAGMENTS = (
    {
        "ordinal": 0,
        "role": "system",
        "content_text": "fixture-only policy",
        "content_sha256": digest("fixture-only policy"),
    },
    {
        "ordinal": 1,
        "role": "user",
        "content_text": "produce the synthetic result",
        "content_sha256": digest("produce the synthetic result"),
    },
)
CONTEXT = json.dumps(
    CONTEXT_FRAGMENTS,
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
)
CAPABILITIES = {
    "policy_version": "f00-deny-all-v1",
    "model_channel": "test-provider",
    "filesystem_roots": [],
    "tools": [],
}
ENVIRONMENT = {
    "adapter_version": "test-adapter-1",
    "architecture": "x86_64",
    "clock_binding": "monotonic_ns",
    "config_sha256": H_B,
    "dependency_lock_sha256": H_C,
    "harness_version": "k0a01-test",
    "locale": "C",
    "os": "test",
    "random_seed": 0,
    "timezone": "UTC",
    "tool_registry_version": "none-v1",
}


class InjectedFailure(RuntimeError):
    pass


class K0a01StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pipeline-v2-k0a01-")
        self.db_path = Path(self.temp.name) / "pipeline.sqlite3"
        self.store = K0a01Store(self.db_path)
        self.migration_sha = self.store.initialize()
        self.store.create_run(
            run_id="run-001",
            pipeline_commit=PIPELINE_COMMIT,
            fixture_commit=FIXTURE_COMMIT,
            fixture_tree=FIXTURE_TREE,
            created_at=T0,
        )
        self.revision = self.store.transition_run(
            run_id="run-001",
            expected_state="created",
            expected_revision=0,
            new_state="running",
            transition_id="run-001:running",
            occurred_at=T1,
        )
        self.store.append_control_event(
            event_id="event-command",
            run_id="run-001",
            event_type="command.received",
            caused_by_event_id=None,
            correlation_id="correlation-001",
            schema_id="event-envelope",
            schema_version="1",
            schema_sha256=H_A,
            payload={"command": "bootstrap", "profile": "F00", "run_id": "run-001"},
            idempotency_key="event:command",
            created_at=T1,
        )
        self.store.append_control_event(
            event_id="event-started",
            run_id="run-001",
            event_type="run.started",
            caused_by_event_id="event-command",
            correlation_id="correlation-001",
            schema_id="event-envelope",
            schema_version="1",
            schema_sha256=H_A,
            payload={"run_id": "run-001", "state": "running"},
            idempotency_key="event:started",
            created_at=T1,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invocation_spec(
        self,
        invocation_id: str = "inv-worker-1",
        delivery_id: str = "delivery-worker",
        attempt_number: int = 1,
    ) -> InvocationSpec:
        return InvocationSpec(
            invocation_id=invocation_id,
            delivery_id=delivery_id,
            attempt_number=attempt_number,
            prompt_id="fixture-worker-prompt",
            prompt_version="1",
            prompt_sha256=H_A,
            contract_id="fixture-worker-contract",
            contract_version="1",
            contract_sha256=H_B,
            result_schema_id="fixture-worker-result",
            result_schema_version="1",
            result_schema_sha256=H_C,
            registry_sha256=H_A,
            provider="test-provider",
            model_profile="pinned-test-profile",
            model_identifier="test-model-immutable-1",
            parameters={"temperature": 0, "top_p": 1},
            context_limit_tokens=4096,
            created_at=T1,
        )

    def create_delivery_and_invocation(
        self,
        *,
        role: str = "fixture_worker",
        delivery_id: str = "delivery-worker",
        invocation_id: str = "inv-worker-1",
        attempt_number: int = 1,
    ) -> InvocationSpec:
        if attempt_number == 1:
            self.store.create_delivery(
                delivery_id=delivery_id,
                run_id="run-001",
                delivery_key=delivery_id,
                role=role,
                triggering_event_id="event-command" if role == "S0" else "event-started",
                created_at=T1,
            )
        spec = self.invocation_spec(invocation_id, delivery_id, attempt_number)
        if role == "S0":
            spec = replace(
                spec,
                prompt_id="s0-prompt",
                contract_id="s0-contract",
                result_schema_id="s0-result",
            )
        self.store.create_invocation(spec)
        return spec

    def record_before(self, spec: InvocationSpec, sequence: int = 0) -> None:
        self.store.record_replay_point(
            ReplayPoint(
                replay_point_id=f"{spec.invocation_id}:before",
                invocation_id=spec.invocation_id,
                position="before",
                sequence_number=sequence,
                context_text=CONTEXT,
                context_sha256=digest(CONTEXT),
                context_fragments=CONTEXT_FRAGMENTS,
                capabilities=CAPABILITIES,
                environment=ENVIRONMENT,
                capture_completeness="typed_gap",
                gap_code="provider_hidden_context_gap",
                created_at=T1,
            )
        )

    def record_success(self, spec: InvocationSpec, sequence: int = 0) -> None:
        self.record_before(spec, sequence)
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="replay_before_committed",
            new_state="dispatched",
            transition_id=f"{spec.invocation_id}:dispatched",
            occurred_at=T2,
        )
        self.store.record_telemetry(
            InvocationTelemetry(
                telemetry_id=f"{spec.invocation_id}:telemetry",
                invocation_id=spec.invocation_id,
                provider=spec.provider,
                model_profile=spec.model_profile,
                model_identifier=spec.model_identifier,
                parameters=spec.parameters,
                response_text=RESPONSE,
                response_sha256=digest(RESPONSE),
                started_at=T2,
                completed_at=T3,
                duration_ms=1000,
                monotonic_started_ns=1_000_000_000,
                monotonic_completed_ns=2_000_000_000,
                input_tokens=12,
                output_tokens=5,
                total_tokens=17,
                usage={"input_tokens": 12, "output_tokens": 5, "total_tokens": 17},
                finish_reason="stop",
            )
        )
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="response_captured",
            new_state="validated",
            transition_id=f"{spec.invocation_id}:validated",
            occurred_at=T3,
        )
        self.store.record_replay_point(
            ReplayPoint(
                replay_point_id=f"{spec.invocation_id}:after",
                invocation_id=spec.invocation_id,
                position="after",
                sequence_number=sequence + 1,
                context_text=CONTEXT,
                context_sha256=digest(CONTEXT),
                context_fragments=CONTEXT_FRAGMENTS,
                capabilities=CAPABILITIES,
                environment=ENVIRONMENT,
                capture_completeness="typed_gap",
                gap_code="provider_hidden_context_gap",
                created_at=T4,
            )
        )

    def publication(self, invocation_id: str = "inv-worker-1") -> ArtifactPublication:
        content = "synthetic fixture result"
        return ArtifactPublication(
            publication_transaction_id="publication-001",
            idempotency_key="publication:idempotency:001",
            run_id="run-001",
            expected_run_revision=self.revision,
            invocation_id=invocation_id,
            artifact_id="artifact-001",
            artifact_version_id="artifact-version-001",
            content_text=content,
            content_sha256=digest(content),
            media_type="text/plain",
            schema_id="bootstrap-synthetic-result",
            schema_version="1",
            schema_sha256=H_B,
            correlation_id="correlation-001",
            caused_by_event_id="event-started",
            version_created_event_id="event-version-created",
            version_created_idempotency_key="event:version-created",
            handoff_event_id="event-handoff-ready",
            handoff_idempotency_key="event:handoff-ready",
            event_schema_id="event-envelope",
            event_schema_version="1",
            event_schema_sha256=H_A,
            lineage=(
                LineageRef(
                    lineage_id="lineage-001",
                    parent_ref_kind="fixture_input",
                    parent_external_ref="fixture:seed:request.yaml",
                    relation="produced_from",
                ),
            ),
            created_at=T4,
        )

    def ready_worker(self) -> InvocationSpec:
        spec = self.create_delivery_and_invocation()
        self.record_success(spec)
        return spec

    def assert_no_publication(self) -> None:
        self.assertEqual(
            self.store.publication_counts(),
            {
                "artifacts": 0,
                "artifact_versions": 0,
                "publication_events": 0,
                "event_deliveries": 0,
                "publications": 0,
            },
        )

    def test_migration_is_deterministic_and_reinitialization_is_a_noop(self) -> None:
        first_fingerprint = self.store.schema_fingerprint()
        second_sha = self.store.initialize()
        second_fingerprint = self.store.schema_fingerprint()
        self.assertEqual(self.migration_sha, second_sha)
        self.assertEqual(first_fingerprint, second_fingerprint)
        migration = self.store.migration_record()
        self.assertEqual(migration["version"], 1)
        self.assertEqual(migration["sha256"], self.migration_sha)

    def test_changed_migration_bytes_are_rejected_after_initialization(self) -> None:
        changed_migration = Path(self.temp.name) / "changed.sql"
        original = self.store.migration_path.read_bytes()
        changed_migration.write_bytes(original + b"\n")
        changed_store = K0a01Store(self.db_path, changed_migration)
        with self.assertRaises(MigrationError):
            changed_store.initialize()

    def test_schema_declares_no_blob_payload_column(self) -> None:
        connection = sqlite3.connect(self.db_path)
        try:
            declarations = []
            for table in ("replay_points", "invocation_telemetry", "artifact_versions", "events"):
                declarations.extend(
                    row[2].upper()
                    for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
                )
            self.assertNotIn("BLOB", declarations)
        finally:
            connection.close()

    def test_replay_rejects_fragment_without_exact_role_byte_hash_binding(self) -> None:
        spec = self.create_delivery_and_invocation()
        weak_fragments = ({"role": "user"},)
        weak_context = json.dumps(weak_fragments, sort_keys=True, separators=(",", ":"))
        with self.assertRaises(IntegrityConflict):
            self.store.record_replay_point(
                ReplayPoint(
                    replay_point_id="weak-before",
                    invocation_id=spec.invocation_id,
                    position="before",
                    sequence_number=0,
                    context_text=weak_context,
                    context_sha256=digest(weak_context),
                    context_fragments=weak_fragments,
                    capabilities=CAPABILITIES,
                    environment=ENVIRONMENT,
                    capture_completeness="typed_gap",
                    gap_code="provider_hidden_context_gap",
                    created_at=T1,
                )
            )

    def test_telemetry_rejects_inconsistent_usage_or_monotonic_time(self) -> None:
        spec = self.create_delivery_and_invocation()
        self.record_before(spec)
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="replay_before_committed",
            new_state="dispatched",
            transition_id="inv-worker-1:dispatched",
            occurred_at=T2,
        )
        invalid = InvocationTelemetry(
            telemetry_id="invalid-telemetry",
            invocation_id=spec.invocation_id,
            provider=spec.provider,
            model_profile=spec.model_profile,
            model_identifier=spec.model_identifier,
            parameters=spec.parameters,
            response_text=RESPONSE,
            response_sha256=digest(RESPONSE),
            started_at=T2,
            completed_at=T3,
            duration_ms=999,
            monotonic_started_ns=1_000_000_000,
            monotonic_completed_ns=2_000_000_000,
            input_tokens=1,
            output_tokens=1,
            total_tokens=3,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 3},
            finish_reason="stop",
        )
        with self.assertRaises(IntegrityConflict):
            self.store.record_telemetry(invalid)

    def test_exact_before_and_after_replay_envelopes_preserve_all_pins(self) -> None:
        spec = self.create_delivery_and_invocation()
        self.record_success(spec)
        before = self.store.read_replay_envelope("inv-worker-1:before")
        after = self.store.read_replay_envelope("inv-worker-1:after")
        for envelope in (before, after):
            self.assertEqual(envelope["run_id"], "run-001")
            self.assertEqual(envelope["delivery_id"], "delivery-worker")
            self.assertEqual(envelope["invocation_id"], "inv-worker-1")
            self.assertEqual(envelope["attempt_number"], 1)
            self.assertEqual(envelope["pipeline_commit"], PIPELINE_COMMIT)
            self.assertEqual(envelope["fixture"], {"commit": FIXTURE_COMMIT, "tree": FIXTURE_TREE})
            self.assertEqual(envelope["prompt"]["sha256"], H_A)
            self.assertEqual(envelope["contract"]["sha256"], H_B)
            self.assertEqual(envelope["result_schema"]["sha256"], H_C)
            self.assertEqual(envelope["registry_sha256"], H_A)
            self.assertEqual(envelope["context"]["text"], CONTEXT)
            self.assertEqual(envelope["context"]["sha256"], digest(CONTEXT))
            self.assertEqual(envelope["model"]["parameters"], {"temperature": 0, "top_p": 1})
            self.assertEqual(envelope["model"]["context_limit_tokens"], 4096)
            self.assertEqual(envelope["context"]["fragments"][0]["content_sha256"], digest("fixture-only policy"))
            self.assertEqual(envelope["capture_completeness"], "typed_gap")
            self.assertEqual(envelope["gap_code"], "provider_hidden_context_gap")
        self.assertIsNone(before["result"])
        self.assertEqual(after["result"]["text"], RESPONSE)
        self.assertEqual(after["result"]["sha256"], digest(RESPONSE))
        self.assertEqual(after["result"]["telemetry"]["duration_ms"], 1000)
        self.assertEqual(after["result"]["telemetry"]["monotonic_started_ns"], 1_000_000_000)
        self.assertEqual(
            after["result"]["telemetry"]["usage"],
            {"input_tokens": 12, "output_tokens": 5, "total_tokens": 17},
        )

    def test_successful_publication_commits_version_two_events_and_snapshots_atomically(self) -> None:
        self.ready_worker()
        result = self.store.publish_artifact_version(self.publication())
        self.assertFalse(result.idempotent_replay)
        self.assertEqual(result.committed_run_revision, self.revision + 1)
        self.assertEqual(
            self.store.publication_counts(),
            {
                "artifacts": 1,
                "artifact_versions": 1,
                "publication_events": 2,
                "event_deliveries": 2,
                "publications": 1,
            },
        )
        version_event = self.store.event_record("event-version-created")
        handoff_event = self.store.event_record("event-handoff-ready")
        self.assertEqual(version_event["artifact_version_id"], "artifact-version-001")
        self.assertEqual(handoff_event["artifact_version_id"], "artifact-version-001")
        self.assertEqual(handoff_event["caused_by_event_id"], "event-version-created")

    def test_artifact_versions_events_and_lineage_are_immutable(self) -> None:
        self.ready_worker()
        self.store.publish_artifact_version(self.publication())
        connection = sqlite3.connect(self.db_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifact_versions SET content_text = 'changed' WHERE artifact_version_id = 'artifact-version-001'"
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM events WHERE event_id = 'event-handoff-ready'")
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM artifact_version_lineage WHERE lineage_id = 'lineage-001'")
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE physical_invocations SET contract_sha256 = ? WHERE invocation_id = 'inv-worker-1'",
                    (H_C,),
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE event_deliveries SET subscriber_id = 'bootstrap_sink', terminal_policy = 'fixture_terminal' "
                    "WHERE event_id = 'event-started'"
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE runs SET fixture_tree = '0000000000000000000000000000000000000000' WHERE run_id = 'run-001'"
                )
        finally:
            connection.rollback()
            connection.close()

    def test_exception_before_commit_leaves_no_artifact_version_event_or_publication(self) -> None:
        self.ready_worker()

        def fail(stage: str) -> None:
            if stage == "after_events":
                raise InjectedFailure("fault before commit")

        with self.assertRaises(InjectedFailure):
            self.store.publish_artifact_version(self.publication(), fault_hook=fail)
        self.assert_no_publication()

    def test_other_connection_never_observes_partially_published_pair(self) -> None:
        self.ready_worker()
        observations = []

        def observe(stage: str) -> None:
            if stage in {"after_artifact_version", "after_events"}:
                observations.append((stage, dict(self.store.publication_counts())))

        self.store.publish_artifact_version(self.publication(), fault_hook=observe)
        self.assertEqual(len(observations), 2)
        for _, counts in observations:
            self.assertTrue(all(value == 0 for value in counts.values()))
        self.assertEqual(self.store.publication_counts()["publications"], 1)

    def test_exact_idempotency_replay_returns_original_identity_without_duplicates(self) -> None:
        self.ready_worker()
        first = self.store.publish_artifact_version(self.publication())
        second = self.store.publish_artifact_version(self.publication())
        self.assertFalse(first.idempotent_replay)
        self.assertTrue(second.idempotent_replay)
        self.assertEqual(first.artifact_version_id, second.artifact_version_id)
        self.assertEqual(self.store.publication_counts()["artifact_versions"], 1)
        self.assertEqual(self.store.publication_counts()["publication_events"], 2)

    def test_conflicting_idempotency_identity_fails_closed(self) -> None:
        self.ready_worker()
        publication = self.publication()
        self.store.publish_artifact_version(publication)
        conflicting = replace(
            publication,
            artifact_version_id="artifact-version-conflict",
            publication_transaction_id="publication-conflict",
        )
        with self.assertRaises(IdempotencyConflict):
            self.store.publish_artifact_version(conflicting)
        self.assertEqual(self.store.publication_counts()["artifact_versions"], 1)

    def test_stale_run_revision_fails_closed_before_any_publication_row(self) -> None:
        self.ready_worker()
        with self.assertRaises(StaleState):
            self.store.publish_artifact_version(
                replace(self.publication(), expected_run_revision=self.revision - 1)
            )
        self.assert_no_publication()

    def test_late_physical_attempt_is_fenced_and_cannot_publish(self) -> None:
        attempt1 = self.create_delivery_and_invocation()
        self.record_before(attempt1)
        self.store.transition_invocation(
            invocation_id=attempt1.invocation_id,
            expected_state="replay_before_committed",
            new_state="dispatched",
            transition_id="inv-worker-1:dispatched",
            occurred_at=T2,
        )
        self.store.record_invocation_failure(
            invocation_id=attempt1.invocation_id,
            failure_code="timeout_before_accepted_response",
            transition_id="inv-worker-1:timeout",
            occurred_at=T3,
        )
        attempt2 = self.create_delivery_and_invocation(
            invocation_id="inv-worker-2", attempt_number=2
        )
        self.record_success(attempt2, sequence=1)
        with self.assertRaises(StaleState):
            self.store.publish_artifact_version(self.publication(invocation_id=attempt1.invocation_id))
        self.assert_no_publication()
        result = self.store.publish_artifact_version(
            replace(
                self.publication(invocation_id=attempt2.invocation_id),
                publication_transaction_id="publication-attempt-2",
                idempotency_key="publication:idempotency:attempt-2",
            )
        )
        self.assertEqual(result.artifact_version_id, "artifact-version-001")

    def test_retry_rejects_changed_invocation_pins_and_context(self) -> None:
        attempt1 = self.create_delivery_and_invocation()
        self.record_before(attempt1)
        self.store.record_invocation_failure(
            invocation_id=attempt1.invocation_id,
            failure_code="transient_unavailable_before_dispatch_ack",
            transition_id="inv-worker-1:unavailable",
            occurred_at=T2,
        )
        drifted_spec = replace(
            self.invocation_spec("inv-worker-2", "delivery-worker", 2),
            provider="different-provider",
        )
        with self.assertRaises(StaleState):
            self.store.create_invocation(drifted_spec)

        attempt2 = self.create_delivery_and_invocation(
            invocation_id="inv-worker-2", attempt_number=2
        )
        drifted_fragments = (
            CONTEXT_FRAGMENTS[0],
            {
                "ordinal": 1,
                "role": "user",
                "content_text": "different retry context",
                "content_sha256": digest("different retry context"),
            },
        )
        drifted_context = json.dumps(
            drifted_fragments,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.assertRaises(StaleState):
            self.store.record_replay_point(
                ReplayPoint(
                    replay_point_id="inv-worker-2:before-drift",
                    invocation_id=attempt2.invocation_id,
                    position="before",
                    sequence_number=1,
                    context_text=drifted_context,
                    context_sha256=digest(drifted_context),
                    context_fragments=drifted_fragments,
                    capabilities=CAPABILITIES,
                    environment=ENVIRONMENT,
                    capture_completeness="typed_gap",
                    gap_code="provider_hidden_context_gap",
                    created_at=T3,
                )
            )

    def test_after_replay_rejects_context_capability_or_environment_drift(self) -> None:
        spec = self.create_delivery_and_invocation()
        self.record_before(spec)
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="replay_before_committed",
            new_state="dispatched",
            transition_id="inv-worker-1:dispatched",
            occurred_at=T2,
        )
        self.store.record_telemetry(
            InvocationTelemetry(
                telemetry_id="inv-worker-1:telemetry",
                invocation_id=spec.invocation_id,
                provider=spec.provider,
                model_profile=spec.model_profile,
                model_identifier=spec.model_identifier,
                parameters=spec.parameters,
                response_text=RESPONSE,
                response_sha256=digest(RESPONSE),
                started_at=T2,
                completed_at=T3,
                duration_ms=1000,
                monotonic_started_ns=1_000_000_000,
                monotonic_completed_ns=2_000_000_000,
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                finish_reason="stop",
            )
        )
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="response_captured",
            new_state="validated",
            transition_id="inv-worker-1:validated",
            occurred_at=T3,
        )
        with self.assertRaises(StaleState):
            self.store.record_replay_point(
                ReplayPoint(
                    replay_point_id="inv-worker-1:after-drift",
                    invocation_id=spec.invocation_id,
                    position="after",
                    sequence_number=1,
                    context_text=CONTEXT,
                    context_sha256=digest(CONTEXT),
                    context_fragments=CONTEXT_FRAGMENTS,
                    capabilities=CAPABILITIES,
                    environment={**ENVIRONMENT, "adapter_version": "different-adapter"},
                    capture_completeness="typed_gap",
                    gap_code="provider_hidden_context_gap",
                    created_at=T4,
                )
            )

    def test_foreign_key_violation_rolls_back_the_entire_publication(self) -> None:
        self.ready_worker()
        broken = replace(
            self.publication(),
            lineage=(
                LineageRef(
                    lineage_id="lineage-missing-parent",
                    parent_ref_kind="artifact_version",
                    parent_artifact_version_id="missing-parent-version",
                    relation="derived_from",
                ),
            ),
        )
        with self.assertRaises(IntegrityConflict):
            self.store.publish_artifact_version(broken)
        self.assert_no_publication()

    def test_composite_foreign_keys_reject_cross_run_artifact_and_causation_graphs(self) -> None:
        self.ready_worker()
        self.store.create_run(
            run_id="run-002",
            pipeline_commit=PIPELINE_COMMIT,
            fixture_commit=FIXTURE_COMMIT,
            fixture_tree=FIXTURE_TREE,
            created_at=T4,
        )
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO artifacts(artifact_id, run_id, artifact_type, logical_owner, created_at) "
                "VALUES ('cross-artifact', 'run-001', 'bootstrap.synthetic_result', 'fixture.bootstrap_worker', ?)",
                (T4,),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO artifact_versions(artifact_version_id, artifact_id, run_id, producing_invocation_id, media_type, encoding, "
                    "schema_id, schema_version, schema_sha256, hash_profile_id, content_text, content_sha256, content_size_bytes, idempotency_key, created_at) "
                    "VALUES ('cross-version', 'cross-artifact', 'run-002', 'inv-worker-1', 'text/plain', 'utf-8', "
                    "'schema', '1', ?, 'sha256-utf8-v1', 'ok', ?, 2, 'cross-key', ?)",
                    (H_A, digest("ok"), T4),
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO events(event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, "
                    "caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, idempotency_key, created_at) "
                    "VALUES ('cross-event', 'run-002', 'run.started', 1, NULL, NULL, 'event-started', 'cross-correlation', "
                    "'event-envelope', '1', ?, '{}', ?, 'cross-event-key', ?)",
                    (H_A, digest("{}"), T4),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_replay_fk_rejects_cross_invocation_telemetry_substitution(self) -> None:
        first = self.create_delivery_and_invocation()
        self.record_success(first)
        second = self.create_delivery_and_invocation(
            delivery_id="delivery-worker-2", invocation_id="inv-worker-2"
        )
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            source = dict(
                connection.execute(
                    "SELECT * FROM replay_points WHERE replay_point_id = ?",
                    ("inv-worker-1:after",),
                ).fetchone()
            )
            source.update(
                replay_point_id="inv-worker-2:forged-after",
                delivery_id=second.delivery_id,
                invocation_id=second.invocation_id,
                sequence_number=2,
            )
            columns = tuple(source)
            placeholders = ", ".join("?" for _ in columns)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    f"INSERT INTO replay_points({', '.join(columns)}) VALUES ({placeholders})",
                    tuple(source[column] for column in columns),
                )
            connection.rollback()
            self.assertEqual(
                connection.execute("PRAGMA foreign_key_check").fetchall(),
                [],
            )
        finally:
            connection.rollback()
            connection.close()

    def test_blob_and_non_utf8_artifacts_are_rejected_before_transaction(self) -> None:
        self.ready_worker()
        publication = self.publication()
        for forbidden in (b"binary", b"\xff\xfe"):
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(TextPolicyError):
                    self.store.publish_artifact_version(
                        replace(publication, content_text=forbidden)  # type: ignore[arg-type]
                    )
        self.assert_no_publication()

    def test_database_constraint_rejects_blob_in_text_column(self) -> None:
        self.ready_worker()
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO artifacts(artifact_id, run_id, artifact_type, logical_owner, created_at) "
                "VALUES ('direct-artifact', 'run-001', 'bootstrap.synthetic_result', 'fixture.bootstrap_worker', ?)",
                (T4,),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO artifact_versions(artifact_version_id, artifact_id, run_id, producing_invocation_id, media_type, encoding, "
                    "schema_id, schema_version, schema_sha256, hash_profile_id, content_text, content_sha256, content_size_bytes, idempotency_key, created_at) "
                    "VALUES ('direct-version', 'direct-artifact', 'run-001', 'inv-worker-1', 'text/plain', 'utf-8', "
                    "'schema', '1', ?, 'sha256-utf8-v1', ?, ?, 2, 'direct-key', ?)",
                    (H_A, sqlite3.Binary(b"\xff\xfe"), digest("xx"), T4),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_s0_blocker_telemetry_cannot_be_laundered_into_validated_route(self) -> None:
        spec = self.create_delivery_and_invocation(
            role="S0", delivery_id="delivery-s0-launder", invocation_id="inv-s0-launder"
        )
        self.record_before(spec)
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="replay_before_committed",
            new_state="dispatched",
            transition_id="inv-s0-launder:dispatched",
            occurred_at=T2,
        )
        response = '{"type":"semantic_blocker"}'
        self.store.record_telemetry(
            InvocationTelemetry(
                telemetry_id="inv-s0-launder:telemetry",
                invocation_id=spec.invocation_id,
                provider=spec.provider,
                model_profile=spec.model_profile,
                model_identifier=spec.model_identifier,
                parameters=spec.parameters,
                response_text=response,
                response_sha256=digest(response),
                started_at=T2,
                completed_at=T3,
                duration_ms=1,
                monotonic_started_ns=1_000_000,
                monotonic_completed_ns=2_000_000,
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                finish_reason="stop",
            )
        )
        self.store.transition_invocation(
            invocation_id=spec.invocation_id,
            expected_state="response_captured",
            new_state="validated",
            transition_id="inv-s0-launder:validated",
            occurred_at=T3,
        )
        self.store.record_replay_point(
            ReplayPoint(
                replay_point_id="inv-s0-launder:after",
                invocation_id=spec.invocation_id,
                position="after",
                sequence_number=1,
                context_text=CONTEXT,
                context_sha256=digest(CONTEXT),
                context_fragments=CONTEXT_FRAGMENTS,
                capabilities=CAPABILITIES,
                environment=ENVIRONMENT,
                capture_completeness="typed_gap",
                gap_code="provider_hidden_context_gap",
                created_at=T4,
            )
        )
        with self.assertRaises(IntegrityConflict):
            self.store.record_s0_route_validation(
                proposal_id="laundered-proposal",
                invocation_id=spec.invocation_id,
                accepted=True,
                created_at=T4,
            )
        self.store.record_s0_route_validation(
            proposal_id="rejected-blocker",
            invocation_id=spec.invocation_id,
            accepted=False,
            created_at=T4,
        )
        row = self.store.route_proposal_record("rejected-blocker")
        self.assertEqual(row["raw_output_text"], response)
        self.assertEqual(row["raw_output_type"], "semantic_blocker")
        self.assertEqual(row["terminal_state"], "failed_validation")

    def test_s0_binding_persists_only_validated_route_and_rejects_blocker_or_abstention(self) -> None:
        outcomes = (
            ("s0_route_proposal", True, "validated_route_proposal", None),
            ("semantic_blocker", False, None, "failed_validation"),
            ("abstention", False, None, "failed_validation"),
        )
        for index, (raw_type, accepted, persisted, terminal) in enumerate(outcomes):
            delivery_id = f"delivery-s0-{index}"
            invocation_id = f"inv-s0-{index}"
            spec = self.create_delivery_and_invocation(
                role="S0", delivery_id=delivery_id, invocation_id=invocation_id
            )
            self.record_before(spec, sequence=index * 2)
            self.store.transition_invocation(
                invocation_id=invocation_id,
                expected_state="replay_before_committed",
                new_state="dispatched",
                transition_id=f"{invocation_id}:dispatched",
                occurred_at=T2,
            )
            response = json.dumps(
                {"route": "synthetic_Layer0", "type": raw_type}
                if raw_type == "s0_route_proposal"
                else {"type": raw_type},
                sort_keys=True,
                separators=(",", ":"),
            )
            telemetry = InvocationTelemetry(
                telemetry_id=f"{invocation_id}:telemetry",
                invocation_id=invocation_id,
                provider=spec.provider,
                model_profile=spec.model_profile,
                model_identifier=spec.model_identifier,
                parameters=spec.parameters,
                response_text=response,
                response_sha256=digest(response),
                started_at=T2,
                completed_at=T3,
                duration_ms=1,
                monotonic_started_ns=1_000_000,
                monotonic_completed_ns=2_000_000,
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                finish_reason="stop",
            )
            self.store.record_telemetry(telemetry)
            self.store.transition_invocation(
                invocation_id=invocation_id,
                expected_state="response_captured",
                new_state="validated",
                transition_id=f"{invocation_id}:validated",
                occurred_at=T3,
            )
            self.store.record_replay_point(
                ReplayPoint(
                    replay_point_id=f"{invocation_id}:after",
                    invocation_id=invocation_id,
                    position="after",
                    sequence_number=index * 2 + 1,
                    context_text=CONTEXT,
                    context_sha256=digest(CONTEXT),
                    context_fragments=CONTEXT_FRAGMENTS,
                    capabilities=CAPABILITIES,
                    environment=ENVIRONMENT,
                    capture_completeness="typed_gap",
                    gap_code="provider_hidden_context_gap",
                    created_at=T4,
                )
            )
            self.store.record_s0_route_validation(
                proposal_id=f"proposal-{index}",
                invocation_id=invocation_id,
                accepted=accepted,
                created_at=T4,
            )
            row = self.store.route_proposal_record(f"proposal-{index}")
            self.assertEqual(row["persisted_output_type"], persisted)
            self.assertEqual(row["terminal_state"], terminal)
        accepted_downstream = self.create_delivery_and_invocation(
            role="synthetic_Layer0",
            delivery_id="delivery-layer0-accepted",
            invocation_id="inv-layer0-accepted",
        )
        rejected_downstream = self.create_delivery_and_invocation(
            role="synthetic_Layer0",
            delivery_id="delivery-layer0-rejected",
            invocation_id="inv-layer0-rejected",
        )
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO route_proposal_consumptions(consumption_id, proposal_id, downstream_invocation_id, created_at) "
                "VALUES ('consumption-accepted', 'proposal-0', ?, ?)",
                (accepted_downstream.invocation_id, T4),
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO route_proposal_consumptions(consumption_id, proposal_id, downstream_invocation_id, created_at) "
                    "VALUES ('consumption-rejected', 'proposal-1', ?, ?)",
                    (rejected_downstream.invocation_id, T4),
                )
            connection.rollback()
            accepted_count = connection.execute(
                "SELECT count(*) FROM route_proposal_consumptions WHERE proposal_id = 'proposal-0'"
            ).fetchone()[0]
            rejected_count = connection.execute(
                "SELECT count(*) FROM route_proposal_consumptions WHERE proposal_id IN ('proposal-1', 'proposal-2')"
            ).fetchone()[0]
            self.assertEqual(accepted_count, 1)
            self.assertEqual(rejected_count, 0)
        finally:
            connection.close()

    def test_k0a01_cannot_mark_run_completed_without_future_sink_readback_gate(self) -> None:
        with self.assertRaises(IntegrityConflict):
            self.store.transition_run(
                run_id="run-001",
                expected_state="running",
                expected_revision=self.revision,
                new_state="completed",
                transition_id="run-001:completed",
                occurred_at=T4,
            )

    def test_tests_use_disposable_database_and_leave_canonical_fixture_clean(self) -> None:
        fixture = ROOT / "projects" / "pipeline-v2-fixture"
        self.assertTrue(self.db_path.is_relative_to(Path(self.temp.name)))
        before = subprocess.run(
            ["git", "-C", str(fixture), "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.ready_worker()
        self.store.publish_artifact_version(self.publication())
        after = subprocess.run(
            ["git", "-C", str(fixture), "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(before, "")
        self.assertEqual(after, "")


if __name__ == "__main__":
    unittest.main()
