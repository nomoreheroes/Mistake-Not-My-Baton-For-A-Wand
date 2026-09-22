from __future__ import annotations

import sqlite3

import pytest

from fixture_support import ContractError, database_for, intent, record
from k0b02_v1.outbox import claim
from k0b02_v1.transaction_writer import admit


def test_atomic_decision_event_and_outbox() -> None:
    root, database, store = database_for("atomic_decision_outbox")
    result = admit(database, intent("atomic_decision_outbox"))
    connection = sqlite3.connect(database)
    counts = {
        table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        for table in (
            "k0b02_decision_versions",
            "events",
            "k0b02_projection_outbox",
            "k0b02_outbox_phase_bindings",
        )
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
        "k0b02_outbox_phase_bindings": 1,
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


def test_claims_are_source_ordered_and_attempts_are_compiled_bounded() -> None:
    root, database, store = database_for("ordered_claims")
    first = admit(database, intent("ordered_claims", 1))
    second_intent = intent("ordered_claims", 2)
    second_intent["decision_version_id"] = "decision-ordered-claims-2"
    second_intent["stable_identity"] = second_intent["decision_version_id"]
    second_intent["idempotency_key"] = "run-ordered_claims|decision-2|2"
    second = admit(database, second_intent)
    with pytest.raises(ContractError, match="claim_order"):
        claim(database, second["outbox_id"])
    claimed = claim(database, first["outbox_id"])
    assert claimed["source_seq"] == 1
    with pytest.raises(ContractError, match="attempt_cap"):
        claim(database, first["outbox_id"])
    connection = sqlite3.connect(database)
    attempts = connection.execute(
        "SELECT attempt_no,status FROM k0b02_projection_attempts ORDER BY attempt_no"
    ).fetchall()
    connection.close()
    assert attempts == [(1, "begun")]
    record("ordered_claims", attempt_cap=1)


def test_outbox_phase_binding_drift_blocks_before_attempt() -> None:
    root, database, store = database_for("outbox_phase_binding_drift")
    admitted = admit(database, intent("outbox_phase_binding_drift"))
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE k0b02_outbox_phase_bindings SET partition_digest=? WHERE outbox_id=?",
        ("9" * 64, admitted["outbox_id"]),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ContractError, match="phase_binding"):
        claim(database, admitted["outbox_id"])
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT status,attempts FROM k0b02_projection_outbox WHERE outbox_id=?",
        (admitted["outbox_id"],),
    ).fetchone() == ("pending", 0)
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_projection_attempts").fetchone()[
            0
        ]
        == 0
    )
    connection.close()
    record("outbox_phase_binding_drift")
