from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path


class CompatibilityError(ValueError):
    pass


def apply_migration(database: Path, migration: Path) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    script = migration.read_text(encoding="utf-8")
    with sqlite3.connect(database) as connection:
        connection.executescript(script)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if version != 7 or foreign_keys:
            raise CompatibilityError("migration validation failed")


def database_integrity(database: Path) -> str:
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if result != "ok" or foreign_keys:
        raise CompatibilityError("database integrity failed")
    return result


def backup_database(source: Path, target: Path) -> str:
    if target.exists():
        raise CompatibilityError("backup target must be new")
    database_integrity(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
        source_connection.backup(target_connection)
    database_integrity(target)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def restore_to_new_target(backup: Path, target: Path) -> str:
    if target.exists():
        raise CompatibilityError("restore target must be new")
    database_integrity(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(backup, target)
    database_integrity(target)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def schema_version(database: Path) -> int:
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def older_harness_disposition(database: Path, supported_version: int) -> str:
    return "read_only_diagnostic" if schema_version(database) > supported_version else "compatible"
