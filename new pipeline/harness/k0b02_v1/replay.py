from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import json_bytes, require, sha256
from .publisher import (
    _git,
    _git_bytes,
    _git_process,
    _trailers,
    verify_git_policy,
)


def _verify_replay_rows(
    connection: sqlite3.Connection,
    expected_envelope: tuple[Any, ...],
    expected_result: tuple[Any, ...],
) -> None:
    envelopes = connection.execute(
        "SELECT envelope_id,envelope_sha256,envelope_json,run_chain_identity,partition_digest FROM k0b02_replay_envelopes"
    ).fetchall()
    results = connection.execute(
        "SELECT replay_id,envelope_id,publication_id,new_restore_target,verified_content_digest,reproducibility_gap,result FROM k0b02_replay_results"
    ).fetchall()
    require(
        envelopes == [expected_envelope] and results == [expected_result],
        "replay:durable_result",
    )


def clone_only_restore(
    producer: Path,
    clone: Path,
    restore_target: Path,
    expected_envelope_sha256: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    require(
        producer.is_absolute() and clone.is_absolute() and restore_target.is_absolute(),
        "replay:absolute",
    )
    require(not clone.exists() and not restore_target.exists(), "replay:new_targets")
    clone_result = _git_process(
        [
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
        ],
        check=False,
    )
    require(clone_result.returncode == 0, "replay:git:clone")
    _git(clone, "config", "--local", "core.autocrlf", "false")
    _git(clone, "config", "--local", "core.eol", "lf")
    _git(clone, "config", "--local", "commit.gpgsign", "false")
    _git(clone, "config", "--local", "tag.gpgsign", "false")
    _git(clone, "config", "--local", "core.hooksPath", "NUL")
    _git(clone, "config", "--local", "user.name", "K0b02 Fixture")
    _git(clone, "config", "--local", "user.email", "k0b02-fixture@example.invalid")
    require(_git(clone, "remote") == "origin", "replay:clone_origin")
    _git(clone, "remote", "remove", "origin")
    verify_git_policy(clone, profile["pair_paths"])
    _git(clone, "checkout", "--force", "HEAD")
    envelope_path = clone / profile["replay_envelope_path"]
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
    checkpoint = clone / profile["checkpoint_path"]
    require(checkpoint.is_file(), "replay:missing_checkpoint")
    checkpoint_raw = checkpoint.read_bytes()
    checkpoint_sha = sha256(checkpoint_raw)
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
            "SELECT publication_id,run_id,source_seq,ready_pair_set_sha256,expected_git_parent "
            "FROM k0b02_publication_intents WHERE status='begun' "
            "ORDER BY source_seq DESC LIMIT 1"
        ).fetchone()
        require(row is not None, "replay:publication_cut")
    finally:
        connection.close()
    pair_hashes = []
    for path in profile["pair_paths"]:
        raw = (clone / path).read_bytes()
        blob_raw = _git_bytes(clone, "show", "HEAD:" + path)
        require(raw == blob_raw, "replay:blob_file_drift")
        pair_hashes.append(sha256(raw))
    footer = dict(_trailers(_git(clone, "log", "-1", "--format=%B")))
    require(
        footer.get("Pipeline-Checkpoint-Publication-ID") == row[0]
        and footer.get("Pipeline-Checkpoint-Source-Sequence") == str(row[2])
        and footer.get("Pipeline-Checkpoint-Snapshot-SHA256") == checkpoint_sha
        and footer.get("Pipeline-Checkpoint-Pair-Set-SHA256") == row[3],
        "replay:footer_cut",
    )
    require(
        len(
            [
                value
                for key, value in _trailers(_git(clone, "log", "-1", "--format=%B"))
                if key == "Pipeline-Checkpoint-Publication-ID"
            ]
        )
        == 1,
        "replay:footer_ambiguity",
    )
    restore_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checkpoint, restore_target)
    content = {
        "checkpoint_sha256": checkpoint_sha,
        "pair_hashes": pair_hashes,
        "source_seq": row[2],
        "publication_id": row[0],
        "ready_pair_set_sha256": row[3],
    }
    verified_digest = sha256(json_bytes(content))
    commit = _git(clone, "rev-parse", "HEAD")
    tree = _git(clone, "rev-parse", "HEAD^{tree}")
    restored = sqlite3.connect(restore_target)
    try:
        restored.execute("PRAGMA foreign_keys=ON")
        restored.execute("BEGIN IMMEDIATE")
        high = (
            restored.execute(
                "SELECT receipt_high_water FROM k0b02_source_sequences WHERE run_id=?",
                (row[1],),
            ).fetchone()[0]
            + 1
        )
        restored.execute(
            "UPDATE k0b02_source_sequences SET receipt_high_water=? WHERE run_id=?",
            (high, row[1]),
        )
        restored.execute(
            "INSERT INTO k0b02_publication_results(publication_id,snapshot_sha256,snapshot_bytes,git_commit,git_tree,predecessor_commit,result,receipt_seq,created_at) VALUES(?,?,?,?,?,?,'committed',?,?)",
            (
                row[0],
                checkpoint_sha,
                len(checkpoint_raw),
                commit,
                tree,
                row[4],
                high,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        restored.execute(
            "UPDATE k0b02_publication_intents SET status='committed' WHERE publication_id=?",
            (row[0],),
        )
        restored.execute(
            "UPDATE k0b02_publication_attempts SET boundary='terminal_clone_recovered',durable_marker_sha256=?,effect_commit=? WHERE publication_id=?",
            (checkpoint_sha, commit, row[0]),
        )
        restored.execute(
            "INSERT INTO k0b02_replay_envelopes(envelope_id,envelope_sha256,envelope_json,run_chain_identity,partition_digest,created_at) VALUES(?,?,?,?,?,?)",
            (
                envelope["envelope_id"],
                expected_envelope_sha256,
                envelope_raw.decode("utf-8").strip(),
                envelope["run_chain_identity"],
                envelope["partition_digest"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        replay_id = (
            "replay-"
            + sha256(json_bytes([envelope["envelope_id"], row[0], verified_digest]))[
                :32
            ]
        )
        restored.execute(
            "INSERT INTO k0b02_replay_results(replay_id,envelope_id,publication_id,new_restore_target,verified_content_digest,reproducibility_gap,result,created_at) VALUES(?,?,?,?,?,?,'pass',?)",
            (
                replay_id,
                envelope["envelope_id"],
                row[0],
                str(restore_target),
                verified_digest,
                "none_fixture_clone_only_no_stochastic_rerun",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        expected_envelope = (
            envelope["envelope_id"],
            expected_envelope_sha256,
            envelope_raw.decode("utf-8").strip(),
            envelope["run_chain_identity"],
            envelope["partition_digest"],
        )
        expected_result = (
            replay_id,
            envelope["envelope_id"],
            row[0],
            str(restore_target),
            verified_digest,
            "none_fixture_clone_only_no_stochastic_rerun",
            "pass",
        )
        _verify_replay_rows(restored, expected_envelope, expected_result)
        restored.commit()
        require(
            restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "replay:restored_integrity",
        )
        _verify_replay_rows(restored, expected_envelope, expected_result)
    except BaseException:
        restored.rollback()
        raise
    finally:
        restored.close()
    return {
        "result": "pass",
        "envelope_id": envelope["envelope_id"],
        "envelope_complete_file_sha256": expected_envelope_sha256,
        "checkpoint_and_pair_hashes": [checkpoint_sha, *pair_hashes],
        "source_seq": row[2],
        "new_restore_target": str(restore_target),
        "verified_content_digest": verified_digest,
        "reproducibility_gap": "none_fixture_clone_only_no_stochastic_rerun",
        "git_policy": verify_git_policy(clone, profile["pair_paths"]),
    }
