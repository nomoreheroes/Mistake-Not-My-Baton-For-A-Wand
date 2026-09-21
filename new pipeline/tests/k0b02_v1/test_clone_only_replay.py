from __future__ import annotations

import json
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
    run_git,
    sha256,
)
from k0b02_v1.publisher import CHECKPOINT_PATH, PAIR_PATHS, _git
from k0b02_v1.replay import clone_only_restore


def _commit(repository, *paths):
    run_git(repository, "add", "--", *paths)
    result = run_git(
        repository, "commit", "--no-gpg-sign", "-m", "negative replay fixture"
    )
    assert result.returncode == 0


def _restore(case_id: str):
    bundle, request, publication = published(case_id)
    clone = bundle["root"] / "coord-clone"
    target = bundle["root"] / "restored.sqlite3"
    result = clone_only_restore(
        bundle["repository"], clone, target, bundle["envelope_sha256"]
    )
    return bundle, publication, clone, target, result


def test_clone_only_restore_and_actual_blob_file_invariance() -> None:
    bundle, publication, clone, target, result = _restore("clone_only_restore")
    assert result["result"] == "pass" and target.is_file()
    assert _git(clone, "remote") == ""
    for path in PAIR_PATHS:
        raw = (clone / path).read_bytes()
        blob = subprocess.run(
            ["git", "-C", str(clone), "show", "HEAD:" + path],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        assert raw == blob and sha256(raw) == sha256(blob)
    record("clone_only_restore", restored_sha256=sha256(target.read_bytes()))


@pytest.mark.parametrize(
    "case_id",
    (
        "replay_corrupt_checkpoint",
        "replay_incompatible_schema",
        "replay_missing_envelope",
    ),
)
def test_replay_corruption_schema_and_envelope_blocks(case_id: str) -> None:
    bundle, request, publication = published(case_id)
    repo = bundle["repository"]
    if case_id == "replay_corrupt_checkpoint":
        path = repo / CHECKPOINT_PATH
        path.write_bytes(b"not a sqlite database\n")
        _commit(repo, CHECKPOINT_PATH)
        match = "corrupt_checkpoint"
    elif case_id == "replay_incompatible_schema":
        path = repo / CHECKPOINT_PATH
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA user_version=5")
        connection.close()
        _commit(repo, CHECKPOINT_PATH)
        match = "incompatible_schema"
    else:
        run_git(repo, "rm", "--", ".pipeline/replay/invocation-envelope.json")
        run_git(repo, "commit", "--no-gpg-sign", "-m", "missing envelope fixture")
        match = "missing_envelope"
    with pytest.raises(
        (ContractError, sqlite3.DatabaseError),
        match=match if case_id != "replay_corrupt_checkpoint" else None,
    ):
        clone_only_restore(
            repo,
            bundle["root"] / "coord-clone",
            bundle["root"] / "restored.sqlite3",
            bundle["envelope_sha256"],
        )
    record(case_id)


def test_checkpoint_cut_is_external_to_immutable_seed() -> None:
    bundle, publication, clone, target, result = _restore(
        "replay_checkpoint_cut_over_immutable_seed"
    )
    seed = json.loads(
        (clone / ".pipeline/replay/invocation-envelope.json").read_bytes()
    )
    assert "source_seq" not in seed and "checkpoint_and_pair_hashes" not in seed
    assert result["source_seq"] == 1
    assert result["envelope_complete_file_sha256"] == bundle["envelope_sha256"]
    record("replay_checkpoint_cut_over_immutable_seed")


def test_fixture_git_config_drift_blocks_before_mutation() -> None:
    bundle = ready_pair("fixture_git_config_drift")
    request = publication_request(bundle)
    run_git(bundle["repository"], "config", "--local", "core.autocrlf", "true")
    head = _git(bundle["repository"], "rev-parse", "HEAD")
    before = bundle["database"].read_bytes()
    with pytest.raises(ContractError, match="git:autocrlf"):
        publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert _git(bundle["repository"], "rev-parse", "HEAD") == head
    assert bundle["database"].read_bytes() == before
    record("fixture_git_config_drift")


def test_twelve_isolated_clone_only_restore_samples() -> None:
    elapsed = []
    for number in range(1, 13):
        case_id = f"restore_performance_{number:02d}"
        (_, _, _, target, result), duration = measured(
            case_id, lambda case_id=case_id: _restore(case_id)
        )
        elapsed.append(duration)
        assert result["result"] == "pass" and target.is_file()
    p95 = sorted(elapsed)[math.ceil(0.95 * len(elapsed)) - 1]
    assert p95 < 120.0
