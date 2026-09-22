from __future__ import annotations

import json
import os
import ctypes
from ctypes import wintypes
import sqlite3
import subprocess
import sys
import time

import pytest

from fixture_support import (
    ContractError,
    REPOSITORY,
    RUNTIME_ROOT,
    database_for,
    init_coordination,
    intent,
    publication_request,
    publish,
    published,
    ready_pair,
    record,
    run_git,
    runtime_values,
)
from k0b02_v1.canonical import json_bytes
from k0b02_v1.outbox import claim
from k0b02_v1.phase import bind, record_publication
from k0b02_v1.reconciliation import reconcile
from k0b02_v1.transaction_writer import admit


class ProcessLoss(BaseException):
    pass


def _terminate_worker(identity: dict, launcher_pid: int) -> None:
    assert identity["launcher_pid"] == launcher_pid
    assert type(identity["pid"]) is int and identity["pid"] != os.getpid()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000 | 0x0001 | 0x00100000, False, identity["pid"])
    assert handle
    try:
        assert kernel.TerminateProcess(handle, 193)
        assert kernel.WaitForSingleObject(handle, 10000) == 0
    finally:
        assert kernel.CloseHandle(handle)


def _begun(case_id: str):
    bundle = ready_pair(case_id)
    request = publication_request(bundle)

    def observer(boundary: str) -> None:
        if boundary == "backup_verified":
            raise ProcessLoss(boundary)

    with pytest.raises(ProcessLoss):
        publish(
            bundle["store"], bundle["database"], bundle["repository"], request, observer
        )
    return bundle, request


def test_ambiguous_begun_effect_blocks() -> None:
    bundle, request = _begun("replay_ambiguous_begun_effect")
    unrelated = bundle["repository"] / "unrelated.txt"
    unrelated.write_bytes(b"new unrelated state\n")
    run_git(bundle["repository"], "add", "--", "unrelated.txt")
    run_git(
        bundle["repository"],
        "commit",
        "--no-gpg-sign",
        "-m",
        "ambiguous external effect",
    )
    with pytest.raises(ContractError, match="ambiguous_unknown_effect"):
        reconcile(bundle["database"], bundle["repository"], request["publication_id"])
    record("replay_ambiguous_begun_effect")


def test_unknown_effect_is_not_invented_or_blindly_aborted() -> None:
    bundle, request = _begun("abort_unknown_effect")
    result = reconcile(
        bundle["database"], bundle["repository"], request["publication_id"]
    )
    assert result == {"result": "safe_to_retry_no_effect"}
    record("abort_unknown_effect")


BOUNDARIES = (
    ("migration_loss_before_commit", "migration", "new_migration_before_commit"),
    ("migration_loss_after_commit", "migration", "new_migration_after_commit"),
    ("projection_before_source_commit", "decision", "decision_outbox_before_commit"),
    (
        "projection_after_source_commit",
        "decision",
        "decision_outbox_after_commit_before_response",
    ),
    ("projection_after_first_peer", "projector", "first_peer_replaced"),
    ("projection_after_both_peers", "projector", "both_peers_replaced_before_result"),
    ("publication_after_backup", "publisher", "backup_verified"),
    ("publication_after_snapshot_replace", "publisher", "snapshot_replaced"),
    (
        "publication_after_git_commit",
        "publisher",
        "coordination_Git_commit_before_DB_result",
    ),
    ("publication_after_db_result", "publisher", "publication_DB_result"),
    ("phase_before_seal", "seal", "terminal_checkpoint_before_seal"),
    ("phase_after_seal", "seal", "seal_committed_before_successor_admission"),
)


