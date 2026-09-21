from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from .canonical import ContractError, json_bytes, require, sha256
from .publisher import CHECKPOINT_PATH, PAIR_PATHS, _git, verify_git_policy


def _run(*args: str) -> None:
    result = subprocess.run(
        list(args),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise ContractError("replay:git:" + result.stderr.decode("utf-8", "replace"))


def clone_only_restore(
    producer: Path,
    clone: Path,
    restore_target: Path,
    expected_envelope_sha256: str,
) -> dict[str, Any]:
    require(
        producer.is_absolute() and clone.is_absolute() and restore_target.is_absolute(),
        "replay:absolute",
    )
    require(not clone.exists() and not restore_target.exists(), "replay:new_targets")
    _run(
        "git",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.eol=lf",
        "clone",
        "--no-hardlinks",
        "--no-checkout",
        str(producer),
        str(clone),
    )
    _git(clone, "config", "--local", "core.autocrlf", "false")
    _git(clone, "config", "--local", "core.eol", "lf")
    _git(clone, "config", "--local", "commit.gpgsign", "false")
    _git(clone, "config", "--local", "tag.gpgsign", "false")
    _git(clone, "config", "--local", "core.hooksPath", "NUL")
    _git(clone, "config", "--local", "user.name", "K0b02 Fixture")
    _git(clone, "config", "--local", "user.email", "k0b02-fixture@example.invalid")
    require(_git(clone, "remote") == "origin", "replay:clone_origin")
    _git(clone, "remote", "remove", "origin")
    verify_git_policy(clone)
    _git(clone, "checkout", "--force", "HEAD")
    envelope_path = clone / ".pipeline/replay/invocation-envelope.json"
    require(envelope_path.is_file(), "replay:missing_envelope")
    envelope_raw = envelope_path.read_bytes()
    require(
        sha256(envelope_raw) == expected_envelope_sha256, "replay:envelope_mutation"
    )
    envelope = json.loads(envelope_raw)
    require(
        "source_seq" not in envelope and "checkpoint_and_pair_hashes" not in envelope,
        "replay:mutable_cut_in_seed",
    )
    checkpoint = clone / CHECKPOINT_PATH
    require(checkpoint.is_file(), "replay:missing_checkpoint")
    connection = sqlite3.connect(checkpoint)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        require(
            connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "replay:corrupt_checkpoint",
        )
        require(
            not list(connection.execute("PRAGMA foreign_key_check")),
            "replay:foreign_keys",
        )
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        require(version == 6, "replay:incompatible_schema")
        row = connection.execute(
            "SELECT publication_id,source_seq,ready_pair_set_sha256 FROM k0b02_publication_intents WHERE status='begun' ORDER BY source_seq DESC LIMIT 1"
        ).fetchone()
        require(row is not None, "replay:publication_cut")
    finally:
        connection.close()
    pair_hashes = []
    for path in PAIR_PATHS:
        raw = (clone / path).read_bytes()
        blob = _git(clone, "rev-parse", "HEAD:" + path)
        blob_raw = subprocess.run(
            ["git", "-C", str(clone), "cat-file", "blob", blob],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        require(raw == blob_raw, "replay:blob_file_drift")
        pair_hashes.append(sha256(raw))
    message = _git(clone, "log", "-1", "--format=%B")
    require(
        "Pipeline-Checkpoint-Publication-ID: " + row[0] in message
        and "Pipeline-Checkpoint-Source-Sequence: " + str(row[1]) in message
        and "Pipeline-Checkpoint-Snapshot-SHA256: " + sha256(checkpoint.read_bytes())
        in message
        and "Pipeline-Checkpoint-Pair-Set-SHA256: " + row[2] in message,
        "replay:footer_cut",
    )
    restore_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checkpoint, restore_target)
    restored = sqlite3.connect(restore_target)
    try:
        require(
            restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "replay:restored_integrity",
        )
    finally:
        restored.close()
    content = {
        "checkpoint_sha256": sha256(checkpoint.read_bytes()),
        "pair_hashes": pair_hashes,
        "source_seq": row[1],
        "publication_id": row[0],
        "ready_pair_set_sha256": row[2],
    }
    return {
        "result": "pass",
        "envelope_id": envelope["envelope_id"],
        "envelope_complete_file_sha256": expected_envelope_sha256,
        "checkpoint_and_pair_hashes": [content["checkpoint_sha256"], *pair_hashes],
        "source_seq": row[1],
        "new_restore_target": str(restore_target),
        "verified_content_digest": sha256(json_bytes(content)),
        "reproducibility_gap": "none_fixture_clone_only_no_stochastic_rerun",
        "git_policy": verify_git_policy(clone),
    }
