"""Forward-only K0a-03 persistence for manual extension handoffs."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Mapping

from harness.k0a01.store import (
    IntegrityConflict,
    MigrationError,
    RETRIABLE_FAILURES,
    _canonical_json,
    _git_object,
    _hash,
    _sha256_text,
    _strict_text,
    _timestamp,
)
from harness.k0a02.store import (
    K0A01_MIGRATION_SHA256,
    K0A02_MIGRATION_SHA256,
    K0a02Store,
)


K0A03_MIGRATION_SHA256 = "0e0b59b111e53406158c6d58ce533ab5b4676e90a6f1f9261583f1b73a79557b"


class K0a03Store(K0a02Store):
    SCHEMA_VERSION = 3
    MIGRATION_NAME = "0003_k0a03"

    def __init__(
        self,
        db_path: str | Path,
        migration_0001_path: str | Path | None = None,
        migration_0002_path: str | Path | None = None,
        migration_0003_path: str | Path | None = None,
    ) -> None:
        super().__init__(db_path, migration_0001_path, migration_0002_path)
        self.migration_0003_path = (
            Path(migration_0003_path)
            if migration_0003_path is not None
            else Path(__file__).resolve().parent.parent / "migrations" / "0003_k0a03.sql"
        )

    @classmethod
    def _expected_k0a03_schema(cls, *scripts: str) -> str:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA recursive_triggers = ON")
            for script in scripts:
                for statement in cls._statements(script):
                    connection.execute(statement)
            return cls._schema_fingerprint_from(connection)
        except sqlite3.DatabaseError as exc:
            raise MigrationError("K0a-03 migrations cannot build the expected schema") from exc
        finally:
            connection.close()

    def initialize(self) -> str:
        if not self.db_path.parent.is_dir():
            raise MigrationError("database parent must already exist")
        migration_0001, hash_0001 = self._migration(self.migration_path, K0A01_MIGRATION_SHA256)
        migration_0002, hash_0002 = self._migration(
            self.migration_0002_path, K0A02_MIGRATION_SHA256
        )
        migration_0003, hash_0003 = self._migration(
            self.migration_0003_path, K0A03_MIGRATION_SHA256
        )
        expected_schema = self._expected_k0a03_schema(
            migration_0001, migration_0002, migration_0003
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version < 2:
                connection.execute("ROLLBACK")
                super().initialize()
                connection.execute("BEGIN IMMEDIATE")
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version == 2:
                records = connection.execute(
                    "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
                ).fetchall()
                if [tuple(row) for row in records] != [
                    (1, "0001_k0a01", hash_0001),
                    (2, "0002_k0a02", hash_0002),
                ]:
                    raise MigrationError("historical migration records differ before K0a-03")
                expected_0002 = self._expected_k0a02_schema(migration_0001, migration_0002)
                if self._schema_fingerprint_from(connection) != expected_0002:
                    raise MigrationError("schema version 2 differs from committed K0a-02 migrations")
                for statement in self._statements(migration_0003):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (3, '0003_k0a03', ?)",
                    (hash_0003,),
                )
                connection.execute("PRAGMA user_version = 3")
            elif version != 3:
                raise MigrationError(f"unsupported schema version {version}")
            records = connection.execute(
                "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
            ).fetchall()
            if [tuple(row) for row in records] != [
                (1, "0001_k0a01", hash_0001),
                (2, "0002_k0a02", hash_0002),
                (3, "0003_k0a03", hash_0003),
            ]:
                raise MigrationError("K0a-03 migration identities are incomplete, stale, or extra")
            if self._schema_fingerprint_from(connection) != expected_schema:
                raise MigrationError("live schema differs from exact 0001+0002+0003 migrations")
            connection.execute("COMMIT")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise MigrationError("post-migration integrity_check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise MigrationError("post-migration foreign_key_check failed")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return hash_0003

    @staticmethod
    def _insert_start_event(
        connection: sqlite3.Connection,
        *,
        event_id: str,
        run_id: str,
        event_type: str,
        caused_by_event_id: str | None,
        correlation_id: str,
        schema_id: str,
        schema_version: str,
        schema_sha256: str,
        payload: Mapping[str, Any],
        created_at: str,
    ) -> None:
        if event_type == "command.received":
            subscriber, policy, state = "s0_control_delivery", "control_delivery", "pending"
            fields = ["run_id", "profile", "command"]
        elif event_type == "run.started":
            subscriber = "bootstrap_readback"
            policy, state = "observational_terminal", "observed_terminal"
            fields = ["run_id", "state"]
        else:
            raise IntegrityConflict("atomic start accepts only its two control events")
        payload_json = _canonical_json(payload)
        connection.execute(
            "INSERT INTO events(event_id, run_id, event_type, event_version, "
            "initiated_by_invocation_id, artifact_version_id, caused_by_event_id, "
            "correlation_id, schema_id, schema_version, schema_sha256, payload_json, "
            "payload_sha256, idempotency_key, created_at) "
            "VALUES (?, ?, ?, 1, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                run_id,
                event_type,
                caused_by_event_id,
                correlation_id,
                schema_id,
                schema_version,
                schema_sha256,
                payload_json,
                _sha256_text(payload_json),
                f"{run_id}:{event_type}",
                created_at,
            ),
        )
        connection.execute(
            "INSERT INTO event_deliveries(event_delivery_id, event_id, subscriber_id, "
            "terminal_policy, state, fields_read_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"{event_id}:delivery:0",
                event_id,
                subscriber,
                policy,
                state,
                _canonical_json(fields),
                created_at,
            ),
        )

    def create_started_run(
        self,
        *,
        run_id: str,
        pipeline_commit: str,
        fixture_commit: str,
        fixture_tree: str,
        created_at: str,
        transition_id: str,
        transitioned_at: str,
        command_event_id: str,
        command_payload: Mapping[str, Any],
        command_created_at: str,
        started_event_id: str,
        started_payload: Mapping[str, Any],
        started_created_at: str,
        correlation_id: str,
        schema_id: str,
        schema_version: str,
        schema_sha256: str,
    ) -> None:
        """Atomically create one running F00 run and both initial control events."""

        for name, value in (
            ("run_id", run_id),
            ("transition_id", transition_id),
            ("command_event_id", command_event_id),
            ("started_event_id", started_event_id),
            ("correlation_id", correlation_id),
            ("schema_id", schema_id),
            ("schema_version", schema_version),
        ):
            _strict_text(name, value)
        _git_object("pipeline_commit", pipeline_commit)
        _git_object("fixture_commit", fixture_commit)
        _git_object("fixture_tree", fixture_tree)
        _hash("schema_sha256", schema_sha256)
        for name, value in (
            ("created_at", created_at),
            ("transitioned_at", transitioned_at),
            ("command_created_at", command_created_at),
            ("started_created_at", started_created_at),
        ):
            _timestamp(name, value)
        if (
            command_payload.get("run_id") != run_id
            or started_payload != {"run_id": run_id, "state": "running"}
        ):
            raise IntegrityConflict("atomic start payload identity differs")
        with self._operation() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, profile, pipeline_commit, fixture_commit, "
                "fixture_tree, state, state_revision, created_at) "
                "VALUES (?, 'F00', ?, ?, ?, 'created', 0, ?)",
                (run_id, pipeline_commit, fixture_commit, fixture_tree, created_at),
            )
            connection.execute(
                "INSERT INTO run_state_transitions(transition_id, run_id, from_state, "
                "to_state, from_revision, to_revision, occurred_at) "
                "VALUES (?, ?, NULL, 'created', NULL, 0, ?)",
                (f"{run_id}:state:0", run_id, created_at),
            )
            connection.execute(
                "UPDATE runs SET state = 'running', state_revision = 1 "
                "WHERE run_id = ? AND state = 'created' AND state_revision = 0",
                (run_id,),
            )
            connection.execute(
                "INSERT INTO run_state_transitions(transition_id, run_id, from_state, "
                "to_state, from_revision, to_revision, occurred_at) "
                "VALUES (?, ?, 'created', 'running', 0, 1, ?)",
                (transition_id, run_id, transitioned_at),
            )
            self._insert_start_event(
                connection,
                event_id=command_event_id,
                run_id=run_id,
                event_type="command.received",
                caused_by_event_id=None,
                correlation_id=correlation_id,
                schema_id=schema_id,
                schema_version=schema_version,
                schema_sha256=schema_sha256,
                payload=command_payload,
                created_at=command_created_at,
            )
            self._insert_start_event(
                connection,
                event_id=started_event_id,
                run_id=run_id,
                event_type="run.started",
                caused_by_event_id=command_event_id,
                correlation_id=correlation_id,
                schema_id=schema_id,
                schema_version=schema_version,
                schema_sha256=schema_sha256,
                payload=started_payload,
                created_at=started_created_at,
            )

    def record_manual_dispatch(self, value: Mapping[str, Any]) -> None:
        required = {
            "before_replay_point_id",
            "context_sha256",
            "context_text",
            "created_at",
            "delivery_id",
            "dispatch_id",
            "execution_mode",
            "executor_key",
            "extension_id",
            "extension_version",
            "invocation_id",
            "model_identifier",
            "model_profile",
            "provider",
            "role",
            "run_id",
            "tool_enforcement",
        }
        if set(value) != required:
            raise IntegrityConflict("manual dispatch fields differ")
        _strict_text("context_text", value["context_text"])
        if _sha256_text(value["context_text"]) != _hash(
            "context_sha256", value["context_sha256"]
        ):
            raise IntegrityConflict("manual dispatch context hash differs")
        _timestamp("created_at", value["created_at"])
        columns = tuple(sorted(required))
        with self._operation() as connection:
            connection.execute(
                f"INSERT INTO manual_dispatches({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                tuple(value[name] for name in columns),
            )

    def record_manual_receipt(self, value: Mapping[str, Any]) -> None:
        required = {
            "accepted_at",
            "dispatch_id",
            "invocation_id",
            "receipt_id",
            "receipt_source",
            "response_sha256",
            "response_text",
            "tool_calls_observed",
            "transcript_event_count",
            "transcript_complete",
            "transcript_sha256",
            "transcript_text",
            "validation_disposition",
        }
        if set(value) != required:
            raise IntegrityConflict("manual receipt fields differ")
        _strict_text("response_text", value["response_text"])
        if _sha256_text(value["response_text"]) != _hash(
            "response_sha256", value["response_sha256"]
        ):
            raise IntegrityConflict("manual receipt response hash differs")
        _strict_text("transcript_text", value["transcript_text"])
        if _sha256_text(value["transcript_text"]) != _hash(
            "transcript_sha256", value["transcript_sha256"]
        ):
            raise IntegrityConflict("manual receipt transcript hash differs")
        if not isinstance(value["transcript_event_count"], int) or value["transcript_event_count"] < 4:
            raise IntegrityConflict("manual receipt transcript event count is invalid")
        _timestamp("accepted_at", value["accepted_at"])
        columns = tuple(sorted(required))
        with self._operation() as connection:
            connection.execute(
                f"INSERT INTO manual_receipts({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                tuple(value[name] for name in columns),
            )

    def record_manual_failure(self, value: Mapping[str, Any]) -> None:
        required = {
            "dispatch_id",
            "failure_code",
            "failure_receipt_id",
            "invocation_id",
            "receipt_source",
            "recorded_at",
            "tool_calls_observed",
            "transcript_complete",
        }
        if set(value) != required:
            raise IntegrityConflict("manual failure fields differ")
        _timestamp("recorded_at", value["recorded_at"])
        columns = tuple(sorted(required))
        with self._operation() as connection:
            connection.execute(
                f"INSERT INTO manual_failures({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                tuple(value[name] for name in columns),
            )

    def record_manual_invocation_failure(
        self, value: Mapping[str, Any], *, transition_id: str
    ) -> None:
        """Atomically fail one invocation and persist its manual failure receipt."""

        required = {
            "dispatch_id",
            "failure_code",
            "failure_receipt_id",
            "invocation_id",
            "receipt_source",
            "recorded_at",
            "tool_calls_observed",
            "transcript_complete",
        }
        if set(value) != required:
            raise IntegrityConflict("manual failure fields differ")
        _timestamp("recorded_at", value["recorded_at"])
        if value["failure_code"] not in RETRIABLE_FAILURES | {
            "non_retriable_provider_failure"
        }:
            raise IntegrityConflict("unknown physical invocation failure code")
        columns = tuple(sorted(required))
        with self._operation() as connection:
            row = self._require_current(connection, value["invocation_id"])
            if (
                row["state"] not in {"replay_before_committed", "dispatched"}
                or row["response_accepted"]
            ):
                raise IntegrityConflict(
                    "only an invocation without an accepted response can fail this way"
                )
            dispatch = connection.execute(
                "SELECT dispatch_id FROM manual_dispatches "
                "WHERE dispatch_id = ? AND invocation_id = ?",
                (value["dispatch_id"], value["invocation_id"]),
            ).fetchone()
            if dispatch is None:
                raise IntegrityConflict("manual failure dispatch identity differs")
            connection.execute(
                "UPDATE physical_invocations "
                "SET state = 'failed_invocation', failure_code = ? WHERE invocation_id = ?",
                (value["failure_code"], value["invocation_id"]),
            )
            delivery_state = (
                "retry_pending"
                if value["failure_code"] in RETRIABLE_FAILURES
                else "failed_invocation"
            )
            connection.execute(
                "UPDATE deliveries SET state = ? WHERE delivery_id = ?",
                (delivery_state, row["delivery_id"]),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions"
                "(transition_id, invocation_id, from_state, to_state, occurred_at) "
                "VALUES (?, ?, ?, 'failed_invocation', ?)",
                (
                    transition_id,
                    value["invocation_id"],
                    row["state"],
                    value["recorded_at"],
                ),
            )
            connection.execute(
                f"INSERT INTO manual_failures({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(value[name] for name in columns),
            )

    def pending_dispatch(self) -> Mapping[str, Any] | None:
        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                "SELECT dispatch.*, invocation.state AS invocation_state, invocation.attempt_number FROM manual_dispatches dispatch "
                "JOIN physical_invocations invocation ON invocation.invocation_id = dispatch.invocation_id "
                "LEFT JOIN manual_receipts receipt ON receipt.dispatch_id = dispatch.dispatch_id "
                "LEFT JOIN manual_failures failure ON failure.dispatch_id = dispatch.dispatch_id "
                "WHERE invocation.state IN ('dispatched', 'response_captured', 'validated', 'replay_after_committed') "
                "AND failure.dispatch_id IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM route_proposals route WHERE route.invocation_id = invocation.invocation_id) "
                "AND NOT EXISTS (SELECT 1 FROM actor_proposals proposal WHERE proposal.invocation_id = invocation.invocation_id) "
                "ORDER BY dispatch.rowid LIMIT 2"
            ).fetchall()
            if len(rows) > 1:
                raise IntegrityConflict("more than one manual dispatch is pending")
            return None if not rows else dict(rows[0])
        finally:
            connection.close()

    def orphan_invocation(self) -> Mapping[str, Any] | None:
        """Return one recoverable prepared invocation lacking its manual dispatch."""

        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                "SELECT invocation.*, delivery.role, delivery.triggering_event_id "
                "FROM physical_invocations invocation "
                "JOIN deliveries delivery ON delivery.delivery_id = invocation.delivery_id "
                "LEFT JOIN manual_dispatches dispatch ON dispatch.invocation_id = invocation.invocation_id "
                "WHERE invocation.state IN ('prepared', 'replay_before_committed', 'dispatched') "
                "AND invocation.fenced = 0 AND dispatch.invocation_id IS NULL "
                "ORDER BY invocation.rowid LIMIT 2"
            ).fetchall()
            if len(rows) > 1:
                raise IntegrityConflict("more than one orphan invocation exists")
            return None if not rows else dict(rows[0])
        finally:
            connection.close()

    def unresolved_manual_failure(self) -> Mapping[str, Any] | None:
        """Return a durable failure whose retry/terminal transition was interrupted."""

        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                "SELECT dispatch.*, invocation.attempt_number, "
                "invocation.state AS invocation_state, failure.failure_code, "
                "delivery.state AS delivery_state, delivery.triggering_event_id "
                "FROM deliveries delivery "
                "JOIN physical_invocations invocation "
                "ON invocation.invocation_id = delivery.current_physical_invocation_id "
                "JOIN manual_dispatches dispatch "
                "ON dispatch.invocation_id = invocation.invocation_id "
                "JOIN manual_failures failure "
                "ON failure.dispatch_id = dispatch.dispatch_id "
                "JOIN runs run ON run.run_id = delivery.run_id "
                "WHERE run.state = 'running' "
                "AND invocation.state = 'failed_invocation' "
                "AND delivery.state IN ('retry_pending', 'failed_invocation') "
                "ORDER BY invocation.rowid LIMIT 2"
            ).fetchall()
            if len(rows) > 1:
                raise IntegrityConflict("more than one unresolved manual failure exists")
            return None if not rows else dict(rows[0])
        finally:
            connection.close()

    def execution_readback(self, run_id: str | None = None) -> Mapping[str, Any]:
        connection = self._connect(query_only=True)
        try:
            if run_id is None:
                rows = connection.execute("SELECT run_id FROM runs ORDER BY rowid LIMIT 2").fetchall()
                if len(rows) != 1:
                    raise IntegrityConflict("execution readback requires exactly one run")
                run_id = rows[0]["run_id"]
            dispatches = connection.execute(
                "SELECT * FROM manual_dispatches WHERE run_id = ? ORDER BY rowid LIMIT 7",
                (run_id,),
            ).fetchall()
            if len(dispatches) > 6:
                raise IntegrityConflict("manual physical invocation budget exceeded")
            receipts = connection.execute(
                "SELECT receipt.* FROM manual_receipts receipt JOIN manual_dispatches dispatch "
                "ON dispatch.dispatch_id = receipt.dispatch_id WHERE dispatch.run_id = ? "
                "ORDER BY receipt.rowid LIMIT 7",
                (run_id,),
            ).fetchall()
            failures = connection.execute(
                "SELECT failure.* FROM manual_failures failure JOIN manual_dispatches dispatch "
                "ON dispatch.dispatch_id = failure.dispatch_id WHERE dispatch.run_id = ? "
                "ORDER BY failure.rowid LIMIT 7",
                (run_id,),
            ).fetchall()
            for row in receipts:
                if _sha256_text(row["response_text"]) != row["response_sha256"]:
                    raise IntegrityConflict("manual receipt readback hash differs")
                if _sha256_text(row["transcript_text"]) != row["transcript_sha256"]:
                    raise IntegrityConflict("manual transcript readback hash differs")
            accepted_receipts = [row for row in receipts if row["validation_disposition"] == "accepted"]
            return {
                "captured_response_receipts": len(receipts),
                "dispatches": [dict(row) for row in dispatches],
                "failures": [dict(row) for row in failures],
                "physical_model_invocations": len(dispatches),
                "receipts": [dict(row) for row in receipts],
                "successful_model_invocations": len(accepted_receipts),
                "type": "k0a03_execution_readback",
            }
        finally:
            connection.close()