def _boundary_fixture(case_id: str, operation: str):
    repository = None
    if operation == "migration":
        root, database, store = database_for(case_id, 4, "process_loss")
        payload = {"target_version": 5}
    elif operation == "decision":
        root, database, store = database_for(case_id, 6, "process_loss")
        payload = intent(case_id)
    elif operation == "projector":
        root, database, store = database_for(case_id, 6, "process_loss")
        repository, parent, envelope_sha = init_coordination(root)
        admitted = admit(database, intent(case_id))
        claim(database, admitted["outbox_id"])
        payload = {"outbox_id": admitted["outbox_id"]}
    elif operation == "publisher":
        bundle = ready_pair(case_id)
        store = bundle["store"]
        root, database, repository = (
            bundle["root"],
            bundle["database"],
            bundle["repository"],
        )
        payload = publication_request(bundle)
    else:
        bundle, request, result = published(case_id)
        store = bundle["store"]
        root, database, repository = (
            bundle["root"],
            bundle["database"],
            bundle["repository"],
        )
        bind(database, "1" * 64)
        record_publication(
            database, runtime_values()["phases"][0], result["snapshot_bytes"]
        )
        payload = {
            "seal_id": "seal-" + case_id,
            "phase_id": runtime_values()["phases"][0],
            "partition_digest": "1" * 64,
            "predecessor_seal_id": None,
            "terminal_checkpoint_publication_id": request["publication_id"],
            "terminal_checkpoint_sha256": result["snapshot_sha256"],
            "ready_pair_set_sha256": request["ready_pair_set_sha256"],
            "outbox_high_water": 1,
            "cumulative_full_bytes": result["snapshot_bytes"],
            "publication_count": 1,
            "authorities": [],
            "all_admitted_members_terminal": True,
            "no_unresolved_begun_effects": True,
            "result": "sealed",
        }
    payload_path = root / "fault-result.json"
    payload_path.write_bytes(json_bytes(payload))
    return root, database, repository, payload_path, store


@pytest.mark.parametrize(("case_id", "operation", "boundary"), BOUNDARIES)
def test_all_twelve_owned_process_loss_boundaries(
    case_id: str, operation: str, boundary: str
) -> None:
    root, database, repository, payload, store = _boundary_fixture(case_id, operation)
    marker, ready = root / "durable-marker.json", root / "durable-marker.ready"
    worker = REPOSITORY / "new pipeline/tests/k0b02_v1/fault_worker.py"
    command = [
        sys.executable,
        "-I",
        "-B",
        str(worker),
        "--repository-root",
        str(REPOSITORY),
        "--runtime-root",
        str(RUNTIME_ROOT),
        "--database",
        str(database),
        "--operation",
        operation,
        "--boundary",
        boundary,
        "--payload",
        str(payload),
        "--marker",
        str(marker),
        "--ready",
        str(ready),
    ]
    if repository is not None:
        command += ["--repository", str(repository)]
    child = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 30
        while (
            (not ready.exists() or ready.stat().st_size != 22)
            and child.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if not ready.exists() or ready.stat().st_size != 22:
            child.kill()
            stdout, stderr = child.communicate(timeout=10)
            pytest.fail(stdout.decode() + stderr.decode())
        identity = json.loads(marker.read_bytes())
        assert identity["launcher_pid"] == child.pid and identity["pid"] != os.getpid()
        assert (
            identity["boundary"] == boundary
            and ready.read_bytes() == b"durable marker closed\n"
        )
        _terminate_worker(identity, child.pid)
        child.communicate(timeout=10)
        assert child.returncode != 0
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    if operation == "publisher":
        request = json.loads(payload.read_bytes())
        recovered = publish(store, database, repository, request)
        assert recovered["result"] in {"committed", "recovered", "original"}
    connection = sqlite3.connect(database)
    if operation == "migration":
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        assert version == (4 if boundary.endswith("before_commit") else 5)
    elif operation == "decision":
        count = connection.execute(
            "SELECT COUNT(*) FROM k0b02_decision_versions"
        ).fetchone()[0]
        assert count == (0 if boundary.endswith("before_commit") else 1)
    elif operation == "projector":
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_projection_pairs"
            ).fetchone()[0]
            == 0
        )
    elif operation == "publisher" and boundary == "publication_DB_result":
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_publication_results"
            ).fetchone()[0]
            == 1
        )
    if operation == "publisher":
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_publication_attempts"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_publication_results"
            ).fetchone()[0]
            == 1
        )
    elif operation == "seal":
        count = connection.execute("SELECT COUNT(*) FROM k0b02_phase_seals").fetchone()[
            0
        ]
        assert count == (0 if boundary == "terminal_checkpoint_before_seal" else 1)
    connection.close()
