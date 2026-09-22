from __future__ import annotations

import sqlite3

import pytest

from fixture_support import (
    ContractError,
    database_for,
    init_coordination,
    intent,
    record,
    runtime_values,
)
from k0b02_v1.outbox import claim
from k0b02_v1.projector import project
from k0b02_v1.transaction_writer import admit


class ProcessLoss(BaseException):
    pass


def _prepared(case_id: str):
    root, database, store = database_for(case_id)
    repository, parent, envelope_sha = init_coordination(root)
    admitted = admit(database, intent(case_id))
    claim(database, admitted["outbox_id"])
    return root, database, repository, admitted


def test_projection_before_and_after_source_commit() -> None:
    root, database, store = database_for(
        "projection_before_source_commit", variant="process_loss"
    )

    def before(boundary: str) -> None:
        if boundary == "decision_outbox_before_commit":
            raise ProcessLoss(boundary)

    with pytest.raises(ProcessLoss):
        admit(database, intent("projection_before_source_commit"), before)
    connection = sqlite3.connect(database)
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_decision_versions").fetchone()[0]
        == 0
    )
    connection.close()
    record("projection_before_source_commit")

    root, database, store = database_for(
        "projection_after_source_commit", variant="process_loss"
    )

    def after(boundary: str) -> None:
        if boundary == "decision_outbox_after_commit_before_response":
            raise ProcessLoss(boundary)

    with pytest.raises(ProcessLoss):
        admit(database, intent("projection_after_source_commit"), after)
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT outbox_id FROM k0b02_projection_outbox").fetchone()
    connection.close()
    assert row is not None
    record("projection_after_source_commit", outbox_id=row[0])


@pytest.mark.parametrize(
    ("case_id", "boundary", "expected_files"),
    (
        ("projection_after_first_peer", "first_peer_replaced", 1),
        ("projection_after_both_peers", "both_peers_replaced_before_result", 2),
    ),
)
def test_projection_process_loss_readback(
    case_id: str, boundary: str, expected_files: int
) -> None:
    root, database, repository, admitted = _prepared(case_id)

    def observer(actual: str) -> None:
        if actual == boundary:
            raise ProcessLoss(actual)

    with pytest.raises(ProcessLoss):
        project(database, admitted["outbox_id"], repository, observer)
    peers = [repository / path for path in runtime_values()["pair_paths"]]
    assert sum(path.is_file() for path in peers) == expected_files
    connection = sqlite3.connect(database)
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_projection_pairs").fetchone()[0]
        == 0
    )
    connection.close()
    recovered = project(database, admitted["outbox_id"], repository)
    assert recovered["result"] == "written" and all(path.is_file() for path in peers)
    record(case_id, recovered=True)


def test_projection_drift_is_detected_on_original_readback() -> None:
    root, database, repository, admitted = _prepared("projection_drift")
    result = project(database, admitted["outbox_id"], repository)
    target = repository / runtime_values()["pair_paths"][0]
    target.write_bytes(target.read_bytes() + b"drift\n")
    with pytest.raises(ContractError, match="existing_pair_drift"):
        project(database, admitted["outbox_id"], repository)
    assert result["ready"] is True
    record("projection_drift")


def test_projection_failure_receipt_is_terminal_and_keeps_v1_payload() -> None:
    root, database, repository, admitted = _prepared("projection_failure_receipt")
    target = repository / runtime_values()["pair_paths"][0]
    temporary = target.with_name("." + target.name + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(b"owned failure fixture\n")
    with pytest.raises(ContractError, match="temp_exists"):
        project(database, admitted["outbox_id"], repository)
    connection = sqlite3.connect(database)
    result = connection.execute(
        "SELECT result,event_json FROM k0b02_projection_results WHERE outbox_id=?",
        (admitted["outbox_id"],),
    ).fetchone()
    status = connection.execute(
        "SELECT status FROM k0b02_projection_outbox WHERE outbox_id=?",
        (admitted["outbox_id"],),
    ).fetchone()[0]
    connection.close()
    assert (
        result is not None
        and result[0] == "failed"
        and '"event_type":"projection.failed"' in result[1]
    )
    assert status == "failed"
    record("projection_failure_receipt")


def test_projection_event_schema_hashes_come_from_compiled_profile() -> None:
    root, database, repository, admitted = _prepared("projection_compiled_schemas")
    project(database, admitted["outbox_id"], repository)
    profile = runtime_values()
    connection = sqlite3.connect(database)
    rows = dict(
        connection.execute(
            "SELECT event_type,schema_sha256 FROM events "
            "WHERE event_type IN ('projection.requested','projection.written')"
        )
    )
    connection.close()
    assert rows == {
        name: profile["event_schema_sha256"][name]
        for name in ("projection.requested", "projection.written")
    }
    record("projection_compiled_schemas")


def test_unapproved_pair_stem_rejected_before_mutation() -> None:
    root, database, store = database_for("projection_unapproved_pair_stem_rejected")
    changed = intent("projection_unapproved_pair_stem_rejected")
    changed["pair_stem"] = "shadow-decision"
    with pytest.raises(ContractError, match="writer:pair_stem"):
        admit(database, changed)
    connection = sqlite3.connect(database)
    counts = [
        connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        for table in ("k0b02_decision_versions", "k0b02_projection_outbox")
    ]
    connection.close()
    assert counts == [0, 0]
    record("projection_unapproved_pair_stem_rejected")
