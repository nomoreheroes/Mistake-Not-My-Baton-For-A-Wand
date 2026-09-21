from __future__ import annotations

import sqlite3

import pytest

from fixture_support import ContractError, database_for, record


class StopAtBoundary(BaseException):
    pass


def test_v4_to_v5_preserves_historical_catalog_and_rows() -> None:
    root, database, store = database_for("migration_v4_to_v5", 4)
    connection = sqlite3.connect(database)
    before = connection.execute(
        "SELECT type,name,sql FROM sqlite_schema WHERE name NOT LIKE 'k0b02_%' ORDER BY type,name"
    ).fetchall()
    connection.close()
    result = store.initialize_to_version(database, 5)
    connection = sqlite3.connect(database)
    after = connection.execute(
        "SELECT type,name,sql FROM sqlite_schema WHERE name NOT LIKE 'k0b02_%' ORDER BY type,name"
    ).fetchall()
    connection.close()
    after_by_identity = {(kind, name): sql for kind, name, sql in after}
    assert all(after_by_identity[(kind, name)] == sql for kind, name, sql in before)
    assert result["user_version"] == 5 and len(result["k0b02_tables"]) == 12
    record("migration_v4_to_v5", schema_fingerprint=result["schema_fingerprint"])


def test_v5_to_v6_and_repeat_readback() -> None:
    root, database, store = database_for("migration_v5_to_v6", 5)
    result = store.initialize_to_version(database, 6)
    assert result["user_version"] == 6 and len(result["k0b02_tables"]) == 17
    record("migration_v5_to_v6", schema_fingerprint=result["schema_fingerprint"])

    root, database, store = database_for("migration_repeat_readback", 6)
    first, second = store.audit(database), store.initialize_to_version(database, 6)
    assert first == second
    record("migration_repeat_readback", schema_fingerprint=first["schema_fingerprint"])


def test_unknown_schema_hard_blocks_without_catalog_write() -> None:
    root, database, store = database_for("migration_unknown_schema", 6)
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version=7")
    connection.close()
    before = database.read_bytes()
    with pytest.raises(ContractError, match="unsupported_version"):
        store.audit(database)
    assert database.read_bytes() == before
    record("migration_unknown_schema")


@pytest.mark.parametrize(
    ("case_id", "boundary", "expected_version"),
    (
        ("migration_exception_before_commit", "new_migration_before_commit", 4),
        ("migration_loss_before_commit", "new_migration_before_commit", 4),
        ("migration_loss_after_commit", "new_migration_after_commit", 5),
    ),
)
def test_migration_boundary_recovery(
    case_id: str, boundary: str, expected_version: int
) -> None:
    root, database, store = database_for(
        case_id, 4, "exception" if "exception" in case_id else "process_loss"
    )

    def observer(actual: str) -> None:
        if actual == boundary:
            raise StopAtBoundary(actual)

    with pytest.raises(StopAtBoundary):
        store.initialize_to_version(database, 5, observer)
    connection = sqlite3.connect(database)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    connection.close()
    assert version == expected_version and integrity == "ok"
    record(case_id, durable_user_version=version)
