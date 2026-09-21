from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

from .canonical import ContractError, no_reparse, require, sha256
from .contract import InputContext
from .digest import schema_fingerprint

FaultObserver = Callable[[str], None]


def _execute(connection: sqlite3.Connection, sql: str) -> None:
    current = ""
    for line in sql.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            if current.strip():
                connection.execute(current)
            current = ""
    require(not current.strip(), "migration:incomplete_statement")


def _v4_blocks(sql: str) -> tuple[tuple[str, str], ...]:
    pieces = re.split(r"^-- k0b01: ([a-z]+\.[A-Za-z0-9_]+)\n", sql, flags=re.MULTILINE)
    require(
        not pieces[0].strip() and len(pieces) > 1 and len(pieces) % 2 == 1,
        "migration:v4_block_format",
    )
    blocks = tuple(
        (pieces[index], pieces[index + 1].strip()) for index in range(1, len(pieces), 2)
    )
    names = [name for name, _ in blocks]
    require(
        len(names) == len(set(names))
        and names[:4]
        == [
            "create.runs",
            "create.events",
            "create.run_state_transitions",
            "create.event_deliveries",
        ]
        and any(name.startswith("rename.") for name in names)
        and any(name.startswith("object.") for name in names),
        "migration:v4_block_inventory",
    )
    for _, statement in blocks:
        require(sqlite3.complete_statement(statement + "\n"), "migration:v4_statement")
    return blocks


def _execute_v4(connection: sqlite3.Connection, sql: str) -> None:
    renaming = False
    for name, statement in _v4_blocks(sql):
        if name.startswith("rename.") and not renaming:
            connection.execute("PRAGMA writable_schema=ON")
            renaming = True
        elif name.startswith("object.") and renaming:
            connection.execute("PRAGMA writable_schema=OFF")
            renaming = False
        connection.execute(statement)
    require(not renaming, "migration:v4_validation_window")


class SafeRoot:
    def __init__(self, actual: Path, approved: Path) -> None:
        require(actual.is_absolute() and actual == approved, "root:identity")
        no_reparse(actual)
        require(actual.is_dir(), "root:directory")
        self.actual = actual

    def file(self, path: Path, *, must_exist: bool = False) -> Path:
        require(path.is_absolute() and path != self.actual, "root:file_absolute")
        try:
            relative = path.relative_to(self.actual)
        except ValueError as exc:
            raise ContractError("root:escape") from exc
        require(".." not in relative.parts, "root:traversal")
        path.parent.mkdir(parents=True, exist_ok=True)
        no_reparse(path.parent)
        require(
            path.parent.resolve().is_relative_to(self.actual.resolve()),
            "root:resolved_escape",
        )
        if must_exist:
            no_reparse(path)
            require(path.is_file(), "root:missing_file")
        else:
            require(not path.is_symlink(), "root:symlink")
        return path


