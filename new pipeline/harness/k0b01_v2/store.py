from __future__ import annotations

import os
import platform
import re
import shutil
import sqlite3
import sys
import threading
import warnings
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .canonical import ContractError, no_reparse, require, sha256
from .contract import InputContext
from .digest import (
    HistoricalTable,
    content_digest,
    equal_historical,
    historical_manifest,
    identifier,
    schema_fingerprint,
    schema_rows,
)


class MigrationError(ContractError):
    pass


class InjectedFault(MigrationError):
    pass


@dataclass(frozen=True)
class ExpectedSchema:
    key: tuple[str, ...]
    v3_fingerprint: str
    v4_fingerprint: str
    historical_tables: tuple[HistoricalTable, ...]
    migration_rows: tuple[tuple[Any, ...], ...]
    v3_schema_rows: tuple[tuple[Any, ...], ...]
    v4_schema_rows: tuple[tuple[Any, ...], ...]


_SCHEMA_CACHE: dict[tuple[str, ...], ExpectedSchema] = {}
_CACHE_LOCK = threading.RLock()
_CACHE_BUILDS: dict[tuple[str, ...], int] = {}
_WRITER_LOCKS: dict[str, threading.Lock] = {}


def split_statements(text: str) -> tuple[str, ...]:
    statements = []
    pending = ""
    for line in text.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending.strip())
            pending = ""
    require(not pending.strip(), "migration:incomplete_SQL")
    return tuple(statements)


def migration_blocks(
    text: str, metadata: dict[str, Any]
) -> tuple[tuple[str, str], ...]:
    pieces = re.split(r"^-- k0b01: ([a-z]+\.[A-Za-z0-9_]+)\n", text, flags=re.MULTILINE)
    require(
        not pieces[0].strip() and len(pieces) > 1 and len(pieces) % 2 == 1,
        "migration:block_format",
    )
    blocks = tuple((pieces[i], pieces[i + 1].strip()) for i in range(1, len(pieces), 2))
    tables = metadata["tables"]
    expected = (
        ["create." + t for t in tables]
        + ["copy." + t for t in tables]
        + ["drop." + t for t in metadata["drop_order"]]
        + ["rename." + t for t in metadata["rename_order"]]
        + ["object." + o["name"] for o in metadata["owned_recreated_catalog"]]
    )
    require(
        [name for name, _ in blocks] == expected
        and len(expected) == len(set(expected)),
        "migration:ordered_catalog",
    )
    require(
        len(tables) == 4
        and metadata["rename_order"] == tables
        and metadata["drop_order"] == list(reversed(tables)),
        "migration:closure_order",
    )
    for _, sql in blocks:
        require(
            len(split_statements(sql + "\n")) == 1, "migration:one_statement_per_block"
        )
    return blocks


def assert_platform(metadata: dict[str, Any]) -> None:
    supported = metadata["platform"]
    require(
        sys.platform == "win32"
        and platform.machine().upper() == supported["architecture"]
        and platform.python_version() == supported["python"]
        and platform.python_implementation() == "CPython"
        and sqlite3.sqlite_version == supported["sqlite"],
        "migration:unsupported_platform",
    )
    version = sys.getwindowsversion()
    require(
        f"{version.major}.{version.minor}.{version.build}" == supported["version"]
        and version.product_type in (2, 3),
        "migration:unsupported_Windows",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        require(
            sqlite3.version == supported["python_sqlite_module"],
            "migration:unsupported_sqlite_module",
        )


def configure(connection: sqlite3.Connection) -> None:
    require(not connection.in_transaction, "migration:active_transaction")
    for name, value, expected in (
        ("busy_timeout", "5000", 5000),
        ("recursive_triggers", "ON", 1),
        ("legacy_alter_table", "OFF", 0),
        ("journal_mode", "WAL", "wal"),
        ("synchronous", "FULL", 2),
    ):
        connection.execute("PRAGMA " + name + "=" + value)
        require(
            connection.execute("PRAGMA " + name).fetchone()[0] == expected,
            "migration:setting:" + name,
        )
    connection.execute("PRAGMA temp_store=MEMORY")
    require(
        connection.execute("PRAGMA temp_store").fetchone()[0] == 2,
        "migration:temp_store",
    )


def integrity(connection: sqlite3.Connection) -> None:
    require(
        connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
        "migration:integrity_check",
    )
    require(
        connection.execute("PRAGMA foreign_key_check").fetchall() == [],
        "migration:foreign_key_check",
    )


def rename_validation_window(connection: sqlite3.Connection, active: bool) -> None:
    # SQLite 3.45.3 parses untouched external triggers during ALTER RENAME.
    # Final-name staging deliberately has a transient missing-parent interval.
    # No direct sqlite_schema writes: only the exact authorized renames run here.
    connection.execute("PRAGMA writable_schema=" + ("ON" if active else "OFF"))
    require(
        connection.execute("PRAGMA writable_schema").fetchone()[0] == int(active),
        "migration:rename_validation_window",
    )


def migration_rows(connection: sqlite3.Connection) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        connection.execute(
            "SELECT version,name,sha256 FROM schema_migrations ORDER BY version"
        )
    )


def readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        path.as_uri() + "?mode=ro", uri=True, isolation_level=None
    )
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA temp_store=MEMORY")
    return connection


class RuntimeRoot:
    def __init__(self, actual: Path, approved: Path) -> None:
        require(
            actual.is_absolute() and approved.is_absolute() and actual == approved,
            "root:identity_mismatch",
        )
        no_reparse(actual)
        require(
            actual.is_dir() and actual.resolve() == approved, "root:verified_directory"
        )
        self.path = approved
        info = actual.stat()
        self.identity = (info.st_dev, info.st_ino)

    def check_identity(self) -> None:
        no_reparse(self.path)
        info = self.path.stat()
        require((info.st_dev, info.st_ino) == self.identity, "root:replaced_identity")

    def file(self, path: Path, *, must_exist: bool) -> Path:
        self.check_identity()
        require(
            path.is_absolute() and path != self.path and path.is_relative_to(self.path),
            "root:outside_or_equal",
        )
        no_reparse(path.parent)
        require(
            path.parent.resolve().is_relative_to(self.path) and path.parent.is_dir(),
            "root:parent_escape",
        )
        if must_exist:
            no_reparse(path)
            require(
                path.is_file() and path.resolve().is_relative_to(self.path),
                "root:source_identity",
            )
        else:
            require(not os.path.lexists(path), "root:existing_destination")
        return path


def expected_schema(
    context: InputContext, blocks: tuple[tuple[str, str], ...]
) -> ExpectedSchema:
    metadata = context.package["migration"]
    paths = [p["path"] for p in metadata["historical_migrations"]] + [metadata["path"]]
    raws = [context.raw(p) for p in paths]
    hashes = tuple(sha256(raw) for raw in raws)
    require(
        hashes[-1] == metadata["sha256"]
        and all(
            hashes[i] == metadata["historical_migrations"][i]["sha256"]
            for i in range(3)
        ),
        "migration:source_hash_chain",
    )
    key = (sqlite3.sqlite_version, *hashes)
    with _CACHE_LOCK:
        if key in _SCHEMA_CACHE:
            return _SCHEMA_CACHE[key]
        require(len(_SCHEMA_CACHE) < 8, "migration:schema_cache_capacity")
        connection = sqlite3.connect(":memory:", isolation_level=None)
        try:
            rows = []
            for version in range(1, 4):
                for sql in split_statements(raws[version - 1].decode("utf-8")):
                    connection.execute(sql)
                row = (version, Path(paths[version - 1]).stem, hashes[version - 1])
                connection.execute(
                    "INSERT INTO schema_migrations(version,name,sha256) VALUES (?,?,?)",
                    row,
                )
                rows.append(row)
            v3 = schema_fingerprint(connection)
            manifest = historical_manifest(connection)
            rows3 = schema_rows(connection)
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("BEGIN IMMEDIATE")
            renaming = False
            for name, sql in blocks:
                if name.startswith("rename.") and not renaming:
                    rename_validation_window(connection, True)
                    renaming = True
                elif name.startswith("object.") and renaming:
                    rename_validation_window(connection, False)
                    renaming = False
                connection.execute(sql)
            require(not renaming, "migration:expected_schema_validation_restored")
            connection.execute("COMMIT")
            v4 = schema_fingerprint(connection)
            rows4 = schema_rows(connection)
            rows.append((4, metadata["logical_identity"], hashes[-1]))
            value = ExpectedSchema(key, v3, v4, manifest, tuple(rows), rows3, rows4)
        finally:
            connection.close()
        _SCHEMA_CACHE[key] = value
        _CACHE_BUILDS[key] = _CACHE_BUILDS.get(key, 0) + 1
        return value


