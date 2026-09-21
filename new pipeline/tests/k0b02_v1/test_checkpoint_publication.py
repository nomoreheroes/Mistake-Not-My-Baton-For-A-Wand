from __future__ import annotations

import math
import sqlite3
import subprocess

import pytest

from fixture_support import (
    ContractError,
    measured,
    publication_request,
    publish,
    published,
    ready_pair,
    record,
    sha256,
)
from k0b02_v1.publisher import CHECKPOINT_PATH, PAIR_PATHS, _git


class ProcessLoss(BaseException):
    pass


def _blob(repository, commit, path):
    return subprocess.run(
        ["git", "-C", str(repository), "show", commit + ":" + path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout


def test_before_backup_invalid_cut_has_no_effect() -> None:
    bundle = ready_pair("publication_before_backup")
    request = publication_request(bundle)
    request["ready_pair_set_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="pair_set"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert not (bundle["repository"] / CHECKPOINT_PATH).exists()
    assert _git(bundle["repository"], "rev-parse", "HEAD") == bundle["parent"]
    record("publication_before_backup")


@pytest.mark.parametrize(
    ("case_id", "boundary"),
    (
        ("publication_after_backup", "backup_verified"),
        ("publication_after_snapshot_replace", "snapshot_replaced"),
        ("publication_after_git_commit", "coordination_Git_commit_before_DB_result"),
        ("publication_after_db_result", "publication_DB_result"),
    ),
)
def test_publication_process_loss_recovers_once(case_id: str, boundary: str) -> None:
    bundle = ready_pair(case_id)
    request = publication_request(bundle)

    def observer(actual: str) -> None:
        if actual == boundary:
            raise ProcessLoss(actual)

    with pytest.raises(ProcessLoss):
        publish(
            bundle["store"], bundle["database"], bundle["repository"], request, observer
        )
    recovered = publish(
        bundle["store"], bundle["database"], bundle["repository"], request
    )
    assert recovered["result"] in {"committed", "recovered", "original"}
    connection = sqlite3.connect(bundle["database"])
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM k0b02_publication_results WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchone()[0]
        == 1
    )
    connection.close()
    assert (
        _git(bundle["repository"], "log", "--format=%B", "-1").count(
            "Pipeline-Checkpoint-Publication-ID: publication-v1"
        )
        == 1
    )
    record(case_id, recovery_result=recovered["result"])


def test_dirty_unrelated_file_blocks_before_publication_mutation() -> None:
    bundle = ready_pair("publication_dirty_tree")
    request = publication_request(bundle)
    (bundle["repository"] / "unrelated.txt").write_bytes(b"dirty\n")
    with pytest.raises(ContractError, match="dirty_tree"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    connection = sqlite3.connect(bundle["database"])
    assert (
        connection.execute("SELECT COUNT(*) FROM k0b02_publication_intents").fetchone()[
            0
        ]
        == 0
    )
    connection.close()
    record("publication_dirty_tree")


def test_checkpoint_binary_divergence_blocks_terminal_readback() -> None:
    bundle, request, result = published("publication_binary_divergence")
    checkpoint = bundle["repository"] / CHECKPOINT_PATH
    checkpoint.write_bytes(checkpoint.read_bytes() + b"divergence")
    with pytest.raises(ContractError, match="terminal_checkpoint_drift"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    record("publication_binary_divergence", committed=result["git_commit"])


def test_twelve_isolated_publication_samples_and_blob_byte_invariance() -> None:
    elapsed = []
    for number in range(1, 13):
        case_id = f"publication_performance_{number:02d}"

        def operation(case_id=case_id):
            return published(case_id)

        (bundle, request, result), duration = measured(case_id, operation)
        elapsed.append(duration)
        for path in PAIR_PATHS:
            file_raw = (bundle["repository"] / path).read_bytes()
            blob_raw = _blob(bundle["repository"], result["git_commit"], path)
            assert file_raw == blob_raw and sha256(file_raw) == sha256(blob_raw)
    ordered = sorted(elapsed)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    assert p95 < 10.0