class K0b02Store:
    MIGRATIONS = (
        (1, "0001_k0a01", "new pipeline/harness/migrations/0001_k0a01.sql"),
        (2, "0002_k0a02", "new pipeline/harness/migrations/0002_k0a02.sql"),
        (3, "0003_k0a03", "new pipeline/harness/migrations/0003_k0a03.sql"),
        (4, "0004_k0b01_v2", "new pipeline/harness/migrations/0004_k0b01_v2.sql"),
        (
            5,
            "0005_k0b02_publication_replay_v1",
            "new pipeline/harness/migrations/0005_k0b02_publication_replay_v1.sql",
        ),
        (
            6,
            "0006_k0b02_checkpoint_phase_partition_v1",
            "new pipeline/harness/migrations/0006_k0b02_checkpoint_phase_partition_v1.sql",
        ),
    )

    def __init__(
        self, context: InputContext, runtime_root: Path, approved_root: Path
    ) -> None:
        self.context = context
        self.root = SafeRoot(runtime_root, approved_root)

    @staticmethod
    def connect(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _migrate_one(
        self,
        connection: sqlite3.Connection,
        version: int,
        name: str,
        locator: str,
        observer: FaultObserver | None,
    ) -> None:
        pin = self.context.pin(locator)
        raw = self.context.raw(locator)
        require(sha256(raw) == pin["sha256"], "migration:pin")
        if observer and version >= 5:
            observer("new_migration_before_commit")
        if version == 4:
            connection.execute("PRAGMA foreign_keys=OFF")
            require(
                connection.execute("PRAGMA foreign_keys").fetchone()[0] == 0,
                "migration:v4_FK_window",
            )
        connection.execute("BEGIN IMMEDIATE")
        try:
            if version == 4:
                _execute_v4(connection, raw.decode("utf-8", "strict"))
            else:
                _execute(connection, raw.decode("utf-8", "strict"))
            connection.execute(
                "INSERT INTO schema_migrations(version,name,sha256) VALUES(?,?,?)",
                (version, name, pin["sha256"]),
            )
            connection.execute("PRAGMA user_version=" + str(version))
            connection.commit()
        except BaseException:
            connection.rollback()
            if version == 4:
                connection.execute("PRAGMA writable_schema=OFF")
                connection.execute("PRAGMA foreign_keys=ON")
            raise
        if version == 4:
            connection.execute("PRAGMA writable_schema=OFF")
            connection.execute("PRAGMA foreign_keys=ON")
            require(
                connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
                "migration:v4_FK_restored",
            )
        if observer and version >= 5:
            observer("new_migration_after_commit")

    def initialize_to_version(
        self, database: Path, version: int = 6, observer: FaultObserver | None = None
    ) -> dict[str, Any]:
        require(version in (4, 5, 6), "migration:target_version")
        database = self.root.file(database)
        connection = self.connect(database)
        try:
            current = connection.execute("PRAGMA user_version").fetchone()[0]
            require(current in range(0, 7), "migration:unsupported_version")
            for item in self.MIGRATIONS:
                if current < item[0] <= version:
                    self._migrate_one(connection, *item, observer)
                    current = item[0]
            return self._audit_connection(connection, version)
        finally:
            connection.close()

    def migrate(
        self, database: Path, backup: Path, observer: FaultObserver | None = None
    ) -> dict[str, Any]:
        database = self.root.file(database, must_exist=True)
        backup = self.root.file(backup)
        require(not backup.exists(), "migration:backup_exists")
        source = self.connect(database)
        try:
            version = source.execute("PRAGMA user_version").fetchone()[0]
            require(version in (4, 5, 6), "migration:unsupported_version")
            if version < 6:
                target = sqlite3.connect(backup)
                try:
                    source.backup(target)
                    target.execute("PRAGMA foreign_keys=ON")
                    require(
                        target.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                        "backup:integrity",
                    )
                    require(
                        not list(target.execute("PRAGMA foreign_key_check")),
                        "backup:foreign_keys",
                    )
                finally:
                    target.close()
        finally:
            source.close()
        return self.initialize_to_version(database, 6, observer)

    def _audit_connection(
        self, connection: sqlite3.Connection, version: int
    ) -> dict[str, Any]:
        require(
            connection.execute("PRAGMA user_version").fetchone()[0] == version,
            "audit:user_version",
        )
        require(
            connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "audit:integrity",
        )
        require(
            not list(connection.execute("PRAGMA foreign_key_check")),
            "audit:foreign_keys",
        )
        migrations = list(
            connection.execute(
                "SELECT version,name,sha256 FROM schema_migrations ORDER BY version"
            )
        )
        require(
            [row[0] for row in migrations] == list(range(1, version + 1)),
            "audit:migration_rows",
        )
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name LIKE 'k0b02_%' ORDER BY name"
            )
        ]
        expected = 0 if version == 4 else 12 if version == 5 else 17
        require(len(tables) == expected, "audit:k0b02_table_count")
        return {
            "result": "pass",
            "user_version": version,
            "schema_fingerprint": schema_fingerprint(connection),
            "migration_rows": [list(x) for x in migrations],
            "k0b02_tables": tables,
            "integrity_check": "ok",
            "foreign_key_check": [],
            "runtime_enabled": False,
        }

    def audit(self, database: Path) -> dict[str, Any]:
        database = self.root.file(database, must_exist=True)
        connection = self.connect(database)
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            require(version in (4, 5, 6), "migration:unsupported_version")
            return self._audit_connection(connection, version)
        finally:
            connection.close()

    def snapshot(self, database: Path, candidate: Path) -> dict[str, Any]:
        database = self.root.file(database, must_exist=True)
        candidate = self.root.file(candidate)
        require(not candidate.exists(), "snapshot:existing_candidate")
        source = self.connect(database)
        target = sqlite3.connect(candidate)
        try:
            source.backup(target)
            target.execute("PRAGMA foreign_keys=ON")
            require(
                target.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "snapshot:integrity",
            )
            require(
                not list(target.execute("PRAGMA foreign_key_check")),
                "snapshot:foreign_keys",
            )
        finally:
            target.close()
            source.close()
        with candidate.open("r+b") as stream:
            os.fsync(stream.fileno())
        raw = candidate.read_bytes()
        return {"sha256": sha256(raw), "bytes": len(raw), "user_version": 6}
