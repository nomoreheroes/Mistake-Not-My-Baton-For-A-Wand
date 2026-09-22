from __future__ import annotations

import math
from pathlib import Path
import sqlite3

import pytest

from fixture_support import (
    ContractError,
    intent,
    measured,
    publication_request,
    publish,
    published,
    ready_pair,
    record,
    run_git,
    runtime_values,
    sha256,
)
from k0b02_v1.publisher import _git, _git_bytes, _known_commit
from k0b02_v1.transaction_writer import admit


class ProcessLoss(BaseException):
    pass


def _blob(repository, commit, path):
    return _git_bytes(repository, "show", commit + ":" + path)


def test_before_backup_invalid_cut_has_no_effect() -> None:
    bundle = ready_pair("publication_before_backup")
    request = publication_request(bundle)
    request["ready_pair_set_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="pair_set"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert not (bundle["repository"] / runtime_values()["checkpoint_path"]).exists()
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
    attempts = connection.execute(
        "SELECT boundary,effect_commit FROM k0b02_publication_attempts WHERE publication_id=?",
        (request["publication_id"],),
    ).fetchall()
    bindings = connection.execute(
        "SELECT phase_id,partition_digest FROM k0b02_publication_phase_bindings WHERE publication_id=?",
        (request["publication_id"],),
    ).fetchall()
    connection.close()
    assert len(attempts) == 1 and attempts[0][0].startswith("terminal_")
    assert attempts[0][1] == recovered["git_commit"]
    assert bindings == [(request["phase_id"], request["partition_digest"])]
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
    checkpoint = bundle["repository"] / runtime_values()["checkpoint_path"]
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
        for path in runtime_values()["pair_paths"]:
            file_raw = (bundle["repository"] / path).read_bytes()
            blob_raw = _blob(bundle["repository"], result["git_commit"], path)
            assert file_raw == blob_raw and sha256(file_raw) == sha256(blob_raw)
    ordered = sorted(elapsed)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    assert p95 < 10.0


def test_source_cut_blocks_new_admission_but_allows_original_readback() -> None:
    case_id = "source_cut_admission_fence"
    bundle = ready_pair(case_id)
    request = publication_request(bundle)

    def stop(boundary: str) -> None:
        if boundary == "backup_verified":
            raise ProcessLoss(boundary)

    with pytest.raises(ProcessLoss):
        publish(
            bundle["store"], bundle["database"], bundle["repository"], request, stop
        )
    duplicate = admit(bundle["database"], intent(case_id))
    assert duplicate["result"] == "duplicate_original"
    successor = intent(case_id, 2)
    successor["decision_version_id"] = "decision-source-cut-successor"
    successor["stable_identity"] = successor["decision_version_id"]
    successor["idempotency_key"] = "run-source_cut_admission_fence|successor|2"
    with pytest.raises(ContractError, match="source_cut"):
        admit(bundle["database"], successor)
    record("source_cut_admission_fence")


def test_publication_phase_binding_drift_blocks_terminal_readback() -> None:
    bundle, request, result = published("publication_phase_binding_drift")
    connection = sqlite3.connect(bundle["database"])
    connection.execute(
        "UPDATE k0b02_publication_phase_bindings SET partition_digest=? WHERE publication_id=?",
        ("9" * 64, request["publication_id"]),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ContractError, match="phase_binding"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert _git(bundle["repository"], "rev-parse", "HEAD") == result["git_commit"]
    record("publication_phase_binding_drift")


def test_publication_attempt_drift_blocks_terminal_readback() -> None:
    bundle, request, result = published("publication_attempt_drift")
    connection = sqlite3.connect(bundle["database"])
    connection.execute(
        "UPDATE k0b02_publication_attempts SET boundary='begun' WHERE publication_id=?",
        (request["publication_id"],),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ContractError, match="attempt_terminal"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert _git(bundle["repository"], "rev-parse", "HEAD") == result["git_commit"]
    record("publication_attempt_drift")


def test_exact_footer_matching_is_literal_unique_and_first_parent_only() -> None:
    bundle = ready_pair("exact_footer_identity")
    repository = bundle["repository"]
    unrelated = repository / "unrelated.txt"
    unrelated.write_bytes(b"decoy\n")
    run_git(repository, "add", "--", "unrelated.txt")
    run_git(
        repository,
        "commit",
        "--no-gpg-sign",
        "-m",
        "decoy\n\nPipeline-Checkpoint-Publication-ID: publication-v10",
    )
    assert _known_commit(repository, "publication-v1") is None
    metachar = "publication-[v1].*"
    unrelated.write_bytes(b"literal\n")
    run_git(repository, "add", "--", "unrelated.txt")
    run_git(
        repository,
        "commit",
        "--no-gpg-sign",
        "-m",
        "literal\n\nPipeline-Checkpoint-Publication-ID: " + metachar,
    )
    assert _known_commit(repository, metachar) == _git(repository, "rev-parse", "HEAD")
    run_git(repository, "checkout", "-b", "unrelated-footer-branch")
    unrelated.write_bytes(b"branch-only\n")
    run_git(repository, "add", "--", "unrelated.txt")
    run_git(
        repository,
        "commit",
        "--no-gpg-sign",
        "-m",
        "branch-only\n\nPipeline-Checkpoint-Publication-ID: branch-only-id",
    )
    run_git(repository, "checkout", "main")
    assert _known_commit(repository, "branch-only-id") is None
    unrelated.write_bytes(b"duplicate\n")
    run_git(repository, "add", "--", "unrelated.txt")
    run_git(
        repository,
        "commit",
        "--no-gpg-sign",
        "-m",
        "duplicate\n\nPipeline-Checkpoint-Publication-ID: duplicate-id\nPipeline-Checkpoint-Publication-ID: duplicate-id",
    )
    with pytest.raises(ContractError, match="ambiguous_footer"):
        _known_commit(repository, "duplicate-id")
    record("exact_footer_identity")


def test_ambient_git_environment_cannot_redirect_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = ready_pair("closed_git_environment")
    monkeypatch.setenv("GIT_DIR", str(bundle["root"] / "missing.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(bundle["root"] / "wrong-worktree"))
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'core.hooksPath=owned'")
    assert (
        Path(_git(bundle["repository"], "rev-parse", "--show-toplevel"))
        == bundle["repository"]
    )
    record("closed_git_environment")
