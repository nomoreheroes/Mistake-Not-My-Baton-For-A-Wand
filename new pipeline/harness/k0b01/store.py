"""Forward-only schema-v4 store boundary for deterministic K0b-01 records."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import sqlite3
from typing import Any, Callable, Mapping

from harness.k0a01.store import MigrationError, _hash, _strict_text, _timestamp
from harness.k0a02.store import K0A01_MIGRATION_SHA256, K0A02_MIGRATION_SHA256
from harness.k0a03.store import K0A03_MIGRATION_SHA256, K0a03Store

from .budget import prove_reference_equivalence
from .compiler import COMPILER_ID, COMPILER_VERSION, compile_registry_bundle
from .contract import (
    PINNED_EVENT_PROFILE_SHA256,
    PINNED_PACKAGE_ID,
    PINNED_PACKAGE_SHA256,
    PINNED_PACKAGE_VERSION,
    PINNED_REFERENCE_CASES_SHA256,
    PINNED_RESOURCE_POLICY_SHA256,
    PINNED_ROUTING_PROFILE_SHA256,
    PINNED_SUBSCRIPTION_PROFILE_SHA256,
    canonical_json,
    load_contract_bundle,
    sha256_json,
)


K0B01_MIGRATION_SHA256 = (
    "7be712f1483c07e52cb34d75c6cd76e4bde5104b31f974faa1bc57e9f0f2c96a"
)
IMPLEMENTATION_AUTHORITY_SHA256 = (
    "cdb87a83b5bc91ca343a76103252183669dc5da6d03ab9222abb1b81b68fe4dc"
)


@dataclass(frozen=True)
class BackupReceipt:
    path: Path
    sha256: str
    source_schema_version: int
    integrity_check: str
    foreign_key_violations: int
    content_sha256: str
    table_counts: Mapping[str, int]


@dataclass(frozen=True)
class DataSnapshot:
    sha256: str
    table_counts: Mapping[str, int]


class K0b01Store(K0a03Store):
    """K0a schema plus immutable K0b-01 registry/compiler definitions."""

    SCHEMA_VERSION = 4
    MIGRATION_NAME = "0004_k0b01"

    def __init__(
        self,
        db_path: str | Path,
        *,
        backup_path: str | Path | None = None,
        migration_0001_path: str | Path | None = None,
        migration_0002_path: str | Path | None = None,
        migration_0003_path: str | Path | None = None,
        migration_0004_path: str | Path | None = None,
    ) -> None:
        super().__init__(
            db_path, migration_0001_path, migration_0002_path, migration_0003_path
        )
        self.backup_path = Path(backup_path) if backup_path is not None else None
        self.migration_0004_path = (
            Path(migration_0004_path)
            if migration_0004_path is not None
            else Path(__file__).resolve().parent.parent
            / "migrations"
            / "0004_k0b01.sql"
        )
        self.last_backup_receipt: BackupReceipt | None = None

    @staticmethod
    def _reject_forbidden_path(path: Path, label: str) -> Path:
        resolved = path.resolve(strict=False)
        normalized = "/" + resolved.as_posix().lower().strip("/") + "/"
        forbidden = ("/tests/fixtures/", "/projects/swarm/", "/research/old-swarm/")
        if any(fragment in normalized for fragment in forbidden):
            raise MigrationError(f"{label} is inside a forbidden root")
        return resolved

    @classmethod
    def _expected_k0b01_schema(cls, *scripts: str) -> str:
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
            raise MigrationError(
                "K0b-01 migrations cannot build the expected schema"
            ) from exc
        finally:
            connection.close()

    @staticmethod
    def _database_version(path: Path) -> int:
        if not path.exists():
            return 0
        connection = sqlite3.connect(str(path), isolation_level=None)
        try:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])
        finally:
            connection.close()

    @staticmethod
    def _snapshot_value(value: Any) -> Mapping[str, Any]:
        if value is None:
            return {"type": "null"}
        if isinstance(value, bytes):
            return {"type": "blob", "hex": value.hex()}
        if isinstance(value, str):
            return {"type": "text", "value": value}
        if isinstance(value, int) and not isinstance(value, bool):
            return {"type": "integer", "value": value}
        if isinstance(value, float):
            return {"type": "real", "hex": value.hex()}
        raise MigrationError(
            f"unsupported SQLite value in preservation snapshot: {type(value).__name__}"
        )

    @classmethod
    def _data_snapshot(
        cls,
        connection: sqlite3.Connection,
        table_names: tuple[str, ...] | None = None,
    ) -> DataSnapshot:
        names = table_names
        if names is None:
            names = tuple(
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                    "AND name <> 'schema_migrations' ORDER BY name"
                ).fetchall()
            )
        tables: list[Mapping[str, Any]] = []
        counts: dict[str, int] = {}
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [
                row[1] for row in connection.execute(f"PRAGMA table_info({quoted})")
            ]
            if not columns:
                raise MigrationError(f"preservation table is missing: {name}")
            rows = [
                [cls._snapshot_value(value) for value in row]
                for row in connection.execute(f"SELECT * FROM {quoted}").fetchall()
            ]
            rows.sort(key=canonical_json)
            counts[name] = len(rows)
            tables.append({"name": name, "columns": columns, "rows": rows})
        return DataSnapshot(sha256=sha256_json({"tables": tables}), table_counts=counts)

    def _create_verified_backup(self) -> BackupReceipt:
        if self.backup_path is None:
            raise MigrationError(
                "an explicit new backup path is required before schema-v4 migration"
            )
        source_path = self._reject_forbidden_path(self.db_path, "source database")
        backup_path = self._reject_forbidden_path(self.backup_path, "backup database")
        if source_path == backup_path:
            raise MigrationError("backup path must differ from source database")
        if not backup_path.parent.is_dir():
            raise MigrationError("backup parent must already exist")
        if backup_path.exists():
            raise MigrationError("backup path must be new")
        source = self._connect(query_only=True)
        destination = sqlite3.connect(str(backup_path), isolation_level=None)
        destination.row_factory = sqlite3.Row
        try:
            if int(source.execute("PRAGMA user_version").fetchone()[0]) != 3:
                raise MigrationError("backup source must be exact schema v3")
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise MigrationError("source integrity check failed before backup")
            if source.execute("PRAGMA foreign_key_check").fetchall():
                raise MigrationError("source foreign-key check failed before backup")
            source_snapshot = self._data_snapshot(source)
            source.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = destination.execute("PRAGMA foreign_key_check").fetchall()
            version = int(destination.execute("PRAGMA user_version").fetchone()[0])
            if integrity != "ok" or foreign_keys or version != 3:
                raise MigrationError("backup readback differs from exact schema v3")
            backup_snapshot = self._data_snapshot(
                destination, tuple(source_snapshot.table_counts)
            )
            if backup_snapshot != source_snapshot:
                raise MigrationError(
                    "backup content differs from the schema-v3 source snapshot"
                )
        finally:
            destination.close()
            source.close()
        receipt = BackupReceipt(
            path=backup_path,
            sha256=sha256(backup_path.read_bytes()).hexdigest(),
            source_schema_version=3,
            integrity_check="ok",
            foreign_key_violations=0,
            content_sha256=source_snapshot.sha256,
            table_counts=source_snapshot.table_counts,
        )
        self.last_backup_receipt = receipt
        return receipt

    def initialize(self, *, fault_hook: Callable[[str], None] | None = None) -> str:
        """Upgrade exact K0a schema v3 to v4 after a verified new-path backup."""

        self._reject_forbidden_path(self.db_path, "source database")
        if not self.db_path.parent.is_dir():
            raise MigrationError("database parent must already exist")
        migration_0001, hash_0001 = self._migration(
            self.migration_path, K0A01_MIGRATION_SHA256
        )
        migration_0002, hash_0002 = self._migration(
            self.migration_0002_path, K0A02_MIGRATION_SHA256
        )
        migration_0003, hash_0003 = self._migration(
            self.migration_0003_path, K0A03_MIGRATION_SHA256
        )
        migration_0004, hash_0004 = self._migration(
            self.migration_0004_path, K0B01_MIGRATION_SHA256
        )
        expected_v3 = self._expected_k0a03_schema(
            migration_0001, migration_0002, migration_0003
        )
        expected_v4 = self._expected_k0b01_schema(
            migration_0001, migration_0002, migration_0003, migration_0004
        )
        version = self._database_version(self.db_path)
        if version > self.SCHEMA_VERSION:
            raise MigrationError(f"unsupported schema version {version}")
        if version < 3:
            super().initialize()
            version = 3
        if version == 3:
            preflight = self._connect(query_only=True)
            try:
                records = preflight.execute(
                    "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
                ).fetchall()
                if [tuple(row) for row in records] != [
                    (1, "0001_k0a01", hash_0001),
                    (2, "0002_k0a02", hash_0002),
                    (3, "0003_k0a03", hash_0003),
                ]:
                    raise MigrationError(
                        "historical migration records differ before K0b-01"
                    )
                if self._schema_fingerprint_from(preflight) != expected_v3:
                    raise MigrationError("schema v3 differs from exact K0a migrations")
                if preflight.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise MigrationError("schema v3 integrity check failed")
                if preflight.execute("PRAGMA foreign_key_check").fetchall():
                    raise MigrationError("schema v3 foreign-key check failed")
                preflight_snapshot = self._data_snapshot(preflight)
            finally:
                preflight.close()
            if fault_hook is not None:
                fault_hook("before_backup")
            backup_receipt = self._create_verified_backup()
            if backup_receipt.content_sha256 != preflight_snapshot.sha256 or dict(
                backup_receipt.table_counts
            ) != dict(preflight_snapshot.table_counts):
                raise MigrationError(
                    "schema-v3 content changed between preflight and backup"
                )
            if fault_hook is not None:
                fault_hook("after_backup")
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 3:
                    raise MigrationError("schema version changed after backup")
                if self._schema_fingerprint_from(connection) != expected_v3:
                    raise MigrationError("schema changed after backup")
                live_snapshot = self._data_snapshot(
                    connection, tuple(backup_receipt.table_counts)
                )
                if live_snapshot.sha256 != backup_receipt.content_sha256:
                    raise MigrationError(
                        "schema-v3 content changed after the verified backup"
                    )
                for index, statement in enumerate(self._statements(migration_0004)):
                    connection.execute(statement)
                    if index == 0 and fault_hook is not None:
                        fault_hook("during_schema_application")
                if fault_hook is not None:
                    fault_hook("before_migration_row_insert")
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (4, '0004_k0b01', ?)",
                    (hash_0004,),
                )
                connection.execute("PRAGMA user_version = 4")
                if self._schema_fingerprint_from(connection) != expected_v4:
                    raise MigrationError("schema v4 differs from exact migration chain")
                migrated_snapshot = self._data_snapshot(
                    connection, tuple(backup_receipt.table_counts)
                )
                if migrated_snapshot.sha256 != backup_receipt.content_sha256:
                    raise MigrationError(
                        "schema-v4 migration changed historical content"
                    )
                if fault_hook is not None:
                    fault_hook("before_commit")
                connection.execute("COMMIT")
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()
        connection = self._connect()
        try:
            records = connection.execute(
                "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
            ).fetchall()
            if [tuple(row) for row in records] != [
                (1, "0001_k0a01", hash_0001),
                (2, "0002_k0a02", hash_0002),
                (3, "0003_k0a03", hash_0003),
                (4, "0004_k0b01", hash_0004),
            ]:
                raise MigrationError(
                    "schema-v4 migration identities are incomplete, stale, or extra"
                )
            if self._schema_fingerprint_from(connection) != expected_v4:
                raise MigrationError(
                    "live schema differs from exact v1+v2+v3+v4 migrations"
                )
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise MigrationError("schema-v4 integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise MigrationError("schema-v4 foreign-key check failed")
            if self.last_backup_receipt is not None:
                final_snapshot = self._data_snapshot(
                    connection, tuple(self.last_backup_receipt.table_counts)
                )
                if final_snapshot.sha256 != self.last_backup_receipt.content_sha256:
                    raise MigrationError(
                        "committed schema-v4 content differs from the verified backup"
                    )
        finally:
            connection.close()
        return hash_0004

    def record_compiled_bundle(
        self,
        *,
        binding_id: str,
        compiler_sha256: str,
        created_at: str,
    ) -> str:
        """Persist one exact compiled source bundle, returning its aggregate digest."""

        _strict_text("binding_id", binding_id)
        _hash("compiler_sha256", compiler_sha256)
        _timestamp("created_at", created_at)
        source = load_contract_bundle()
        compiled = compile_registry_bundle(source).document
        if compiler_sha256 != compiled["compiler_hashes"]["registry_routing_sha256"]:
            raise MigrationError(
                "registry/routing compiler SHA-256 differs from loaded bytes"
            )
        references = prove_reference_equivalence(
            source.reference_cases, source.resource_policy
        )
        expected_binding = {
            "binding_id": binding_id,
            "profile": "Alpha0",
            "package_id": PINNED_PACKAGE_ID,
            "package_version": PINNED_PACKAGE_VERSION,
            "package_sha256": PINNED_PACKAGE_SHA256,
            "event_profile_sha256": PINNED_EVENT_PROFILE_SHA256,
            "subscription_profile_sha256": PINNED_SUBSCRIPTION_PROFILE_SHA256,
            "routing_profile_sha256": PINNED_ROUTING_PROFILE_SHA256,
            "resource_policy_sha256": PINNED_RESOURCE_POLICY_SHA256,
            "reference_cases_sha256": PINNED_REFERENCE_CASES_SHA256,
            "implementation_authority_sha256": IMPLEMENTATION_AUTHORITY_SHA256,
            "created_at": created_at,
        }
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM k0b_contract_profile_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
            if existing is not None:
                if dict(existing) != expected_binding:
                    raise MigrationError(
                        "compiled binding identity was reused with different bytes"
                    )
                stored = connection.execute(
                    "SELECT COUNT(*) AS count, MIN(aggregate_digest) AS minimum, MAX(aggregate_digest) AS maximum "
                    "FROM k0b_compiled_profile_records WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()
                if (
                    stored["count"] != 8
                    or stored["minimum"] != compiled["aggregate_digest"]
                    or stored["maximum"] != compiled["aggregate_digest"]
                ):
                    raise MigrationError(
                        "stored compiled binding is incomplete or conflicting"
                    )
                connection.execute("COMMIT")
                return compiled["aggregate_digest"]
            connection.execute(
                "INSERT INTO k0b_contract_profile_bindings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(expected_binding.values()),
            )
            source_hashes_json = canonical_json(compiled["source_hashes"])
            for family, output in compiled["outputs"].items():
                connection.execute(
                    "INSERT INTO k0b_compiled_profile_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{binding_id}:{family}",
                        binding_id,
                        family,
                        COMPILER_ID,
                        COMPILER_VERSION,
                        compiler_sha256,
                        canonical_json(compiled["compiler_hashes"]),
                        source_hashes_json,
                        canonical_json(output),
                        compiled["output_hashes"][family],
                        compiled["aggregate_digest"],
                        created_at,
                    ),
                )
            for event in source.event_profile["events"]:
                connection.execute(
                    "INSERT INTO k0b_event_type_definitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding_id,
                        event["event_type"],
                        event["event_version"],
                        event["payload_schema_id"],
                        event["payload_schema_version"],
                        event["payload_schema_sha256"],
                        event["producer_owner"],
                        event["route_ref"],
                        canonical_json(event["allowed_subscribers"]),
                        event["terminal_policy"],
                        canonical_json(event["fields_consumed"]),
                        event["activation_work_item"],
                        event["replay_semantics"],
                        event["idempotency_scope"],
                        event["terminal_disposition"],
                    ),
                )
            for route in source.subscription_profile["routes"]:
                connection.execute(
                    "INSERT INTO k0b_subscription_terminal_definitions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding_id,
                        route["route_id"],
                        route["kind"],
                        canonical_json(route["subscribers"]),
                        route["terminal_policy"],
                        canonical_json(route["fields_read"]),
                        route["activation_work_item"],
                    ),
                )
            for route in source.routing_profile["routes"]:
                connection.execute(
                    "INSERT INTO k0b_s_route_definitions VALUES (?, ?, ?, ?)",
                    (
                        binding_id,
                        route["route_id"],
                        canonical_json(route),
                        sha256_json(route),
                    ),
                )
            for reference in references:
                case = next(
                    item
                    for item in source.reference_cases["cases"]
                    if item["case_id"] == reference.case_id
                )
                input_case = {
                    key: value
                    for key, value in case.items()
                    if key != "expected_reference_result"
                }
                result_json = canonical_json(reference.result)
                connection.execute(
                    "INSERT INTO k0b_resource_budget_compilations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{binding_id}:{reference.case_id}",
                        binding_id,
                        reference.case_id,
                        PINNED_RESOURCE_POLICY_SHA256,
                        PINNED_REFERENCE_CASES_SHA256,
                        sha256_json(input_case),
                        result_json,
                        sha256_json(reference.result),
                        "exact_field_value_match",
                        created_at,
                    ),
                )
            connection.execute("COMMIT")
        except sqlite3.DatabaseError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise MigrationError(str(exc)) from exc
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return compiled["aggregate_digest"]

    def k0b01_counts(self, binding_id: str) -> Mapping[str, int]:
        _strict_text("binding_id", binding_id)
        connection = self._connect(query_only=True)
        try:
            return {
                "bindings": connection.execute(
                    "SELECT COUNT(*) FROM k0b_contract_profile_bindings WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
                "compiled_outputs": connection.execute(
                    "SELECT COUNT(*) FROM k0b_compiled_profile_records WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
                "events": connection.execute(
                    "SELECT COUNT(*) FROM k0b_event_type_definitions WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
                "subscription_routes": connection.execute(
                    "SELECT COUNT(*) FROM k0b_subscription_terminal_definitions WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
                "s_routes": connection.execute(
                    "SELECT COUNT(*) FROM k0b_s_route_definitions WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
                "budget_cases": connection.execute(
                    "SELECT COUNT(*) FROM k0b_resource_budget_compilations WHERE binding_id = ?",
                    (binding_id,),
                ).fetchone()[0],
            }
        finally:
            connection.close()