def payload_byte_summaries(
    connection: sqlite3.Connection, table_names: dict[str, str] | None = None
) -> dict[str, Any]:
    result = {}
    for table, pk, column in (
        ("events", "event_id", "payload_json"),
        ("event_deliveries", "event_delivery_id", "fields_read_json"),
    ):
        actual = (table_names or {}).get(table, table)
        query = (
            "SELECT "
            + identifier(pk)
            + ",length(CAST("
            + identifier(column)
            + " AS BLOB)),hex(CAST("
            + identifier(column)
            + " AS BLOB)) FROM "
            + identifier(actual)
            + " ORDER BY CAST("
            + identifier(pk)
            + " AS BLOB)"
        )
        cursor = connection.execute(query)
        per_row = {}
        while batch := cursor.fetchmany(512):
            for key, length, hex_bytes in batch:
                require(key not in per_row, "migration:duplicate_byte_summary_PK")
                per_row[key] = {
                    "bytes": length,
                    "SQL_HEX_SHA256": sha256(hex_bytes.encode("ascii")),
                }
        result[table] = per_row
    return result


def compare_copy_bytes(connection: sqlite3.Connection, table: str) -> None:
    if table not in ("events", "event_deliveries"):
        return
    pk, column = (
        ("event_id", "payload_json")
        if table == "events"
        else ("event_delivery_id", "fields_read_json")
    )
    select = (
        "SELECT "
        + identifier(pk)
        + ",length(CAST("
        + identifier(column)
        + " AS BLOB)),hex(CAST("
        + identifier(column)
        + " AS BLOB)) FROM "
    )
    suffix = " ORDER BY CAST(" + identifier(pk) + " AS BLOB)"
    old = connection.execute(select + identifier(table) + suffix)
    new = connection.execute(select + identifier(table + "__k0b01_new") + suffix)
    while True:
        a, b = old.fetchmany(512), new.fetchmany(512)
        require(a == b, "migration:exact_length_HEX_copy")
        if not a:
            break


