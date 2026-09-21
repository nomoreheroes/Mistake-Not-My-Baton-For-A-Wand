from __future__ import annotations

import sqlite3

import pytest

from fixture_support import ContractError, database_for, intent, record
from k0b02_v1.transaction_writer import admit


def test_atomic_decision_event_and_outbox() -> None:
    root, database, store = database_for("atomic_decision_outbox")
    result = admit(database, intent("atomic_decision_outbox"))
    connection = sqlite3.connect(database)
    counts = {
        table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        for table in ("k0b02_decision_versions", "events", "k0b02_projection_outbox")
    }
    event = connection.execute(
        "SELECT event_type,event_version,payload_json,idempotency_key FROM events WHERE event_id=?",
        (result["event"]["event_id"],),
    ).fetchone()
    connection.close()
    assert counts == {
        "k0b02_decision_versions": 1,
        "events": 1,
        "k0b02_projection_outbox": 1,
    }
    assert event[0:2] == ("projection.requested", 1)
    record("atomic_decision_outbox", source_seq=result["source_seq"])


def test_identical_duplicate_returns_original() -> None:
    root, database, store = database_for("duplicate_original_result")
    value = intent("duplicate_original_result")
    first, second = admit(database, value), admit(database, value)
    assert second["result"] == "duplicate_original"
    assert (first["decision_version_id"], first["source_seq"], first["outbox_id"]) == (
        second["decision_version_id"],
        second["source_seq"],
        second["outbox_id"],
    )
    record("duplicate_original_result")


def test_conflicting_duplicate_blocks_without_second_effect() -> None:
    root, database, store = database_for("conflicting_duplicate")
    value = intent("conflicting_duplicate")
    first = admit(database, value)
    changed = dict(value)
    changed["expected_revision"] = 2
    with pytest.raises(ContractError, match="conflicting_duplicate"):
        admit(database, changed)
    connection = sqlite3.connect(database)
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_decision_versions").fetchone()[0]
        == 1
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_projection_outbox").fetchone()[0]
        == 1
    )
    connection.close()
    record("conflicting_duplicate", original_outbox_id=first["outbox_id"])
