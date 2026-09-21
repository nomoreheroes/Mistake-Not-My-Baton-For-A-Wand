from __future__ import annotations

import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import ContractError, json_bytes, require, sha256
from .store import K0b02Store


PAIR_PATHS = (
    ".pipeline/projections/fixture-decision.yaml",
    ".pipeline/projections/fixture-decision.md",
)
CHECKPOINT_PATH = ".pipeline/history/pipeline-checkpoint.sqlite3"
CHECKPOINT_TEMP_PATH = ".pipeline/history/.pipeline-checkpoint.sqlite3.tmp"
PUBLICATION_PATHS = (CHECKPOINT_PATH, *PAIR_PATHS)


def _git(repo: Path, *args: str, check: bool = True) -> str:
    command = [
        "git",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.eol=lf",
        "-C",
        str(repo),
        *args,
    ]
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        raise ContractError("git:" + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout.decode("utf-8", "strict").strip()


def verify_git_policy(repo: Path) -> dict[str, Any]:
    require(repo.is_absolute() and (repo / ".git").is_dir(), "git:repository")
    require(
        _git(repo, "config", "--local", "--get", "core.autocrlf") == "false",
        "git:autocrlf",
    )
    require(_git(repo, "config", "--local", "--get", "core.eol") == "lf", "git:eol")
    require(
        _git(repo, "config", "--local", "--get", "commit.gpgsign") == "false",
        "git:commit_signing",
    )
    require(
        _git(repo, "config", "--local", "--get", "tag.gpgsign") == "false",
        "git:tag_signing",
    )
    require(
        _git(repo, "config", "--local", "--get", "core.hooksPath") == "NUL", "git:hooks"
    )
    require(
        bool(_git(repo, "config", "--local", "--get", "user.name")), "git:user_name"
    )
    require(
        bool(_git(repo, "config", "--local", "--get", "user.email")), "git:user_email"
    )
    require(not _git(repo, "remote"), "git:remote")
    for path in PAIR_PATHS:
        attrs = _git(
            repo,
            "check-attr",
            "text",
            "eol",
            "filter",
            "working-tree-encoding",
            "--",
            path,
        )
        require(
            all(line.endswith(": unspecified") for line in attrs.splitlines()),
            "git:transforming_attribute",
        )
    return {
        "core.autocrlf": "false",
        "core.eol": "lf",
        "hooks_path": "NUL",
        "remote_count": 0,
        "pair_attributes": "unspecified",
    }


def _known_commit(repo: Path, publication_id: str) -> str | None:
    value = _git(
        repo,
        "log",
        "--all",
        "-1",
        "--format=%H",
        "--grep=Pipeline-Checkpoint-Publication-ID: " + publication_id,
        check=False,
    )
    return value or None


def _blob_raw(repo: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", commit + ":" + path],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(result.returncode == 0, "publication:missing_blob")
    return result.stdout


def _verified_snapshot(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        require(
            connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "publication:snapshot_integrity",
        )
        require(
            not list(connection.execute("PRAGMA foreign_key_check")),
            "publication:snapshot_foreign_keys",
        )
        require(
            connection.execute("PRAGMA user_version").fetchone()[0] == 6,
            "publication:snapshot_schema",
        )
    finally:
        connection.close()
    raw = path.read_bytes()
    return {"sha256": sha256(raw), "bytes": len(raw), "user_version": 6}


def _record_result(
    database: Path,
    request: dict[str, Any],
    commit: str,
    tree: str,
    snapshot_sha: str,
    snapshot_bytes: int,
    recovered: bool,
) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    try:
        existing = connection.execute(
            "SELECT git_commit,git_tree,snapshot_sha256,snapshot_bytes,receipt_seq FROM k0b02_publication_results WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchone()
        if existing:
            require(
                existing[0] == commit and existing[2] == snapshot_sha,
                "publication:conflicting_result",
            )
            return {
                "result": "original",
                "publication_id": request["publication_id"],
                "git_commit": existing[0],
                "git_tree": existing[1],
                "snapshot_sha256": existing[2],
                "snapshot_bytes": existing[3],
                "receipt_seq": existing[4],
            }
        connection.execute("BEGIN IMMEDIATE")
        high = (
            connection.execute(
                "SELECT receipt_high_water FROM k0b02_source_sequences WHERE run_id=?",
                (request["run_id"],),
            ).fetchone()[0]
            + 1
        )
        connection.execute(
            "UPDATE k0b02_source_sequences SET receipt_high_water=? WHERE run_id=?",
            (high, request["run_id"]),
        )
        connection.execute(
            "INSERT INTO k0b02_publication_results(publication_id,snapshot_sha256,snapshot_bytes,git_commit,git_tree,predecessor_commit,result,receipt_seq,created_at) VALUES(?,?,?,?,?,?,'committed',?,?)",
            (
                request["publication_id"],
                snapshot_sha,
                snapshot_bytes,
                commit,
                tree,
                request["expected_Git_parent"],
                high,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.execute(
            "UPDATE k0b02_publication_intents SET status='committed' WHERE publication_id=?",
            (request["publication_id"],),
        )
        connection.commit()
        return {
            "result": "recovered" if recovered else "committed",
            "publication_id": request["publication_id"],
            "git_commit": commit,
            "git_tree": tree,
            "snapshot_sha256": snapshot_sha,
            "snapshot_bytes": snapshot_bytes,
            "receipt_seq": high,
        }
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def publish(
    store: K0b02Store,
    database: Path,
    repository: Path,
    request: dict[str, Any],
    observer: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    policy = verify_git_policy(repository)
    require(
        request["checkpoint_target"] == CHECKPOINT_PATH, "publication:checkpoint_target"
    )
    require(
        _git(repository, "rev-parse", "HEAD") == request["expected_Git_parent"]
        or _known_commit(repository, request["publication_id"]) is not None,
        "publication:parent",
    )
    connection = K0b02Store.connect(database)
    try:
        previous = connection.execute(
            "SELECT git_commit,git_tree,snapshot_sha256,snapshot_bytes,receipt_seq FROM k0b02_publication_results WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchone()
        if previous:
            checkpoint = repository / CHECKPOINT_PATH
            require(
                checkpoint.is_file()
                and sha256(checkpoint.read_bytes()) == previous[2]
                and sha256(_blob_raw(repository, previous[0], CHECKPOINT_PATH))
                == previous[2],
                "publication:terminal_checkpoint_drift",
            )
            return {
                "result": "original",
                "publication_id": request["publication_id"],
                "git_commit": previous[0],
                "git_tree": previous[1],
                "snapshot_sha256": previous[2],
                "snapshot_bytes": previous[3],
                "receipt_seq": previous[4],
            }
        dirty = {
            line[3:]
            for line in _git(
                repository, "status", "--porcelain=v1", "--untracked-files=all"
            ).splitlines()
            if len(line) >= 4
        }
        require(
            dirty <= {*PUBLICATION_PATHS, CHECKPOINT_TEMP_PATH},
            "publication:dirty_tree",
        )
        intent = connection.execute(
            "SELECT status FROM k0b02_publication_intents WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchone()
        pair = connection.execute(
            "SELECT projection_id,yaml_sha256,markdown_sha256,source_seq,projection_profile_sha256 FROM k0b02_projection_pairs WHERE ready=1 AND source_seq<=? ORDER BY source_seq DESC LIMIT 1",
            (request["source_seq"],),
        ).fetchone()
        require(
            pair is not None and pair[3] == request["source_seq"],
            "publication:ready_cut",
        )
        unresolved = connection.execute(
            "SELECT COUNT(*) FROM k0b02_projection_outbox WHERE source_seq<=? AND status NOT IN ('written','failed')",
            (request["source_seq"],),
        ).fetchone()[0]
        require(unresolved == 0, "publication:unresolved_outbox")
        pair_set_sha = sha256(
            json_bytes(
                {
                    "projection_id": pair[0],
                    "yaml_sha256": pair[1],
                    "markdown_sha256": pair[2],
                    "source_seq": pair[3],
                }
            )
        )
        require(
            pair_set_sha == request["ready_pair_set_sha256"], "publication:pair_set"
        )
        require(
            sha256((repository / PAIR_PATHS[0]).read_bytes()) == pair[1]
            and sha256((repository / PAIR_PATHS[1]).read_bytes()) == pair[2],
            "publication:pair_files",
        )
        if not intent:
            connection.execute(
                "INSERT INTO k0b02_publication_intents(publication_id,run_id,phase_id,partition_digest,source_seq,receipt_high_water,outbox_high_water,ready_pair_set_sha256,expected_git_parent,predecessor_publication_id,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,'begun',?)",
                (
                    request["publication_id"],
                    request["run_id"],
                    request["phase_id"],
                    request["partition_digest"],
                    request["source_seq"],
                    request["receipt_high_water"],
                    request["outbox_high_water"],
                    pair_set_sha,
                    request["expected_Git_parent"],
                    request["predecessor_publication_id"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    finally:
        connection.close()
    known = _known_commit(repository, request["publication_id"])
    checkpoint = repository / CHECKPOINT_PATH
    if known:
        raw = checkpoint.read_bytes()
        require(
            sha256(_blob_raw(repository, known, CHECKPOINT_PATH)) == sha256(raw),
            "publication:known_checkpoint_drift",
        )
        tree = _git(repository, "show", "-s", "--format=%T", known)
        return _record_result(
            database, request, known, tree, sha256(raw), len(raw), True
        )
    require(
        _git(repository, "rev-parse", "HEAD") == request["expected_Git_parent"],
        "publication:ambiguous_begun_effect",
    )
    candidate = repository / CHECKPOINT_TEMP_PATH
    snapshot = (
        _verified_snapshot(candidate)
        if candidate.exists()
        else store.snapshot(database, candidate)
    )
    if observer:
        observer("backup_verified")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    os.replace(candidate, checkpoint)
    if observer:
        observer("snapshot_replaced")
    require(
        sha256(checkpoint.read_bytes()) == snapshot["sha256"],
        "publication:snapshot_readback",
    )
    message = (
        "fixture checkpoint publication\n\n"
        + "Pipeline-Checkpoint-Publication-ID: "
        + request["publication_id"]
        + "\n"
        + "Pipeline-Checkpoint-Source-Sequence: "
        + str(request["source_seq"])
        + "\n"
        + "Pipeline-Checkpoint-Snapshot-SHA256: "
        + snapshot["sha256"]
        + "\n"
        + "Pipeline-Checkpoint-Profile-SHA256: "
        + request["projection_profile_sha256"]
        + "\n"
        + "Pipeline-Checkpoint-Pair-Set-SHA256: "
        + request["ready_pair_set_sha256"]
        + "\n"
        + "Pipeline-Checkpoint-Predecessor: "
        + (request["predecessor_publication_id"] or "none")
        + "\n"
    )
    _git(repository, "add", "--", *PUBLICATION_PATHS)
    staged = tuple(
        x for x in _git(repository, "diff", "--cached", "--name-only").splitlines() if x
    )
    require(
        len(staged) == 3 and set(staged) == set(PUBLICATION_PATHS),
        "publication:exact_paths",
    )
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )
    command = [
        "git",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.eol=lf",
        "-C",
        str(repository),
        "commit",
        "--no-gpg-sign",
        "-m",
        message,
    ]
    result = subprocess.run(
        command,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(result.returncode == 0, "publication:Git_commit")
    commit = _git(repository, "rev-parse", "HEAD")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    require(
        _known_commit(repository, request["publication_id"]) == commit,
        "publication:footer_readback",
    )
    for path, expected in zip(PAIR_PATHS, (pair[1], pair[2])):
        blob = _git(repository, "rev-parse", "HEAD:" + path)
        blob_raw = subprocess.run(
            ["git", "-C", str(repository), "cat-file", "blob", blob],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        require(
            sha256(blob_raw) == expected
            and sha256((repository / path).read_bytes()) == expected,
            "publication:blob_worktree",
        )
    if observer:
        observer("coordination_Git_commit_before_DB_result")
    result_data = _record_result(
        database, request, commit, tree, snapshot["sha256"], snapshot["bytes"], False
    )
    if observer:
        observer("publication_DB_result")
    result_data["git_policy"] = policy
    return result_data