class AlphaStore:
    def __init__(
        self, context: InputContext, runtime_root: Path, approved_environment: str
    ) -> None:
        require(
            approved_environment in context.manifest["runtime_roots"],
            "root:environment_identity",
        )
        approved = Path(context.manifest["runtime_roots"][approved_environment])
        self.root = RuntimeRoot(runtime_root, approved)
        self.context = context
        self.metadata = context.package["migration"]
        assert_platform(self.metadata)
        self.blocks = migration_blocks(
            context.raw(self.metadata["path"]).decode("utf-8"), self.metadata
        )
        self.expected = expected_schema(context, self.blocks)

    def _verify(
        self,
        connection: sqlite3.Connection,
        version: int,
        expected_historical: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        require(version in (3, 4), "migration:unsupported_version")
        fingerprint = (
            self.expected.v3_fingerprint
            if version == 3
            else self.expected.v4_fingerprint
        )
        require(
            connection.execute("PRAGMA user_version").fetchone()[0] == version
            and schema_fingerprint(connection) == fingerprint,
            "migration:live_schema_drift",
        )
        require(
            migration_rows(connection) == self.expected.migration_rows[:version],
            "migration:identity_rows",
        )
        integrity(connection)
        digest = content_digest(connection, self.expected.historical_tables)
        if expected_historical is not None:
            require(
                equal_historical(expected_historical, digest),
                "migration:historical_digest_changed",
            )
        return digest

    def audit(
        self, source: Path, expected_historical: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        path = self.root.file(source, must_exist=True)
        with closing(readonly(path)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            digest = self._verify(connection, version, expected_historical)
            result = {
                "version": version,
                "schema_fingerprint": schema_fingerprint(connection),
                "historical_digest": digest,
                "payload_bytes": payload_byte_summaries(connection),
            }
        return result

    def verify_backup(
        self, backup: Path, expected_v3_digest: dict[str, Any]
    ) -> dict[str, Any]:
        backup = self.root.file(backup, must_exist=True)
        own_sha = sha256(backup.read_bytes())
        with closing(readonly(backup)) as connection:
            digest = self._verify(connection, 3, expected_v3_digest)
        require(
            sha256(backup.read_bytes()) == own_sha, "backup:artifact_changed_on_reopen"
        )
        return {
            "artifact_sha256": own_sha,
            "bytes": backup.stat().st_size,
            "schema_fingerprint": self.expected.v3_fingerprint,
            "historical_digest": digest,
            "source_file_byte_equality_required": False,
        }

    def restore(
        self, backup: Path, destination: Path, verified_backup: dict[str, Any]
    ) -> dict[str, Any]:
        backup = self.root.file(backup, must_exist=True)
        destination = self.root.file(destination, must_exist=False)
        require(
            backup != destination
            and sha256(backup.read_bytes()) == verified_backup["artifact_sha256"],
            "restore:backup_identity",
        )
        self.verify_backup(backup, verified_backup["historical_digest"])
        shutil.copyfile(backup, destination)
        with destination.open("r+b") as stream:
            os.fsync(stream.fileno())
        require(
            sha256(destination.read_bytes()) == verified_backup["artifact_sha256"],
            "restore:artifact_identity",
        )
        result = self.audit(destination, verified_backup["historical_digest"])
        require(result["version"] == 3, "restore:version")
        return {
            "result": "pass",
            "version": 3,
            "restored_artifact_sha256": sha256(destination.read_bytes()),
            "historical_digest": result["historical_digest"],
        }

    def initialize(
        self,
        source: Path,
        backup: Path | None = None,
        *,
        fault: str | None = None,
        observer: Callable[[str], None] | None = None,
        expected_historical: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = self.root.file(source, must_exist=True)
        require(
            fault is None or fault in self.metadata["exception_faults"],
            "migration:unknown_fault",
        )
        with _CACHE_LOCK:
            lock = _WRITER_LOCKS.setdefault(str(source), threading.Lock())
        require(lock.acquire(blocking=False), "migration:second_writer")
        connection: sqlite3.Connection | None = None
        observed: list[str] = []

        def boundary(name: str) -> None:
            require(
                name in self.metadata["exception_faults"] and name not in observed,
                "migration:boundary_inventory",
            )
            observed.append(name)
            if observer is not None:
                observer(name)
            if fault == name:
                raise InjectedFault(name)

        try:
            connection = sqlite3.connect(source, isolation_level=None, timeout=5)
            require(not connection.in_transaction, "migration:active_transaction")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            require(version in (3, 4), "migration:unsupported_version")
            configure(connection)
            connection.execute("PRAGMA foreign_keys=ON")
            require(
                connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
                "migration:FK_ON_preflight",
            )
            before = self._verify(connection, version, expected_historical)
            if version == 4:
                require(
                    fault is None and observer is None,
                    "migration:v4_fault_not_applicable",
                )
                return {
                    "result": "pass",
                    "version": 4,
                    "migrated": False,
                    "historical_digest": before,
                    "live_checks_repeated": True,
                    "schema_cache_key": list(self.expected.key),
                }
            require(backup is not None, "backup:explicit_required")
            backup = self.root.file(backup, must_exist=False)
            require(source != backup, "backup:source_destination_identity")
            before_bytes = payload_byte_summaries(connection)
            outside_owned = tuple(
                row
                for row in schema_rows(connection)
                if row[2] not in self.metadata["tables"]
            )
            boundary("B00.before_wal_checkpoint")
            checkpoint_result = connection.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            ).fetchone()
            require(
                checkpoint_result is not None
                and checkpoint_result[0] == 0
                and checkpoint_result[1:] == (0, 0),
                "migration:WAL_checkpoint_busy_or_frames",
            )
            boundary("B01.after_wal_checkpoint")
            connection.execute("PRAGMA foreign_keys=OFF")
            require(
                connection.execute("PRAGMA foreign_keys").fetchone()[0] == 0
                and not connection.in_transaction,
                "migration:FK_OFF_before_BEGIN",
            )
            boundary("B02.before_backup")
            destination = sqlite3.connect(backup, isolation_level=None)
            try:
                connection.backup(destination)
            finally:
                destination.close()
            with backup.open("r+b") as stream:
                os.fsync(stream.fileno())
            boundary("B03.after_backup_close")
            verified_backup = self.verify_backup(backup, before)
            boundary("B04.after_backup_verify")
            require(
                equal_historical(before, self._verify(connection, 3)),
                "migration:second_pre_mutation_digest",
            )
            boundary("T00.before_begin_immediate")
            connection.execute("BEGIN IMMEDIATE")
            boundary("T01.after_begin_immediate")
            require(
                equal_historical(before, self._verify(connection, 3)),
                "migration:writer_race_before_mutation",
            )
            for group in ("create", "copy", "drop", "rename"):
                if group == "rename":
                    rename_validation_window(connection, True)
                for name, sql in self.blocks:
                    if not name.startswith(group + "."):
                        continue
                    table = name.split(".", 1)[1]
                    label = {"copy": "C", "drop": "D", "rename": "R"}.get(group)
                    if label:
                        boundary(label + "." + table + ".before")
                    connection.execute(sql)
                    if group == "copy":
                        manifest = tuple(
                            t
                            for t in self.expected.historical_tables
                            if t.name == table
                        )
                        original = content_digest(connection, manifest)
                        copied = content_digest(
                            connection,
                            manifest,
                            source_names={table: table + "__k0b01_new"},
                        )
                        require(
                            equal_historical(original, copied), "migration:copy_digest"
                        )
                        compare_copy_bytes(connection, table)
                    if label:
                        boundary(label + "." + table + ".after")
                if group == "rename":
                    rename_validation_window(connection, False)
            boundary("S00.before_schema_objects")
            for name, sql in self.blocks:
                if name.startswith("object."):
                    connection.execute(sql)
            boundary("S01.after_schema_objects")
            new_names = {
                o["name"]
                for o in self.metadata["owned_recreated_catalog"]
                if o.get("definition")
            }
            outside_after = tuple(
                row
                for row in schema_rows(connection)
                if row[2] not in self.metadata["tables"]
                and row[1] not in new_names
                and row[2] not in new_names
            )
            require(
                outside_after == outside_owned, "migration:external_schema_SQL_changed"
            )
            require(
                schema_fingerprint(connection) == self.expected.v4_fingerprint,
                "migration:v4_fingerprint_before_record",
            )
            require(
                equal_historical(
                    before, content_digest(connection, self.expected.historical_tables)
                )
                and payload_byte_summaries(connection) == before_bytes,
                "migration:pre_record_historical_bytes",
            )
            boundary("M00.before_migration_row")
            connection.execute(
                "INSERT INTO schema_migrations(version,name,sha256) VALUES (?,?,?)",
                self.expected.migration_rows[3],
            )
            boundary("M01.after_migration_row")
            connection.execute("PRAGMA user_version=4")
            boundary("M02.after_user_version")
            boundary("V00.before_integrity_checks")
            after = self._verify(connection, 4, before)
            require(
                payload_byte_summaries(connection) == before_bytes,
                "migration:precommit_payload_length_HEX",
            )
            boundary("V01.after_integrity_checks")
            boundary("T99.immediately_before_commit")
            require(
                observed == self.metadata["exception_faults"],
                "migration:full_boundary_order",
            )
            connection.execute("COMMIT")
            connection.execute("PRAGMA foreign_keys=ON")
            require(
                connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
                "migration:FK_ON_after_COMMIT",
            )
            self._verify(connection, 4, before)
            require(
                payload_byte_summaries(connection) == before_bytes,
                "migration:postcommit_payload_length_HEX",
            )
            return {
                "result": "pass",
                "version": 4,
                "migrated": True,
                "historical_digest": after,
                "verified_backup": verified_backup,
                "payload_length_HEX_preserved": True,
                "external_schema_SQL_preserved": True,
                "observed_boundaries": observed,
                "schema_cache_key": list(self.expected.key),
                "runtime_enabled": False,
            }
        except sqlite3.Error as exc:
            raise MigrationError("migration:SQLite:" + str(exc)) from exc
        finally:
            if connection is not None:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                connection.close()
            lock.release()
