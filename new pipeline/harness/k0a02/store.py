"""Forward-only K0a-02 persistence, sink, and bounded readback gates."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Callable, Mapping

from harness.k0a01.store import (
    ArtifactPublication,
    IntegrityConflict,
    K0a01Store,
    MigrationError,
    PublicationResult,
    StaleState,
    _canonical_json,
    _hash,
    _sha256_text,
    _strict_text,
    _timestamp,
)
from .security import scan_untrusted_text


K0A01_MIGRATION_SHA256 = "9901b21aa733611a36191f07cb139b7a79b5d73fd0184e6347792b091adf4dc3"
K0A02_MIGRATION_SHA256 = "7539ab85afaddac2b520f806787177d78106a934e05f5e2a2229c3ef13c8456b"


@dataclass(frozen=True)
class SinkAcceptance:
    sink_acceptance_id: str
    run_id: str
    event_delivery_id: str
    handoff_event_id: str
    artifact_version_id: str
    profile: str
    artifact_type: str
    logical_owner: str
    media_type: str
    content_text: str
    content_sha256: str
    accepted_at: str


@dataclass(frozen=True)
class ReadbackGate:
    readback_gate_id: str
    run_id: str
    graph_sha256: str
    checked_at: str


class K0a02Store(K0a01Store):
    """K0a-01 API plus the single forward K0a-02 completion gate."""

    SCHEMA_VERSION = 2
    MIGRATION_NAME = "0002_k0a02"

    def __init__(
        self,
        db_path: str | Path,
        migration_0001_path: str | Path | None = None,
        migration_0002_path: str | Path | None = None,
    ):
        super().__init__(db_path, migration_0001_path)
        self.migration_0002_path = (
            Path(migration_0002_path)
            if migration_0002_path is not None
            else Path(__file__).resolve().parent.parent / "migrations" / "0002_k0a02.sql"
        )

    @staticmethod
    def _migration(path: Path, expected_hash: str | None = None) -> tuple[str, str]:
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise MigrationError(f"migration is unavailable: {path.name}") from exc
        if payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
            raise MigrationError(f"{path.name} must be UTF-8 without BOM and LF-only")
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise MigrationError(f"{path.name} is not strict UTF-8") from exc
        digest = sha256(payload).hexdigest()
        if expected_hash is not None and digest != expected_hash:
            raise MigrationError(f"{path.name} committed bytes changed")
        return text, digest

    @classmethod
    def _expected_k0a02_schema(cls, migration_0001: str, migration_0002: str) -> str:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA recursive_triggers = ON")
            for script in (migration_0001, migration_0002):
                for statement in cls._statements(script):
                    connection.execute(statement)
            return cls._schema_fingerprint_from(connection)
        except sqlite3.DatabaseError as exc:
            raise MigrationError("K0a-02 migrations cannot build the expected schema") from exc
        finally:
            connection.close()

    def initialize(self) -> str:
        """Apply 0001 then the sole forward 0002, or verify exact applied bytes."""

        if not self.db_path.parent.is_dir():
            raise MigrationError("database parent must already exist")
        migration_0001, hash_0001 = self._migration(self.migration_path, K0A01_MIGRATION_SHA256)
        migration_0002, hash_0002 = self._migration(
            self.migration_0002_path, K0A02_MIGRATION_SHA256
        )
        expected_schema = self._expected_k0a02_schema(migration_0001, migration_0002)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if user_version == 0:
                for statement in self._statements(migration_0001):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (1, '0001_k0a01', ?)",
                    (hash_0001,),
                )
                connection.execute("PRAGMA user_version = 1")
                user_version = 1
            if user_version == 1:
                row = connection.execute(
                    "SELECT name, sha256 FROM schema_migrations WHERE version = 1"
                ).fetchone()
                if row is None or row["name"] != "0001_k0a01" or row["sha256"] != hash_0001:
                    raise MigrationError("historical K0a-01 migration record does not match committed bytes")
                expected_0001 = self._expected_schema_fingerprint(migration_0001)
                if self._schema_fingerprint_from(connection) != expected_0001:
                    raise MigrationError("schema version 1 differs from committed K0a-01 migration")
                for statement in self._statements(migration_0002):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (2, '0002_k0a02', ?)",
                    (hash_0002,),
                )
                connection.execute("PRAGMA user_version = 2")
            elif user_version != 2:
                raise MigrationError(f"unsupported schema version {user_version}")
            rows = connection.execute(
                "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
            ).fetchall()
            expected_records = [(1, "0001_k0a01", hash_0001), (2, "0002_k0a02", hash_0002)]
            if [tuple(row) for row in rows] != expected_records:
                raise MigrationError("applied migration identities are incomplete, stale, or extra")
            if self._schema_fingerprint_from(connection) != expected_schema:
                raise MigrationError("live SQLite schema does not match exact 0001+0002 migrations")
            connection.execute("COMMIT")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise MigrationError("post-migration SQLite integrity_check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise MigrationError("post-migration SQLite foreign_key_check failed")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return hash_0002

    def publish_artifact_version(
        self,
        publication: ArtifactPublication,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> PublicationResult:
        """Reject secrets/PII before the inherited atomic transaction can persist bytes."""

        scan_untrusted_text(publication.content_text, label="artifact publication content")
        return super().publish_artifact_version(publication, fault_hook=fault_hook)

    def migration_records(self) -> tuple[Mapping[str, Any], ...]:
        connection = self._connect(query_only=True)
        try:
            return tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
                ).fetchall()
            )
        finally:
            connection.close()

    def count_rows(self, table: str) -> int:
        allowed = {
            "runs",
            "deliveries",
            "physical_invocations",
            "replay_points",
            "route_proposals",
            "route_proposal_consumptions",
            "actor_proposals",
            "actor_proposal_consumptions",
            "artifacts",
            "artifact_versions",
            "events",
            "event_deliveries",
            "publication_transactions",
            "sink_acceptances",
            "readback_gates",
        }
        if table not in allowed:
            raise IntegrityConflict("row count is outside the K0a-02 bounded allowlist")
        connection = self._connect(query_only=True)
        try:
            return int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
        finally:
            connection.close()

    def record_actor_proposal(
        self,
        *,
        proposal_id: str,
        invocation_id: str,
        accepted: bool,
        created_at: str,
    ) -> Mapping[str, Any]:
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            invocation = self._require_current(connection, invocation_id)
            if invocation["role"] not in {"synthetic_Layer0", "fixture_worker"}:
                raise IntegrityConflict("actor proposal role is outside K0a-02")
            if invocation["state"] != "replay_after_committed":
                raise StaleState("actor proposal requires current after-replay boundary")
            telemetry = connection.execute(
                "SELECT response_text, response_sha256 FROM invocation_telemetry WHERE invocation_id = ?",
                (invocation_id,),
            ).fetchone()
            if telemetry is None:
                raise IntegrityConflict("actor proposal requires exact raw telemetry")
            try:
                parsed = json.loads(telemetry["response_text"])
            except json.JSONDecodeError:
                parsed = None
            declared_type = parsed.get("type") if isinstance(parsed, dict) else None
            expected_type = (
                "synthetic_layer0_invocation_proposal"
                if invocation["role"] == "synthetic_Layer0"
                else "fixture_worker_publication_proposal"
            )
            result_type = declared_type if declared_type == expected_type else "malformed_or_forbidden"
            if accepted and result_type != expected_type:
                raise IntegrityConflict("only the exact declared actor proposal may be accepted")
            connection.execute(
                "INSERT INTO actor_proposals(proposal_id, run_id, delivery_id, invocation_id, role, raw_output_text, raw_output_sha256, "
                "result_type, validation_disposition, terminal_state, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal_id,
                    invocation["run_id"],
                    invocation["delivery_id"],
                    invocation_id,
                    invocation["role"],
                    telemetry["response_text"],
                    telemetry["response_sha256"],
                    result_type,
                    "accepted" if accepted else "rejected",
                    None if accepted else "failed_validation",
                    created_at,
                ),
            )
            connection.execute(
                "UPDATE deliveries SET state = ? WHERE delivery_id = ?",
                ("result_validated" if accepted else "failed_validation", invocation["delivery_id"]),
            )
            row = connection.execute(
                "SELECT * FROM actor_proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            assert row is not None
            return dict(row)

    def consume_s0_route(
        self,
        *,
        consumption_id: str,
        proposal_id: str,
        downstream_invocation_id: str,
        created_at: str,
    ) -> None:
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            proposal = connection.execute(
                "SELECT invocation_id FROM route_proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise IntegrityConflict("unknown S0 proposal")
            connection.execute(
                "INSERT INTO route_proposal_consumptions(consumption_id, proposal_id, downstream_invocation_id, created_at) "
                "VALUES (?, ?, ?, ?)",
                (consumption_id, proposal_id, downstream_invocation_id, created_at),
            )
            self._publish_consumed_invocation(connection, proposal["invocation_id"], created_at)

    def consume_actor_proposal(
        self,
        *,
        consumption_id: str,
        proposal_id: str,
        downstream_invocation_id: str,
        created_at: str,
    ) -> None:
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            proposal = connection.execute(
                "SELECT invocation_id, run_id FROM actor_proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise IntegrityConflict("unknown actor proposal")
            connection.execute(
                "INSERT INTO actor_proposal_consumptions(consumption_id, proposal_id, run_id, downstream_invocation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (consumption_id, proposal_id, proposal["run_id"], downstream_invocation_id, created_at),
            )
            self._publish_consumed_invocation(connection, proposal["invocation_id"], created_at)

    @staticmethod
    def _publish_consumed_invocation(
        connection: sqlite3.Connection, invocation_id: str, created_at: str
    ) -> None:
        row = connection.execute(
            "SELECT delivery_id, state FROM physical_invocations WHERE invocation_id = ?",
            (invocation_id,),
        ).fetchone()
        if row is None or row["state"] != "replay_after_committed":
            raise StaleState("proposal source is not ready for consumption")
        connection.execute(
            "UPDATE physical_invocations SET state = 'published' WHERE invocation_id = ?",
            (invocation_id,),
        )
        connection.execute(
            "UPDATE deliveries SET state = 'published' WHERE delivery_id = ?", (row["delivery_id"],)
        )
        connection.execute(
            "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) "
            "VALUES (?, ?, 'replay_after_committed', 'published', ?)",
            (f"{invocation_id}:proposal-consumed", invocation_id, created_at),
        )

    def sink_bundle(self, handoff_event_id: str) -> Mapping[str, Any]:
        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                "SELECT e.event_id, e.run_id, e.event_type, e.artifact_version_id, e.payload_json, "
                "ed.event_delivery_id, ed.subscriber_id, ed.terminal_policy, ed.state AS delivery_state, "
                "a.artifact_type, a.logical_owner, v.media_type, v.encoding, v.schema_id, v.schema_version, "
                "v.schema_sha256, v.content_text, v.content_sha256, v.content_size_bytes "
                "FROM events e JOIN event_deliveries ed ON ed.event_id = e.event_id "
                "JOIN artifact_versions v ON v.artifact_version_id = e.artifact_version_id AND v.run_id = e.run_id "
                "JOIN artifacts a ON a.artifact_id = v.artifact_id AND a.run_id = v.run_id "
                "WHERE e.event_id = ? LIMIT 2",
                (handoff_event_id,),
            ).fetchall()
            if len(rows) != 1:
                raise IntegrityConflict("bounded sink lookup requires exactly one handoff delivery")
            result = dict(rows[0])
            result["payload"] = json.loads(result.pop("payload_json"))
            return result
        finally:
            connection.close()

    def accept_sink(self, acceptance: SinkAcceptance) -> None:
        _strict_text("content_text", acceptance.content_text)
        if _sha256_text(acceptance.content_text) != _hash(
            "content_sha256", acceptance.content_sha256
        ):
            raise IntegrityConflict("sink content hash does not match exact text")
        _timestamp("accepted_at", acceptance.accepted_at)
        with self._operation() as connection:
            connection.execute(
                "INSERT INTO sink_acceptances(sink_acceptance_id, run_id, event_delivery_id, handoff_event_id, artifact_version_id, "
                "profile, artifact_type, logical_owner, media_type, content_text, content_sha256, accepted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    acceptance.sink_acceptance_id,
                    acceptance.run_id,
                    acceptance.event_delivery_id,
                    acceptance.handoff_event_id,
                    acceptance.artifact_version_id,
                    acceptance.profile,
                    acceptance.artifact_type,
                    acceptance.logical_owner,
                    acceptance.media_type,
                    acceptance.content_text,
                    acceptance.content_sha256,
                    acceptance.accepted_at,
                ),
            )
            cursor = connection.execute(
                "UPDATE event_deliveries SET state = 'accepted_terminal' "
                "WHERE event_delivery_id = ? AND state = 'pending'",
                (acceptance.event_delivery_id,),
            )
            if cursor.rowcount != 1:
                raise StaleState("sink delivery is no longer pending")

    @staticmethod
    def _require_one(rows: list[sqlite3.Row], label: str) -> sqlite3.Row:
        if len(rows) != 1:
            raise IntegrityConflict(f"bounded readback requires exactly one {label}; got {len(rows)}")
        return rows[0]

    @staticmethod
    def _optional_one(rows: list[sqlite3.Row], label: str) -> sqlite3.Row | None:
        if len(rows) > 1:
            raise IntegrityConflict(f"bounded readback allows at most one {label}; got {len(rows)}")
        return rows[0] if rows else None

    def _precompletion_graph(self, connection: sqlite3.Connection, run_id: str) -> Mapping[str, Any]:
        run = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if run is None or run["state"] != "running":
            raise StaleState("pre-completion readback requires one running run")
        events = connection.execute(
            "SELECT event_id, event_type, caused_by_event_id, artifact_version_id, payload_sha256 "
            "FROM events WHERE run_id = ? ORDER BY rowid LIMIT 6",
            (run_id,),
        ).fetchall()
        if len(events) != 4 or [row["event_type"] for row in events] != [
            "command.received",
            "run.started",
            "artifact.version_created",
            "handoff.ready",
        ]:
            raise IntegrityConflict("pre-completion event profile is not the exact four-event prefix")
        current = connection.execute(
            "SELECT i.invocation_id, i.delivery_id, i.attempt_number, i.state, i.contract_sha256, "
            "i.prompt_sha256, i.result_schema_sha256, d.role, d.triggering_event_id "
            "FROM deliveries d JOIN physical_invocations i ON i.invocation_id = d.current_physical_invocation_id "
            "WHERE d.run_id = ? ORDER BY CASE d.role WHEN 'S0' THEN 1 WHEN 'synthetic_Layer0' THEN 2 ELSE 3 END",
            (run_id,),
        ).fetchall()
        if len(current) != 3 or [row["role"] for row in current] != [
            "S0",
            "synthetic_Layer0",
            "fixture_worker",
        ]:
            raise IntegrityConflict("readback requires exactly one current invocation per F00 role")
        if any(row["state"] != "published" for row in current):
            raise IntegrityConflict("all current F00 invocations must be published")
        all_invocations = connection.execute(
            "SELECT invocation_id, delivery_id, attempt_number, state, fenced, failure_code "
            "FROM physical_invocations WHERE run_id = ? ORDER BY rowid LIMIT 7",
            (run_id,),
        ).fetchall()
        if not 3 <= len(all_invocations) <= 6:
            raise IntegrityConflict("physical invocation count exceeds the pinned retry bound")
        replay = connection.execute(
            "SELECT replay_point_id, invocation_id, position, sequence_number, envelope_sha256 "
            "FROM replay_points WHERE run_id = ? ORDER BY sequence_number LIMIT 10",
            (run_id,),
        ).fetchall()
        if not 6 <= len(replay) <= 9:
            raise IntegrityConflict("replay point count is outside the pinned retry bound")
        publication = self._require_one(
            connection.execute(
                "SELECT * FROM publication_transactions WHERE run_id = ? LIMIT 2", (run_id,)
            ).fetchall(),
            "publication",
        )
        artifact = self._require_one(
            connection.execute(
                "SELECT a.artifact_id, a.artifact_type, a.logical_owner, v.artifact_version_id, "
                "v.producing_invocation_id, v.media_type, v.schema_id, v.schema_version, v.schema_sha256, "
                "v.content_sha256, v.content_size_bytes "
                "FROM artifacts a JOIN artifact_versions v ON v.artifact_id = a.artifact_id AND v.run_id = a.run_id "
                "WHERE a.run_id = ? LIMIT 2",
                (run_id,),
            ).fetchall(),
            "artifact version",
        )
        sink = self._require_one(
            connection.execute(
                "SELECT * FROM sink_acceptances WHERE run_id = ? LIMIT 2", (run_id,)
            ).fetchall(),
            "sink acceptance",
        )
        sink_delivery = self._require_one(
            connection.execute(
                "SELECT delivery.* FROM event_deliveries delivery "
                "JOIN events event ON event.event_id = delivery.event_id "
                "WHERE event.run_id = ? AND delivery.event_delivery_id = ? LIMIT 2",
                (run_id, sink["event_delivery_id"]),
            ).fetchall(),
            "sink event delivery",
        )
        worker_proposal = self._require_one(
            connection.execute(
                "SELECT proposal_id, invocation_id, delivery_id, role, result_type, validation_disposition, terminal_state "
                "FROM actor_proposals WHERE run_id = ? AND invocation_id = ? AND role = 'fixture_worker' "
                "AND result_type = 'fixture_worker_publication_proposal' "
                "AND validation_disposition = 'accepted' AND terminal_state IS NULL LIMIT 2",
                (run_id, current[2]["invocation_id"]),
            ).fetchall(),
            "accepted fixture-worker proposal",
        )
        if (
            sink_delivery["subscriber_id"] != "bootstrap_sink"
            or sink_delivery["terminal_policy"] != "fixture_terminal"
            or sink_delivery["state"] != "accepted_terminal"
        ):
            raise IntegrityConflict("pre-completion sink delivery is not accepted terminal")
        graph = {
            "artifact": dict(artifact),
            "events": [dict(row) for row in events],
            "invocations": [dict(row) for row in all_invocations],
            "replay_points": [dict(row) for row in replay],
            "run": dict(run),
            "sink_delivery": dict(sink_delivery),
            "sink_acceptance": {
                key: sink[key]
                for key in (
                    "sink_acceptance_id",
                    "handoff_event_id",
                    "artifact_version_id",
                    "profile",
                    "content_sha256",
                )
            },
            "worker_proposal": dict(worker_proposal),
        }
        graph["bindings"] = {
            "command_event_id": events[0]["event_id"],
            "started_event_id": events[1]["event_id"],
            "version_created_event_id": events[2]["event_id"],
            "handoff_event_id": events[3]["event_id"],
            "s0_invocation_id": current[0]["invocation_id"],
            "layer0_invocation_id": current[1]["invocation_id"],
            "worker_invocation_id": current[2]["invocation_id"],
            "publication_transaction_id": publication["publication_transaction_id"],
            "artifact_version_id": artifact["artifact_version_id"],
            "sink_acceptance_id": sink["sink_acceptance_id"],
        }
        return graph

    def create_readback_gate(
        self, *, readback_gate_id: str, run_id: str, checked_at: str
    ) -> ReadbackGate:
        _timestamp("checked_at", checked_at)
        with self._operation() as connection:
            graph = self._precompletion_graph(connection, run_id)
            graph_json = _canonical_json(graph)
            graph_sha256 = _sha256_text(graph_json)
            bindings = graph["bindings"]
            connection.execute(
                "INSERT INTO readback_gates(readback_gate_id, run_id, command_event_id, started_event_id, version_created_event_id, "
                "handoff_event_id, s0_invocation_id, layer0_invocation_id, worker_invocation_id, publication_transaction_id, "
                "artifact_version_id, sink_acceptance_id, graph_json, graph_sha256, status, checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'passed', ?)",
                (
                    readback_gate_id,
                    run_id,
                    bindings["command_event_id"],
                    bindings["started_event_id"],
                    bindings["version_created_event_id"],
                    bindings["handoff_event_id"],
                    bindings["s0_invocation_id"],
                    bindings["layer0_invocation_id"],
                    bindings["worker_invocation_id"],
                    bindings["publication_transaction_id"],
                    bindings["artifact_version_id"],
                    bindings["sink_acceptance_id"],
                    graph_json,
                    graph_sha256,
                    checked_at,
                ),
            )
            return ReadbackGate(readback_gate_id, run_id, graph_sha256, checked_at)

    def complete_run(
        self,
        *,
        run_id: str,
        expected_revision: int,
        event_id: str,
        correlation_id: str,
        schema_id: str,
        schema_version: str,
        schema_sha256: str,
        idempotency_key: str,
        occurred_at: str,
    ) -> int:
        _hash("schema_sha256", schema_sha256)
        _timestamp("occurred_at", occurred_at)
        with self._operation() as connection:
            gate = connection.execute(
                "SELECT * FROM readback_gates WHERE run_id = ? AND status = 'passed'", (run_id,)
            ).fetchone()
            if gate is None:
                raise IntegrityConflict("completion requires gate-bearing pre-completion readback")
            cursor = connection.execute(
                "UPDATE runs SET state = 'completed', state_revision = state_revision + 1 "
                "WHERE run_id = ? AND state = 'running' AND state_revision = ?",
                (run_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise StaleState("completion run state or revision changed")
            new_revision = expected_revision + 1
            connection.execute(
                "INSERT INTO run_state_transitions(transition_id, run_id, from_state, to_state, from_revision, to_revision, occurred_at) "
                "VALUES (?, ?, 'running', 'completed', ?, ?, ?)",
                (f"{run_id}:completed", run_id, expected_revision, new_revision, occurred_at),
            )
            payload_json = _canonical_json(
                {
                    "readback_gate_id": gate["readback_gate_id"],
                    "run_id": run_id,
                    "sink_acceptance_id": gate["sink_acceptance_id"],
                    "state": "completed",
                }
            )
            connection.execute(
                "INSERT INTO events(event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, "
                "caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, "
                "idempotency_key, created_at) VALUES (?, ?, 'run.completed', 1, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    run_id,
                    gate["handoff_event_id"],
                    correlation_id,
                    schema_id,
                    schema_version,
                    schema_sha256,
                    payload_json,
                    _sha256_text(payload_json),
                    idempotency_key,
                    occurred_at,
                ),
            )
            connection.execute(
                "INSERT INTO event_deliveries(event_delivery_id, event_id, subscriber_id, terminal_policy, state, fields_read_json, created_at) "
                "VALUES (?, ?, 'bootstrap_readback', 'observational_terminal', 'observed_terminal', ?, ?)",
                (
                    f"{event_id}:delivery:0",
                    event_id,
                    _canonical_json(["run_id", "state", "sink_acceptance_id", "readback_gate_id"]),
                    occurred_at,
                ),
            )
            return new_revision

    def inspect(self, run_id: str | None = None) -> Mapping[str, Any]:
        connection = self._connect(query_only=True)
        try:
            if run_id is None:
                runs = connection.execute("SELECT run_id FROM runs ORDER BY rowid LIMIT 2").fetchall()
                run_id = self._require_one(runs, "run")["run_id"]
            run = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise IntegrityConflict("unknown run")

            control_deliveries = connection.execute(
                "SELECT delivery_id, delivery_key, role, triggering_event_id, state, current_physical_invocation_id, created_at "
                "FROM deliveries WHERE run_id = ? ORDER BY rowid LIMIT 4",
                (run_id,),
            ).fetchall()
            if len(control_deliveries) > 3:
                raise IntegrityConflict("inspect control-delivery bound exceeded")
            invocations = connection.execute(
                "SELECT invocation_id, delivery_id, attempt_number, state, prompt_id, prompt_version, prompt_sha256, "
                "contract_id, contract_version, contract_sha256, result_schema_id, result_schema_version, "
                "result_schema_sha256, registry_sha256, provider, model_profile, model_identifier, parameters_json, "
                "context_limit_tokens, response_accepted, fenced, failure_code, created_at "
                "FROM physical_invocations WHERE run_id = ? ORDER BY rowid LIMIT 7",
                (run_id,),
            ).fetchall()
            if len(invocations) > 6:
                raise IntegrityConflict("inspect invocation bound exceeded")
            telemetry_rows = connection.execute(
                "SELECT telemetry.* FROM invocation_telemetry telemetry "
                "JOIN physical_invocations invocation ON invocation.invocation_id = telemetry.invocation_id "
                "WHERE invocation.run_id = ? ORDER BY telemetry.rowid LIMIT 7",
                (run_id,),
            ).fetchall()
            if len(telemetry_rows) > 6:
                raise IntegrityConflict("inspect telemetry bound exceeded")
            telemetry = []
            for row in telemetry_rows:
                if _sha256_text(row["response_text"]) != row["response_sha256"]:
                    raise IntegrityConflict("inspect telemetry response hash mismatch")
                item = dict(row)
                item["parameters"] = json.loads(item.pop("parameters_json"))
                item["usage"] = json.loads(item.pop("usage_json"))
                telemetry.append(item)

            replay_rows = connection.execute(
                "SELECT replay_point_id, invocation_id, delivery_id, attempt_number, position, sequence_number, "
                "envelope_json, envelope_sha256 FROM replay_points WHERE run_id = ? "
                "ORDER BY sequence_number LIMIT 10",
                (run_id,),
            ).fetchall()
            if len(replay_rows) > 9:
                raise IntegrityConflict("inspect replay bound exceeded")
            replay = []
            for row in replay_rows:
                if _sha256_text(row["envelope_json"]) != row["envelope_sha256"]:
                    raise IntegrityConflict("inspect replay envelope hash mismatch")
                item = dict(row)
                item["envelope"] = json.loads(item["envelope_json"])
                replay.append(item)

            route_proposals = connection.execute(
                "SELECT proposal.* FROM route_proposals proposal "
                "JOIN deliveries delivery ON delivery.delivery_id = proposal.delivery_id "
                "WHERE delivery.run_id = ? ORDER BY proposal.rowid LIMIT 3",
                (run_id,),
            ).fetchall()
            actor_proposals = connection.execute(
                "SELECT * FROM actor_proposals WHERE run_id = ? ORDER BY rowid LIMIT 3",
                (run_id,),
            ).fetchall()
            route_consumptions = connection.execute(
                "SELECT consumption.* FROM route_proposal_consumptions consumption "
                "JOIN route_proposals proposal ON proposal.proposal_id = consumption.proposal_id "
                "JOIN deliveries delivery ON delivery.delivery_id = proposal.delivery_id "
                "WHERE delivery.run_id = ? ORDER BY consumption.rowid LIMIT 2",
                (run_id,),
            ).fetchall()
            actor_consumptions = connection.execute(
                "SELECT * FROM actor_proposal_consumptions WHERE run_id = ? ORDER BY rowid LIMIT 2",
                (run_id,),
            ).fetchall()
            if (
                len(route_proposals) > 2
                or len(actor_proposals) > 2
                or len(route_consumptions) > 1
                or len(actor_consumptions) > 1
            ):
                raise IntegrityConflict("inspect proposal/consumption bound exceeded")

            events = connection.execute(
                "SELECT event_id, event_type, event_version, initiated_by_invocation_id, caused_by_event_id, "
                "correlation_id, artifact_version_id, schema_id, schema_version, schema_sha256, payload_json, "
                "payload_sha256, idempotency_key, created_at "
                "FROM events WHERE run_id = ? ORDER BY rowid LIMIT 6",
                (run_id,),
            ).fetchall()
            if len(events) > 5:
                raise IntegrityConflict("inspect event bound exceeded")
            inspected_events = []
            for row in events:
                if _sha256_text(row["payload_json"]) != row["payload_sha256"]:
                    raise IntegrityConflict("inspect event payload hash mismatch")
                item = dict(row)
                item["payload"] = json.loads(item["payload_json"])
                inspected_events.append(item)
            event_deliveries = connection.execute(
                "SELECT delivery.* FROM event_deliveries delivery "
                "JOIN events event ON event.event_id = delivery.event_id "
                "WHERE event.run_id = ? ORDER BY delivery.rowid LIMIT 6",
                (run_id,),
            ).fetchall()
            if len(event_deliveries) > 5:
                raise IntegrityConflict("inspect event-delivery bound exceeded")

            artifact_rows = connection.execute(
                "SELECT a.artifact_id, a.artifact_type, a.logical_owner, v.artifact_version_id, v.media_type, v.schema_id, "
                "v.schema_version, v.schema_sha256, v.content_text, v.content_sha256, v.content_size_bytes "
                "FROM artifacts a JOIN artifact_versions v ON v.artifact_id = a.artifact_id AND v.run_id = a.run_id "
                "WHERE a.run_id = ? LIMIT 2",
                (run_id,),
            ).fetchall()
            lineage_rows = connection.execute(
                "SELECT * FROM artifact_version_lineage WHERE run_id = ? ORDER BY rowid LIMIT 2",
                (run_id,),
            ).fetchall()
            publication_rows = connection.execute(
                "SELECT * FROM publication_transactions WHERE run_id = ? LIMIT 2", (run_id,)
            ).fetchall()
            sink_rows = connection.execute(
                "SELECT sink_acceptance_id, event_delivery_id, handoff_event_id, artifact_version_id, profile, "
                "artifact_type, logical_owner, media_type, content_text, content_sha256, accepted_at "
                "FROM sink_acceptances WHERE run_id = ? LIMIT 2",
                (run_id,),
            ).fetchall()
            gate_rows = connection.execute(
                "SELECT * FROM readback_gates WHERE run_id = ? LIMIT 2",
                (run_id,),
            ).fetchall()
            artifact = self._optional_one(artifact_rows, "artifact version")
            publication = self._optional_one(publication_rows, "publication")
            sink = self._optional_one(sink_rows, "sink acceptance")
            gate = self._optional_one(gate_rows, "readback gate")
            if len(lineage_rows) > 1:
                raise IntegrityConflict("inspect artifact-lineage bound exceeded")
            artifact_value = dict(artifact) if artifact is not None else {}
            if artifact is not None and _sha256_text(artifact["content_text"]) != artifact["content_sha256"]:
                raise IntegrityConflict("inspect artifact content hash mismatch")
            gate_value = dict(gate) if gate is not None else {}
            if gate is not None:
                if _sha256_text(gate["graph_json"]) != gate["graph_sha256"]:
                    raise IntegrityConflict("inspect readback graph hash mismatch")
                gate_value["graph"] = json.loads(gate["graph_json"])
            result = {
                "artifact": artifact_value,
                "control_deliveries": [dict(row) for row in control_deliveries],
                "event_deliveries": [dict(row) for row in event_deliveries],
                "events": inspected_events,
                "invocations": [dict(row) for row in invocations],
                "lineage": {"artifact_version_edges": [dict(row) for row in lineage_rows]},
                "proposals": {
                    "actor": [dict(row) for row in actor_proposals],
                    "actor_consumptions": [dict(row) for row in actor_consumptions],
                    "s0": [dict(row) for row in route_proposals],
                    "s0_consumptions": [dict(row) for row in route_consumptions],
                },
                "publication": dict(publication) if publication is not None else {},
                "readback_gate": gate_value,
                "replay_points": replay,
                "run": dict(run),
                "sink_acceptance": dict(sink) if sink is not None else {},
                "telemetry": telemetry,
                "type": "inspect_readback",
            }
            if run["state"] == "completed":
                if [row["event_type"] for row in events] != [
                    "command.received",
                    "run.started",
                    "artifact.version_created",
                    "handoff.ready",
                    "run.completed",
                ]:
                    raise IntegrityConflict("completed inspect lacks exact terminal event profile")
                if any(value is None for value in (artifact, publication, sink, gate)):
                    raise IntegrityConflict("completed inspect lacks a terminal artifact/sink/gate record")
                if len(lineage_rows) != 1 or len(event_deliveries) != 5:
                    raise IntegrityConflict("completed inspect lacks exact lineage/delivery cardinality")
                sink_delivery = [
                    row
                    for row in event_deliveries
                    if row["event_delivery_id"] == sink["event_delivery_id"]
                ]
                if (
                    len(sink_delivery) != 1
                    or sink_delivery[0]["subscriber_id"] != "bootstrap_sink"
                    or sink_delivery[0]["terminal_policy"] != "fixture_terminal"
                    or sink_delivery[0]["state"] != "accepted_terminal"
                ):
                    raise IntegrityConflict("completed inspect lacks accepted terminal sink delivery")
                if len(route_proposals) != 1 or len(actor_proposals) != 2:
                    raise IntegrityConflict("completed inspect lacks exact accepted proposal lineage")
            return result
        finally:
            connection.close()

    def integrity_results(self) -> Mapping[str, Any]:
        connection = self._connect(query_only=True)
        try:
            return {
                "foreign_key_check": [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")],
                "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            }
        finally:
            connection.close()
