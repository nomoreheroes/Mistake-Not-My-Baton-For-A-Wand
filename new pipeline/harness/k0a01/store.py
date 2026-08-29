"""Minimal, fixture-only SQLite persistence for Pipeline v2 K0a-01.

This module deliberately stops at the persistence boundary.  It does not load
prompts, invoke models, materialize F00, expose a CLI, or publish checkpoints.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Iterator, Mapping, Sequence
import unicodedata


SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_OBJECT_RE = re.compile(r"[0-9a-f]{40}")
RETRIABLE_FAILURES = {
    "transient_unavailable_before_dispatch_ack",
    "timeout_before_accepted_response",
}
TERMINAL_RUN_STATES = {
    "completed",
    "blocked_input",
    "blocked_policy",
    "failed_invocation",
    "failed_validation",
    "failed_persistence",
}


class K0a01StoreError(RuntimeError):
    """Base class for a fail-closed K0a-01 persistence error."""


class MigrationError(K0a01StoreError):
    """The only K0a-01 migration is missing, changed, or incompatible."""


class StaleState(K0a01StoreError):
    """A CAS revision, current physical attempt, or state guard is stale."""


class IdempotencyConflict(K0a01StoreError):
    """An idempotency identity was reused for different semantic input."""


class IntegrityConflict(K0a01StoreError):
    """SQLite rejected an integrity or immutability invariant."""


class TextPolicyError(K0a01StoreError):
    """A BLOB, non-UTF-8 value, non-NFC artifact, or invalid JSON was supplied."""


@dataclass(frozen=True)
class InvocationSpec:
    invocation_id: str
    delivery_id: str
    attempt_number: int
    prompt_id: str
    prompt_version: str
    prompt_sha256: str
    contract_id: str
    contract_version: str
    contract_sha256: str
    result_schema_id: str
    result_schema_version: str
    result_schema_sha256: str
    registry_sha256: str
    provider: str
    model_profile: str
    model_identifier: str | None
    parameters: Mapping[str, Any]
    context_limit_tokens: int
    created_at: str


@dataclass(frozen=True)
class InvocationTelemetry:
    telemetry_id: str
    invocation_id: str
    provider: str
    model_profile: str
    model_identifier: str | None
    parameters: Mapping[str, Any]
    response_text: str
    response_sha256: str
    started_at: str
    completed_at: str
    duration_ms: int
    monotonic_started_ns: int
    monotonic_completed_ns: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    usage: Mapping[str, Any]
    finish_reason: str | None


@dataclass(frozen=True)
class ReplayPoint:
    replay_point_id: str
    invocation_id: str
    position: str
    sequence_number: int
    context_text: str
    context_sha256: str
    context_fragments: Sequence[Mapping[str, Any]]
    capabilities: Mapping[str, Any]
    environment: Mapping[str, Any]
    capture_completeness: str
    gap_code: str | None
    created_at: str


@dataclass(frozen=True)
class LineageRef:
    lineage_id: str
    parent_ref_kind: str
    relation: str
    parent_artifact_version_id: str | None = None
    parent_external_ref: str | None = None


@dataclass(frozen=True)
class ArtifactPublication:
    publication_transaction_id: str
    idempotency_key: str
    run_id: str
    expected_run_revision: int
    invocation_id: str
    artifact_id: str
    artifact_version_id: str
    content_text: str
    content_sha256: str
    media_type: str
    schema_id: str
    schema_version: str
    schema_sha256: str
    correlation_id: str
    caused_by_event_id: str
    version_created_event_id: str
    version_created_idempotency_key: str
    handoff_event_id: str
    handoff_idempotency_key: str
    event_schema_id: str
    event_schema_version: str
    event_schema_sha256: str
    lineage: Sequence[LineageRef]
    created_at: str


@dataclass(frozen=True)
class PublicationResult:
    publication_transaction_id: str
    artifact_version_id: str
    version_created_event_id: str
    handoff_event_id: str
    committed_run_revision: int
    idempotent_replay: bool


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8", errors="strict")).hexdigest()


def _strict_text(name: str, value: Any, *, nfc: bool = False) -> str:
    if not isinstance(value, str):
        raise TextPolicyError(f"{name} must be UTF-8 text; BLOB/bytes are forbidden")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise TextPolicyError(f"{name} is not strict UTF-8 text") from exc
    if nfc and unicodedata.normalize("NFC", value) != value:
        raise TextPolicyError(f"{name} must be NFC-normalized")
    return value


def _hash(name: str, value: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise IntegrityConflict(f"{name} must be lowercase SHA-256")
    return value


def _git_object(name: str, value: str) -> str:
    if not isinstance(value, str) or GIT_OBJECT_RE.fullmatch(value) is None:
        raise IntegrityConflict(f"{name} must be a lowercase 40-hex Git object ID")
    return value


def _timestamp(name: str, value: str) -> str:
    _strict_text(name, value)
    if not value.endswith("Z"):
        raise IntegrityConflict(f"{name} must be an explicit UTC RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise IntegrityConflict(f"{name} is not an RFC3339 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise IntegrityConflict(f"{name} must be UTC")
    return value


def _parsed_timestamp(name: str, value: str) -> datetime:
    _timestamp(name, value)
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _normalize_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise TextPolicyError("non-finite JSON number is forbidden")
        return value
    if isinstance(value, str):
        return _strict_text("JSON string", value)
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TextPolicyError("JSON mapping keys must be strings")
            normalized[_strict_text("JSON key", key)] = _normalize_json(item)
        return normalized
    raise TextPolicyError(f"value of type {type(value).__name__} is outside the JSON data model")


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            _normalize_json(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise TextPolicyError("value is not canonical JSON-compatible data") from exc


def _context_fragments(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)) or not value:
        raise IntegrityConflict("rendered context must contain at least one exact fragment")
    expected_keys = {"ordinal", "role", "content_text", "content_sha256"}
    allowed_roles = {"system", "developer", "user", "assistant", "tool"}
    result: list[dict[str, Any]] = []
    for ordinal, fragment in enumerate(value):
        if not isinstance(fragment, Mapping) or set(fragment) != expected_keys:
            raise IntegrityConflict("each context fragment requires only ordinal/role/content_text/content_sha256")
        if fragment["ordinal"] != ordinal or fragment["role"] not in allowed_roles:
            raise IntegrityConflict("context fragment order or role is invalid")
        content = _strict_text("context fragment content", fragment["content_text"])
        if _sha256_text(content) != _hash("context fragment SHA-256", fragment["content_sha256"]):
            raise IntegrityConflict("context fragment SHA-256 does not match exact UTF-8 content")
        result.append(
            {
                "content_sha256": fragment["content_sha256"],
                "content_text": content,
                "ordinal": ordinal,
                "role": fragment["role"],
            }
        )
    return result


def _capability_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"policy_version", "model_channel", "filesystem_roots", "tools"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise IntegrityConflict("capability snapshot fields are incomplete or unexpected")
    normalized = _normalize_json(value)
    if (
        not isinstance(normalized["policy_version"], str)
        or not isinstance(normalized["model_channel"], str)
        or normalized["filesystem_roots"] != []
        or normalized["tools"] != []
    ):
        raise IntegrityConflict("F00 reasoning capability snapshot must be deny-all except its model channel")
    return normalized


def _environment_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "adapter_version",
        "architecture",
        "clock_binding",
        "config_sha256",
        "dependency_lock_sha256",
        "harness_version",
        "locale",
        "os",
        "random_seed",
        "timezone",
        "tool_registry_version",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise IntegrityConflict("environment snapshot fields are incomplete or unexpected")
    normalized = _normalize_json(value)
    for name in required - {"random_seed"}:
        if not isinstance(normalized[name], str) or not normalized[name]:
            raise IntegrityConflict(f"environment field {name} must be non-empty text")
    if normalized["random_seed"] is not None and not isinstance(normalized["random_seed"], int):
        raise IntegrityConflict("random_seed must be an integer or explicit null gap")
    _hash("dependency_lock_sha256", normalized["dependency_lock_sha256"])
    _hash("config_sha256", normalized["config_sha256"])
    return normalized


class K0a01Store:
    """Short-transaction persistence API for a disposable F00 SQLite file."""

    SCHEMA_VERSION = 1
    MIGRATION_NAME = "0001_k0a01"

    def __init__(self, db_path: str | Path, migration_path: str | Path | None = None):
        self.db_path = Path(db_path)
        self.migration_path = (
            Path(migration_path)
            if migration_path is not None
            else Path(__file__).resolve().parent.parent / "migrations" / "0001_k0a01.sql"
        )

    def _connect(self, *, query_only: bool = False) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA recursive_triggers = ON")
        if query_only:
            connection.execute("PRAGMA query_only = ON")
        else:
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _operation(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise IntegrityConflict(str(exc)) from exc
        except sqlite3.DatabaseError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise IntegrityConflict(str(exc)) from exc
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @staticmethod
    def _statements(script: str) -> Iterator[str]:
        buffer = ""
        for line in script.splitlines(keepends=True):
            buffer += line
            if sqlite3.complete_statement(buffer):
                statement = buffer.strip()
                buffer = ""
                if statement:
                    yield statement
        if buffer.strip():
            raise MigrationError("migration ends with an incomplete SQL statement")

    @staticmethod
    def _schema_fingerprint_from(connection: sqlite3.Connection) -> str:
        rows = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        payload = [dict(row) for row in rows]
        return _sha256_text(_canonical_json(payload))

    @classmethod
    def _expected_schema_fingerprint(cls, migration_text: str) -> str:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA recursive_triggers = ON")
            for statement in cls._statements(migration_text):
                connection.execute(statement)
            return cls._schema_fingerprint_from(connection)
        except sqlite3.DatabaseError as exc:
            raise MigrationError("migration cannot build the expected SQLite schema") from exc
        finally:
            connection.close()

    def initialize(self) -> str:
        """Apply or verify the sole forward migration and return its SHA-256."""

        if not self.db_path.parent.is_dir():
            raise MigrationError("database parent must already exist")
        migration_bytes = self.migration_path.read_bytes()
        if migration_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in migration_bytes:
            raise MigrationError("migration must be UTF-8 without BOM and LF-only")
        try:
            migration_text = migration_bytes.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise MigrationError("migration is not strict UTF-8") from exc
        migration_sha256 = sha256(migration_bytes).hexdigest()
        expected_schema_fingerprint = self._expected_schema_fingerprint(migration_text)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if user_version == 0:
                for statement in self._statements(migration_text):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (?, ?, ?)",
                    (self.SCHEMA_VERSION, self.MIGRATION_NAME, migration_sha256),
                )
                connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
            elif user_version == self.SCHEMA_VERSION:
                row = connection.execute(
                    "SELECT name, sha256 FROM schema_migrations WHERE version = ?",
                    (self.SCHEMA_VERSION,),
                ).fetchone()
                if row is None or row["name"] != self.MIGRATION_NAME or row["sha256"] != migration_sha256:
                    raise MigrationError("applied K0a-01 migration identity does not match committed bytes")
            else:
                raise MigrationError(f"unsupported schema version {user_version}")
            if self._schema_fingerprint_from(connection) != expected_schema_fingerprint:
                raise MigrationError("live SQLite schema does not match the committed migration")
            connection.execute("COMMIT")
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok" or foreign_keys:
                raise MigrationError("post-migration SQLite integrity check failed")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return migration_sha256

    def schema_fingerprint(self) -> str:
        connection = self._connect(query_only=True)
        try:
            return self._schema_fingerprint_from(connection)
        finally:
            connection.close()

    def create_run(
        self,
        *,
        run_id: str,
        pipeline_commit: str,
        fixture_commit: str,
        fixture_tree: str,
        created_at: str,
    ) -> None:
        _strict_text("run_id", run_id)
        _git_object("pipeline_commit", pipeline_commit)
        _git_object("fixture_commit", fixture_commit)
        _git_object("fixture_tree", fixture_tree)
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, profile, pipeline_commit, fixture_commit, fixture_tree, state, state_revision, created_at) "
                "VALUES (?, 'F00', ?, ?, ?, 'created', 0, ?)",
                (run_id, pipeline_commit, fixture_commit, fixture_tree, created_at),
            )
            connection.execute(
                "INSERT INTO run_state_transitions(transition_id, run_id, from_state, to_state, from_revision, to_revision, occurred_at) "
                "VALUES (?, ?, NULL, 'created', NULL, 0, ?)",
                (f"{run_id}:state:0", run_id, created_at),
            )

    def transition_run(
        self,
        *,
        run_id: str,
        expected_state: str,
        expected_revision: int,
        new_state: str,
        transition_id: str,
        occurred_at: str,
    ) -> int:
        _timestamp("occurred_at", occurred_at)
        allowed = expected_state == "created" and new_state == "running"
        allowed = allowed or (
            expected_state == "running" and new_state in TERMINAL_RUN_STATES - {"completed"}
        )
        if new_state == "completed":
            raise IntegrityConflict("K0a-01 cannot bypass the K0a-02 sink/readback completion gate")
        if not allowed:
            raise StaleState(f"forbidden run transition {expected_state} -> {new_state}")
        with self._operation() as connection:
            cursor = connection.execute(
                "UPDATE runs SET state = ?, state_revision = state_revision + 1 "
                "WHERE run_id = ? AND state = ? AND state_revision = ?",
                (new_state, run_id, expected_state, expected_revision),
            )
            if cursor.rowcount != 1:
                raise StaleState("run state or revision changed")
            new_revision = expected_revision + 1
            connection.execute(
                "INSERT INTO run_state_transitions(transition_id, run_id, from_state, to_state, from_revision, to_revision, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (transition_id, run_id, expected_state, new_state, expected_revision, new_revision, occurred_at),
            )
            return new_revision

    def append_control_event(
        self,
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
        idempotency_key: str,
        created_at: str,
    ) -> None:
        if event_type not in {"command.received", "run.started"}:
            raise IntegrityConflict("K0a-01 control append accepts only command.received or run.started")
        if event_type == "command.received" and caused_by_event_id is not None:
            raise IntegrityConflict("command.received cannot have a causal event")
        if event_type == "run.started" and caused_by_event_id is None:
            raise IntegrityConflict("run.started must be caused by command.received")
        payload_json = _canonical_json(payload)
        _hash("schema_sha256", schema_sha256)
        _timestamp("created_at", created_at)
        if event_type == "command.received":
            subscriber, policy, state = "s0_control_delivery", "control_delivery", "pending"
            fields = ["run_id", "profile", "command"]
        else:
            subscriber, policy, state = "bootstrap_readback", "observational_terminal", "observed_terminal"
            fields = ["run_id", "state"]
        with self._operation() as connection:
            connection.execute(
                "INSERT INTO events(event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, "
                "caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, idempotency_key, created_at) "
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
                    idempotency_key,
                    created_at,
                ),
            )
            connection.execute(
                "INSERT INTO event_deliveries(event_delivery_id, event_id, subscriber_id, terminal_policy, state, fields_read_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"{event_id}:delivery:0", event_id, subscriber, policy, state, _canonical_json(fields), created_at),
            )

    def create_delivery(
        self,
        *,
        delivery_id: str,
        run_id: str,
        delivery_key: str,
        role: str,
        triggering_event_id: str,
        created_at: str,
    ) -> None:
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            run = connection.execute("SELECT state FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            event = connection.execute(
                "SELECT run_id FROM events WHERE event_id = ?", (triggering_event_id,)
            ).fetchone()
            if run is None or run["state"] != "running":
                raise StaleState("delivery requires a running F00 run")
            if event is None or event["run_id"] != run_id:
                raise IntegrityConflict("triggering event does not belong to the run")
            connection.execute(
                "INSERT INTO deliveries(delivery_id, run_id, delivery_key, role, triggering_event_id, state, current_physical_invocation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'preflight_passed', NULL, ?)",
                (delivery_id, run_id, delivery_key, role, triggering_event_id, created_at),
            )

    def create_invocation(self, spec: InvocationSpec) -> None:
        if spec.attempt_number not in (1, 2):
            raise IntegrityConflict("only physical attempts 1 and 2 exist in F00")
        for name in (
            "prompt_sha256",
            "contract_sha256",
            "result_schema_sha256",
            "registry_sha256",
        ):
            _hash(name, getattr(spec, name))
        _timestamp("created_at", spec.created_at)
        if not isinstance(spec.context_limit_tokens, int) or spec.context_limit_tokens <= 0:
            raise IntegrityConflict("context_limit_tokens must be a positive integer")
        parameters_json = _canonical_json(spec.parameters)
        with self._operation() as connection:
            delivery = connection.execute(
                "SELECT run_id, current_physical_invocation_id FROM deliveries WHERE delivery_id = ?",
                (spec.delivery_id,),
            ).fetchone()
            if delivery is None:
                raise IntegrityConflict("unknown delivery")
            current_id = delivery["current_physical_invocation_id"]
            if spec.attempt_number == 1:
                if current_id is not None:
                    raise StaleState("delivery already has a physical invocation")
            else:
                if current_id is None:
                    raise StaleState("attempt 2 requires a current failed attempt 1")
                prior = connection.execute(
                    "SELECT * FROM physical_invocations WHERE invocation_id = ?",
                    (current_id,),
                ).fetchone()
                if (
                    prior is None
                    or prior["attempt_number"] != 1
                    or prior["state"] != "failed_invocation"
                    or prior["failure_code"] not in RETRIABLE_FAILURES
                    or prior["response_accepted"] != 0
                ):
                    raise StaleState("attempt 2 is allowed only after a named pre-acceptance transient failure")
                immutable_pins = (
                    "prompt_id",
                    "prompt_version",
                    "prompt_sha256",
                    "contract_id",
                    "contract_version",
                    "contract_sha256",
                    "result_schema_id",
                    "result_schema_version",
                    "result_schema_sha256",
                    "registry_sha256",
                    "provider",
                    "model_profile",
                    "model_identifier",
                    "parameters_json",
                    "context_limit_tokens",
                )
                proposed = {
                    **spec.__dict__,
                    "parameters_json": parameters_json,
                }
                if any(prior[name] != proposed[name] for name in immutable_pins):
                    raise StaleState("attempt 2 must reuse byte-identical invocation pins")
                connection.execute(
                    "UPDATE physical_invocations SET fenced = 1 WHERE invocation_id = ?",
                    (current_id,),
                )
            connection.execute(
                "INSERT INTO physical_invocations(invocation_id, delivery_id, run_id, attempt_number, state, prompt_id, prompt_version, prompt_sha256, "
                "contract_id, contract_version, contract_sha256, result_schema_id, result_schema_version, result_schema_sha256, "
                "registry_sha256, provider, model_profile, model_identifier, parameters_json, context_limit_tokens, response_accepted, fenced, failure_code, created_at) "
                "VALUES (?, ?, ?, ?, 'prepared', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, ?)",
                (
                    spec.invocation_id,
                    spec.delivery_id,
                    delivery["run_id"],
                    spec.attempt_number,
                    spec.prompt_id,
                    spec.prompt_version,
                    spec.prompt_sha256,
                    spec.contract_id,
                    spec.contract_version,
                    spec.contract_sha256,
                    spec.result_schema_id,
                    spec.result_schema_version,
                    spec.result_schema_sha256,
                    spec.registry_sha256,
                    spec.provider,
                    spec.model_profile,
                    spec.model_identifier,
                    parameters_json,
                    spec.context_limit_tokens,
                    spec.created_at,
                ),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) "
                "VALUES (?, ?, NULL, 'prepared', ?)",
                (f"{spec.invocation_id}:state:prepared", spec.invocation_id, spec.created_at),
            )
            connection.execute(
                "UPDATE deliveries SET current_physical_invocation_id = ?, state = 'evaluating' WHERE delivery_id = ?",
                (spec.invocation_id, spec.delivery_id),
            )

    @staticmethod
    def _require_current(connection: sqlite3.Connection, invocation_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT i.*, d.role, d.current_physical_invocation_id "
            "FROM physical_invocations i JOIN deliveries d ON d.delivery_id = i.delivery_id "
            "WHERE i.invocation_id = ?",
            (invocation_id,),
        ).fetchone()
        if row is None:
            raise IntegrityConflict("unknown physical invocation")
        if row["current_physical_invocation_id"] != invocation_id or row["fenced"] != 0:
            raise StaleState("physical invocation is late, superseded, or fenced")
        return row

    def transition_invocation(
        self,
        *,
        invocation_id: str,
        expected_state: str,
        new_state: str,
        transition_id: str,
        occurred_at: str,
    ) -> None:
        allowed = {
            ("replay_before_committed", "dispatched"),
            ("response_captured", "validated"),
        }
        if (expected_state, new_state) not in allowed:
            raise StaleState("transition is outside the K0a-01 persistence boundary")
        _timestamp("occurred_at", occurred_at)
        with self._operation() as connection:
            row = self._require_current(connection, invocation_id)
            if row["state"] != expected_state:
                raise StaleState("physical invocation state changed")
            connection.execute(
                "UPDATE physical_invocations SET state = ? WHERE invocation_id = ?",
                (new_state, invocation_id),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (transition_id, invocation_id, expected_state, new_state, occurred_at),
            )

    def record_invocation_failure(
        self,
        *,
        invocation_id: str,
        failure_code: str,
        transition_id: str,
        occurred_at: str,
    ) -> None:
        if failure_code not in RETRIABLE_FAILURES | {"non_retriable_provider_failure"}:
            raise IntegrityConflict("unknown physical invocation failure code")
        _timestamp("occurred_at", occurred_at)
        with self._operation() as connection:
            row = self._require_current(connection, invocation_id)
            if row["state"] not in {"replay_before_committed", "dispatched"} or row["response_accepted"]:
                raise StaleState("only an invocation without an accepted response can fail this way")
            connection.execute(
                "UPDATE physical_invocations SET state = 'failed_invocation', failure_code = ? WHERE invocation_id = ?",
                (failure_code, invocation_id),
            )
            connection.execute(
                "UPDATE deliveries SET state = ? WHERE delivery_id = ?",
                ("retry_pending" if failure_code in RETRIABLE_FAILURES else "failed_invocation", row["delivery_id"]),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) "
                "VALUES (?, ?, ?, 'failed_invocation', ?)",
                (transition_id, invocation_id, row["state"], occurred_at),
            )

    def record_telemetry(self, telemetry: InvocationTelemetry) -> None:
        _strict_text("response_text", telemetry.response_text)
        if _sha256_text(telemetry.response_text) != _hash("response_sha256", telemetry.response_sha256):
            raise IntegrityConflict("response SHA-256 does not match exact UTF-8 response text")
        started_at = _parsed_timestamp("started_at", telemetry.started_at)
        completed_at = _parsed_timestamp("completed_at", telemetry.completed_at)
        if completed_at < started_at:
            raise IntegrityConflict("telemetry completion cannot precede start")
        if (
            telemetry.monotonic_started_ns < 0
            or telemetry.monotonic_completed_ns < telemetry.monotonic_started_ns
            or telemetry.duration_ms
            != (telemetry.monotonic_completed_ns - telemetry.monotonic_started_ns) // 1_000_000
        ):
            raise IntegrityConflict("duration must match ordered monotonic-time bindings")
        if (
            any(
                not isinstance(value, int) or value < 0
                for value in (telemetry.input_tokens, telemetry.output_tokens, telemetry.total_tokens)
            )
            or telemetry.total_tokens != telemetry.input_tokens + telemetry.output_tokens
        ):
            raise IntegrityConflict("token usage fields must be present, non-negative, and additive")
        parameters_json = _canonical_json(telemetry.parameters)
        usage_json = _canonical_json(telemetry.usage)
        usage = json.loads(usage_json)
        if (
            not isinstance(usage, dict)
            or usage.get("input_tokens") != telemetry.input_tokens
            or usage.get("output_tokens") != telemetry.output_tokens
            or usage.get("total_tokens") != telemetry.total_tokens
        ):
            raise IntegrityConflict("exact usage receipt does not match typed telemetry counts")
        with self._operation() as connection:
            row = self._require_current(connection, telemetry.invocation_id)
            if row["state"] != "dispatched":
                raise StaleState("telemetry requires a dispatched current invocation")
            if (
                row["provider"] != telemetry.provider
                or row["model_profile"] != telemetry.model_profile
                or row["model_identifier"] != telemetry.model_identifier
                or row["parameters_json"] != parameters_json
            ):
                raise StaleState("telemetry model pins differ from the prepared invocation")
            connection.execute(
                "INSERT INTO invocation_telemetry(telemetry_id, invocation_id, provider, model_profile, model_identifier, parameters_json, "
                "response_text, response_sha256, started_at, completed_at, duration_ms, monotonic_started_ns, monotonic_completed_ns, "
                "input_tokens, output_tokens, total_tokens, usage_json, finish_reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    telemetry.telemetry_id,
                    telemetry.invocation_id,
                    telemetry.provider,
                    telemetry.model_profile,
                    telemetry.model_identifier,
                    parameters_json,
                    telemetry.response_text,
                    telemetry.response_sha256,
                    telemetry.started_at,
                    telemetry.completed_at,
                    telemetry.duration_ms,
                    telemetry.monotonic_started_ns,
                    telemetry.monotonic_completed_ns,
                    telemetry.input_tokens,
                    telemetry.output_tokens,
                    telemetry.total_tokens,
                    usage_json,
                    telemetry.finish_reason,
                ),
            )
            connection.execute(
                "UPDATE physical_invocations SET state = 'response_captured', response_accepted = 1 WHERE invocation_id = ?",
                (telemetry.invocation_id,),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) "
                "VALUES (?, ?, 'dispatched', 'response_captured', ?)",
                (f"{telemetry.telemetry_id}:state", telemetry.invocation_id, telemetry.completed_at),
            )

    def record_replay_point(self, point: ReplayPoint) -> str:
        if point.position not in {"before", "after"}:
            raise IntegrityConflict("replay position must be before or after")
        _strict_text("context_text", point.context_text)
        fragments = _context_fragments(point.context_fragments)
        fragments_json = _canonical_json(fragments)
        if point.context_text != fragments_json:
            raise IntegrityConflict("context_text must be the exact canonical ordered role/message snapshot")
        if _sha256_text(point.context_text) != _hash("context_sha256", point.context_sha256):
            raise IntegrityConflict("context SHA-256 does not match exact rendered context text")
        if point.capture_completeness not in {"complete_harness_visible", "typed_gap"}:
            raise IntegrityConflict("unknown capture completeness")
        if (point.capture_completeness == "typed_gap") != (point.gap_code is not None):
            raise IntegrityConflict("typed replay gaps must be explicit and complete captures must not invent one")
        _timestamp("created_at", point.created_at)
        capabilities = _capability_snapshot(point.capabilities)
        environment = _environment_snapshot(point.environment)
        capabilities_json = _canonical_json(capabilities)
        environment_json = _canonical_json(environment)

        with self._operation() as connection:
            invocation = self._require_current(connection, point.invocation_id)
            run = connection.execute("SELECT * FROM runs WHERE run_id = ?", (invocation["run_id"],)).fetchone()
            if run is None:
                raise IntegrityConflict("invocation run is missing")
            expected_state = "prepared" if point.position == "before" else "validated"
            next_state = "replay_before_committed" if point.position == "before" else "replay_after_committed"
            if invocation["state"] != expected_state:
                raise StaleState(f"{point.position} replay point requires invocation state {expected_state}")
            if capabilities["model_channel"] != invocation["provider"]:
                raise StaleState("replay capability model channel differs from the invocation provider pin")

            equality_fields = (
                "context_text",
                "context_sha256",
                "context_fragments_json",
                "capabilities_json",
                "environment_json",
                "capture_completeness",
                "gap_code",
            )
            candidate = {
                "context_text": point.context_text,
                "context_sha256": point.context_sha256,
                "context_fragments_json": fragments_json,
                "capabilities_json": capabilities_json,
                "environment_json": environment_json,
                "capture_completeness": point.capture_completeness,
                "gap_code": point.gap_code,
            }
            baseline = None
            if point.position == "after":
                baseline = connection.execute(
                    "SELECT * FROM replay_points WHERE invocation_id = ? AND position = 'before'",
                    (point.invocation_id,),
                ).fetchone()
            elif invocation["attempt_number"] == 2:
                baseline = connection.execute(
                    "SELECT replay.* FROM replay_points replay "
                    "JOIN physical_invocations prior ON prior.invocation_id = replay.invocation_id "
                    "WHERE prior.delivery_id = ? AND prior.attempt_number = 1 AND replay.position = 'before'",
                    (invocation["delivery_id"],),
                ).fetchone()
            if baseline is not None and any(baseline[name] != candidate[name] for name in equality_fields):
                raise StaleState("retry and before/after replay snapshots must be byte-identical")
            if (point.position == "after" or invocation["attempt_number"] == 2) and baseline is None:
                raise IntegrityConflict("required replay comparison baseline is missing")

            telemetry = None
            result_text = None
            result_sha256 = None
            telemetry_id = None
            if point.position == "after":
                telemetry = connection.execute(
                    "SELECT * FROM invocation_telemetry WHERE invocation_id = ?",
                    (point.invocation_id,),
                ).fetchone()
                if telemetry is None:
                    raise IntegrityConflict("after replay point requires exact invocation telemetry")
                result_text = telemetry["response_text"]
                result_sha256 = telemetry["response_sha256"]
                telemetry_id = telemetry["telemetry_id"]

            envelope = {
                "attempt_number": invocation["attempt_number"],
                "capabilities": json.loads(capabilities_json),
                "capture_completeness": point.capture_completeness,
                "context": {
                    "fragments": json.loads(fragments_json),
                    "sha256": point.context_sha256,
                    "text": point.context_text,
                },
                "contract": {
                    "id": invocation["contract_id"],
                    "sha256": invocation["contract_sha256"],
                    "version": invocation["contract_version"],
                },
                "delivery_id": invocation["delivery_id"],
                "environment": json.loads(environment_json),
                "fixture": {"commit": run["fixture_commit"], "tree": run["fixture_tree"]},
                "gap_code": point.gap_code,
                "invocation_id": point.invocation_id,
                "model": {
                    "context_limit_tokens": invocation["context_limit_tokens"],
                    "identifier": invocation["model_identifier"],
                    "parameters": json.loads(invocation["parameters_json"]),
                    "profile": invocation["model_profile"],
                    "provider": invocation["provider"],
                },
                "pipeline_commit": run["pipeline_commit"],
                "position": point.position,
                "prompt": {
                    "id": invocation["prompt_id"],
                    "sha256": invocation["prompt_sha256"],
                    "version": invocation["prompt_version"],
                },
                "registry_sha256": invocation["registry_sha256"],
                "replay_point_id": point.replay_point_id,
                "result": None if telemetry is None else {
                    "sha256": result_sha256,
                    "telemetry": {
                        "completed_at": telemetry["completed_at"],
                        "duration_ms": telemetry["duration_ms"],
                        "finish_reason": telemetry["finish_reason"],
                        "id": telemetry_id,
                        "monotonic_completed_ns": telemetry["monotonic_completed_ns"],
                        "monotonic_started_ns": telemetry["monotonic_started_ns"],
                        "started_at": telemetry["started_at"],
                        "usage": json.loads(telemetry["usage_json"]),
                    },
                    "text": result_text,
                },
                "result_schema": {
                    "id": invocation["result_schema_id"],
                    "sha256": invocation["result_schema_sha256"],
                    "version": invocation["result_schema_version"],
                },
                "run_id": invocation["run_id"],
                "sequence_number": point.sequence_number,
            }
            envelope_json = _canonical_json(envelope)
            envelope_sha256 = _sha256_text(envelope_json)
            connection.execute(
                "INSERT INTO replay_points(replay_point_id, run_id, delivery_id, invocation_id, attempt_number, position, sequence_number, "
                "pipeline_commit, fixture_commit, fixture_tree, prompt_id, prompt_version, prompt_sha256, contract_id, contract_version, contract_sha256, "
                "result_schema_id, result_schema_version, result_schema_sha256, registry_sha256, context_text, context_sha256, context_fragments_json, fragment_count, "
                "provider, model_profile, model_identifier, parameters_json, capabilities_json, environment_json, capture_completeness, gap_code, "
                "result_text, result_sha256, telemetry_id, envelope_json, envelope_sha256, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    point.replay_point_id,
                    invocation["run_id"],
                    invocation["delivery_id"],
                    point.invocation_id,
                    invocation["attempt_number"],
                    point.position,
                    point.sequence_number,
                    run["pipeline_commit"],
                    run["fixture_commit"],
                    run["fixture_tree"],
                    invocation["prompt_id"],
                    invocation["prompt_version"],
                    invocation["prompt_sha256"],
                    invocation["contract_id"],
                    invocation["contract_version"],
                    invocation["contract_sha256"],
                    invocation["result_schema_id"],
                    invocation["result_schema_version"],
                    invocation["result_schema_sha256"],
                    invocation["registry_sha256"],
                    point.context_text,
                    point.context_sha256,
                    fragments_json,
                    len(fragments),
                    invocation["provider"],
                    invocation["model_profile"],
                    invocation["model_identifier"],
                    invocation["parameters_json"],
                    capabilities_json,
                    environment_json,
                    point.capture_completeness,
                    point.gap_code,
                    result_text,
                    result_sha256,
                    telemetry_id,
                    envelope_json,
                    envelope_sha256,
                    point.created_at,
                ),
            )
            connection.executemany(
                "INSERT INTO replay_context_fragments(replay_point_id, ordinal, role, content_text, content_sha256) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        point.replay_point_id,
                        fragment["ordinal"],
                        fragment["role"],
                        fragment["content_text"],
                        fragment["content_sha256"],
                    )
                    for fragment in fragments
                ],
            )
            connection.execute(
                "UPDATE physical_invocations SET state = ? WHERE invocation_id = ?",
                (next_state, point.invocation_id),
            )
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (f"{point.replay_point_id}:state", point.invocation_id, expected_state, next_state, point.created_at),
            )
            return envelope_sha256

    def read_replay_envelope(self, replay_point_id: str) -> Mapping[str, Any]:
        connection = self._connect(query_only=True)
        try:
            row = connection.execute(
                "SELECT envelope_json, envelope_sha256 FROM replay_points WHERE replay_point_id = ?",
                (replay_point_id,),
            ).fetchone()
            if row is None:
                raise IntegrityConflict("unknown replay point")
            if _sha256_text(row["envelope_json"]) != row["envelope_sha256"]:
                raise IntegrityConflict("stored replay envelope hash mismatch")
            return json.loads(row["envelope_json"])
        finally:
            connection.close()

    def record_s0_route_validation(
        self,
        *,
        proposal_id: str,
        invocation_id: str,
        accepted: bool,
        created_at: str,
    ) -> None:
        _timestamp("created_at", created_at)
        with self._operation() as connection:
            invocation = self._require_current(connection, invocation_id)
            if invocation["role"] != "S0" or invocation["state"] != "replay_after_committed":
                raise StaleState("route persistence requires the current S0 after-replay boundary")
            telemetry = connection.execute(
                "SELECT response_text, response_sha256 FROM invocation_telemetry WHERE invocation_id = ?",
                (invocation_id,),
            ).fetchone()
            if telemetry is None:
                raise IntegrityConflict("route persistence requires exact raw response telemetry")
            raw_output_text = telemetry["response_text"]
            try:
                raw_value = json.loads(raw_output_text)
            except json.JSONDecodeError:
                raw_value = None
            declared_type = raw_value.get("type") if isinstance(raw_value, dict) else None
            allowed_types = {"s0_route_proposal", "semantic_blocker", "abstention"}
            raw_output_type = declared_type if declared_type in allowed_types else "malformed_or_forbidden"
            if accepted and raw_output_type != "s0_route_proposal":
                raise IntegrityConflict("only telemetry-declared s0_route_proposal can become validated_route_proposal")
            disposition = "accepted" if accepted else "rejected"
            persisted_type = "validated_route_proposal" if accepted else None
            terminal_state = None if accepted else "failed_validation"
            connection.execute(
                "INSERT INTO route_proposals(proposal_id, delivery_id, invocation_id, raw_output_type, raw_output_text, raw_output_sha256, "
                "validation_disposition, persisted_output_type, terminal_state, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal_id,
                    invocation["delivery_id"],
                    invocation_id,
                    raw_output_type,
                    raw_output_text,
                    telemetry["response_sha256"],
                    disposition,
                    persisted_type,
                    terminal_state,
                    created_at,
                ),
            )
            connection.execute(
                "UPDATE deliveries SET state = ? WHERE delivery_id = ?",
                ("result_validated" if accepted else "failed_validation", invocation["delivery_id"]),
            )

    @staticmethod
    def _publication_digest(publication: ArtifactPublication) -> str:
        payload = {
            "artifact_id": publication.artifact_id,
            "artifact_version_id": publication.artifact_version_id,
            "caused_by_event_id": publication.caused_by_event_id,
            "content_sha256": publication.content_sha256,
            "correlation_id": publication.correlation_id,
            "event_schema": [
                publication.event_schema_id,
                publication.event_schema_version,
                publication.event_schema_sha256,
            ],
            "expected_run_revision": publication.expected_run_revision,
            "handoff_event_id": publication.handoff_event_id,
            "handoff_idempotency_key": publication.handoff_idempotency_key,
            "invocation_id": publication.invocation_id,
            "lineage": [ref.__dict__ for ref in publication.lineage],
            "media_type": publication.media_type,
            "publication_transaction_id": publication.publication_transaction_id,
            "run_id": publication.run_id,
            "schema": [publication.schema_id, publication.schema_version, publication.schema_sha256],
            "version_created_event_id": publication.version_created_event_id,
            "version_created_idempotency_key": publication.version_created_idempotency_key,
        }
        return _sha256_text(_canonical_json(payload))

    def publish_artifact_version(
        self,
        publication: ArtifactPublication,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> PublicationResult:
        content_text = _strict_text("content_text", publication.content_text, nfc=True)
        content_sha256 = _hash("content_sha256", publication.content_sha256)
        if _sha256_text(content_text) != content_sha256:
            raise IntegrityConflict("artifact content SHA-256 does not match exact UTF-8 text")
        if publication.media_type not in {"text/plain", "application/json"}:
            raise TextPolicyError("F00 accepts only textual media types")
        if publication.media_type == "application/json":
            try:
                parsed = json.loads(content_text)
            except json.JSONDecodeError as exc:
                raise TextPolicyError("application/json artifact is invalid") from exc
            if _canonical_json(parsed) != content_text:
                raise TextPolicyError("application/json artifact must use canonical JSON text")
        _hash("schema_sha256", publication.schema_sha256)
        _hash("event_schema_sha256", publication.event_schema_sha256)
        _timestamp("created_at", publication.created_at)
        if not publication.lineage:
            raise IntegrityConflict("artifact publication must record at least one lineage edge")
        request_sha256 = self._publication_digest(publication)

        with self._operation() as connection:
            existing = connection.execute(
                "SELECT * FROM publication_transactions WHERE idempotency_key = ?",
                (publication.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["request_sha256"] != request_sha256:
                    raise IdempotencyConflict("publication idempotency identity was reused with different input")
                return PublicationResult(
                    existing["publication_transaction_id"],
                    existing["artifact_version_id"],
                    existing["version_created_event_id"],
                    existing["handoff_event_id"],
                    existing["committed_run_revision"],
                    True,
                )

            invocation = self._require_current(connection, publication.invocation_id)
            if invocation["run_id"] != publication.run_id or invocation["role"] != "fixture_worker":
                raise IntegrityConflict("only the current fixture worker invocation can publish this artifact")
            if invocation["state"] != "replay_after_committed" or invocation["response_accepted"] != 1:
                raise StaleState("publication requires an accepted current invocation with after replay committed")
            run = connection.execute("SELECT * FROM runs WHERE run_id = ?", (publication.run_id,)).fetchone()
            if (
                run is None
                or run["state"] != "running"
                or run["state_revision"] != publication.expected_run_revision
            ):
                raise StaleState("publication run state or revision is stale")
            cause = connection.execute(
                "SELECT run_id FROM events WHERE event_id = ?", (publication.caused_by_event_id,)
            ).fetchone()
            if cause is None or cause["run_id"] != publication.run_id:
                raise IntegrityConflict("publication causal event is missing or belongs to another run")

            connection.execute(
                "INSERT INTO artifacts(artifact_id, run_id, artifact_type, logical_owner, created_at) "
                "VALUES (?, ?, 'bootstrap.synthetic_result', 'fixture.bootstrap_worker', ?)",
                (publication.artifact_id, publication.run_id, publication.created_at),
            )
            connection.execute(
                "INSERT INTO artifact_versions(artifact_version_id, artifact_id, run_id, producing_invocation_id, media_type, encoding, "
                "schema_id, schema_version, schema_sha256, hash_profile_id, content_text, content_sha256, content_size_bytes, idempotency_key, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'utf-8', ?, ?, ?, 'sha256-utf8-v1', ?, ?, ?, ?, ?)",
                (
                    publication.artifact_version_id,
                    publication.artifact_id,
                    publication.run_id,
                    publication.invocation_id,
                    publication.media_type,
                    publication.schema_id,
                    publication.schema_version,
                    publication.schema_sha256,
                    content_text,
                    content_sha256,
                    len(content_text.encode("utf-8")),
                    f"{publication.idempotency_key}:artifact-version",
                    publication.created_at,
                ),
            )
            if fault_hook is not None:
                fault_hook("after_artifact_version")

            for lineage in publication.lineage:
                connection.execute(
                    "INSERT INTO artifact_version_lineage(lineage_id, run_id, child_artifact_version_id, parent_ref_kind, parent_artifact_version_id, parent_external_ref, relation) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        lineage.lineage_id,
                        publication.run_id,
                        publication.artifact_version_id,
                        lineage.parent_ref_kind,
                        lineage.parent_artifact_version_id,
                        lineage.parent_external_ref,
                        lineage.relation,
                    ),
                )

            version_payload = _canonical_json(
                {
                    "artifact_type": "bootstrap.synthetic_result",
                    "artifact_version_id": publication.artifact_version_id,
                    "content_sha256": content_sha256,
                }
            )
            handoff_payload = _canonical_json(
                {"artifact_version_id": publication.artifact_version_id, "profile": "F00"}
            )
            event_rows = (
                (
                    publication.version_created_event_id,
                    "artifact.version_created",
                    publication.caused_by_event_id,
                    version_payload,
                    publication.version_created_idempotency_key,
                    "bootstrap_readback",
                    "observational_terminal",
                    "observed_terminal",
                    ["artifact_version_id", "artifact_type", "content_sha256"],
                ),
                (
                    publication.handoff_event_id,
                    "handoff.ready",
                    publication.version_created_event_id,
                    handoff_payload,
                    publication.handoff_idempotency_key,
                    "bootstrap_sink",
                    "fixture_terminal",
                    "pending",
                    ["artifact_version_id", "profile"],
                ),
            )
            for (
                event_id,
                event_type,
                caused_by_event_id,
                payload_json,
                idempotency_key,
                subscriber_id,
                terminal_policy,
                delivery_state,
                fields_read,
            ) in event_rows:
                connection.execute(
                    "INSERT INTO events(event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, "
                    "caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, payload_sha256, idempotency_key, created_at) "
                    "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        publication.run_id,
                        event_type,
                        publication.invocation_id,
                        publication.artifact_version_id,
                        caused_by_event_id,
                        publication.correlation_id,
                        publication.event_schema_id,
                        publication.event_schema_version,
                        publication.event_schema_sha256,
                        payload_json,
                        _sha256_text(payload_json),
                        idempotency_key,
                        publication.created_at,
                    ),
                )
                connection.execute(
                    "INSERT INTO event_deliveries(event_delivery_id, event_id, subscriber_id, terminal_policy, state, fields_read_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{event_id}:delivery:0",
                        event_id,
                        subscriber_id,
                        terminal_policy,
                        delivery_state,
                        _canonical_json(fields_read),
                        publication.created_at,
                    ),
                )
            if fault_hook is not None:
                fault_hook("after_events")

            committed_revision = publication.expected_run_revision + 1
            connection.execute(
                "INSERT INTO publication_transactions(publication_transaction_id, run_id, invocation_id, idempotency_key, request_sha256, "
                "artifact_version_id, version_created_event_id, handoff_event_id, expected_run_revision, committed_run_revision, committed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    publication.publication_transaction_id,
                    publication.run_id,
                    publication.invocation_id,
                    publication.idempotency_key,
                    request_sha256,
                    publication.artifact_version_id,
                    publication.version_created_event_id,
                    publication.handoff_event_id,
                    publication.expected_run_revision,
                    committed_revision,
                    publication.created_at,
                ),
            )
            connection.execute(
                "UPDATE physical_invocations SET state = 'published' WHERE invocation_id = ?",
                (publication.invocation_id,),
            )
            connection.execute(
                "UPDATE deliveries SET state = 'published' WHERE delivery_id = ?",
                (invocation["delivery_id"],),
            )
            cursor = connection.execute(
                "UPDATE runs SET state_revision = ? WHERE run_id = ? AND state = 'running' AND state_revision = ?",
                (committed_revision, publication.run_id, publication.expected_run_revision),
            )
            if cursor.rowcount != 1:
                raise StaleState("publication lost its final run revision CAS")
            connection.execute(
                "INSERT INTO invocation_state_transitions(transition_id, invocation_id, from_state, to_state, occurred_at) "
                "VALUES (?, ?, 'replay_after_committed', 'published', ?)",
                (f"{publication.publication_transaction_id}:state", publication.invocation_id, publication.created_at),
            )
            if fault_hook is not None:
                fault_hook("before_commit")
            return PublicationResult(
                publication.publication_transaction_id,
                publication.artifact_version_id,
                publication.version_created_event_id,
                publication.handoff_event_id,
                committed_revision,
                False,
            )

    def publication_counts(self) -> Mapping[str, int]:
        connection = self._connect(query_only=True)
        try:
            return {
                "artifacts": connection.execute("SELECT count(*) FROM artifacts").fetchone()[0],
                "artifact_versions": connection.execute("SELECT count(*) FROM artifact_versions").fetchone()[0],
                "publication_events": connection.execute(
                    "SELECT count(*) FROM events WHERE event_type IN ('artifact.version_created', 'handoff.ready')"
                ).fetchone()[0],
                "event_deliveries": connection.execute(
                    "SELECT count(*) FROM event_deliveries ed JOIN events e ON e.event_id = ed.event_id "
                    "WHERE e.event_type IN ('artifact.version_created', 'handoff.ready')"
                ).fetchone()[0],
                "publications": connection.execute("SELECT count(*) FROM publication_transactions").fetchone()[0],
            }
        finally:
            connection.close()

    def _bounded_record(self, table: str, key_column: str, key: Any) -> Mapping[str, Any] | None:
        allowed = {
            ("schema_migrations", "version"),
            ("events", "event_id"),
            ("route_proposals", "proposal_id"),
        }
        if (table, key_column) not in allowed:
            raise IntegrityConflict("query is outside the K0a-01 bounded read allowlist")
        connection = self._connect(query_only=True)
        try:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ?", (key,)
            ).fetchone()
            return None if row is None else dict(row)
        finally:
            connection.close()

    def migration_record(self) -> Mapping[str, Any] | None:
        return self._bounded_record("schema_migrations", "version", self.SCHEMA_VERSION)

    def event_record(self, event_id: str) -> Mapping[str, Any] | None:
        return self._bounded_record("events", "event_id", event_id)

    def route_proposal_record(self, proposal_id: str) -> Mapping[str, Any] | None:
        return self._bounded_record("route_proposals", "proposal_id", proposal_id)
