from __future__ import annotations

import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import ContractError, json_bytes, require, sha256
from .store import K0b02Store, runtime_profile


def _closed_git_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    admitted = {
        "systemroot",
        "windir",
        "comspec",
        "path",
        "pathext",
        "temp",
        "tmp",
    }
    environment = {
        key: value for key, value in os.environ.items() if key.lower() in admitted
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    if extra:
        require(
            set(extra) <= {"GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"},
            "git:environment_extra",
        )
        environment.update(extra)
    require(
        not any(
            key.upper()
            in {
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_CONFIG_PARAMETERS",
                "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            }
            for key in environment
        ),
        "git:environment_closed",
    )
    return environment


def _git_process(
    command: list[str], *, check: bool = True, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        env=_closed_git_environment(extra_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        raise ContractError("git:" + result.stderr.decode("utf-8", "replace").strip())
    return result


def _git(repo: Path, *args: str, check: bool = True) -> str:
    result = _git_process(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "-C",
            str(repo),
            *args,
        ],
        check=check,
    )
    return result.stdout.decode("utf-8", "strict").strip()


def _git_bytes(repo: Path, *args: str, check: bool = True) -> bytes:
    return _git_process(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "-C",
            str(repo),
            *args,
        ],
        check=check,
    ).stdout


def verify_git_policy(repo: Path, pair_paths: list[str]) -> dict[str, Any]:
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
        _git(repo, "config", "--local", "--get", "core.hooksPath") == "NUL",
        "git:hooks",
    )
    require(
        bool(_git(repo, "config", "--local", "--get", "user.name")), "git:user_name"
    )
    require(
        bool(_git(repo, "config", "--local", "--get", "user.email")),
        "git:user_email",
    )
    require(not _git(repo, "remote"), "git:remote")
    for path in pair_paths:
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
        "environment": "closed",
    }


def _trailers(message: str) -> list[tuple[str, str]]:
    lines = message.replace("\r\n", "\n").split("\n")
    while lines and not lines[-1]:
        lines.pop()
    block: list[str] = []
    for line in reversed(lines):
        if not line or ": " not in line:
            break
        block.append(line)
    result = []
    for line in reversed(block):
        key, value = line.split(": ", 1)
        if key and value:
            result.append((key, value))
    return result


def _known_commit(repo: Path, publication_id: str) -> str | None:
    require(
        bool(publication_id)
        and "\n" not in publication_id
        and "\r" not in publication_id,
        "publication:ID",
    )
    candidates = [
        value
        for value in _git(repo, "rev-list", "--first-parent", "HEAD").splitlines()
        if value
    ]
    matches: list[str] = []
    key = "Pipeline-Checkpoint-Publication-ID"
    for commit in candidates:
        values = [
            value
            for name, value in _trailers(
                _git(repo, "show", "-s", "--format=%B", commit)
            )
            if name == key
        ]
        if publication_id in values:
            require(values == [publication_id], "publication:ambiguous_footer")
            matches.append(commit)
    require(len(matches) <= 1, "publication:ambiguous_footer")
    return matches[0] if matches else None


def _blob_raw(repo: Path, commit: str, path: str) -> bytes:
    result = _git_process(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "-C",
            str(repo),
            "show",
            commit + ":" + path,
        ],
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


def _attempt_boundary(
    database: Path,
    publication_id: str,
    boundary: str,
    *,
    marker_sha256: str | None = None,
    effect_commit: str | None = None,
) -> None:
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        changed = connection.execute(
            "UPDATE k0b02_publication_attempts SET boundary=?,durable_marker_sha256=COALESCE(?,durable_marker_sha256),effect_commit=COALESCE(?,effect_commit) WHERE publication_id=?",
            (boundary, marker_sha256, effect_commit, publication_id),
        ).rowcount
        require(changed == 1, "publication:attempt_singleton")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


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
        boundary = "terminal_recovered" if recovered else "terminal_committed"
        changed = connection.execute(
            "UPDATE k0b02_publication_attempts SET boundary=?,durable_marker_sha256=?,effect_commit=? WHERE publication_id=?",
            (boundary, snapshot_sha, commit, request["publication_id"]),
        ).rowcount
        require(changed == 1, "publication:attempt_singleton")
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
    connection = K0b02Store.connect(database)
    try:
        profile = runtime_profile(connection)
    finally:
        connection.close()
    pair_paths = profile["pair_paths"]
    checkpoint_path = profile["checkpoint_path"]
    checkpoint_target = repository / checkpoint_path
    checkpoint_temp = checkpoint_target.with_name("." + checkpoint_target.name + ".tmp")
    checkpoint_temp_path = checkpoint_temp.relative_to(repository).as_posix()
    publication_paths = [checkpoint_path, *pair_paths]
    policy = verify_git_policy(repository, pair_paths)
    require(
        request["checkpoint_target"] == checkpoint_path,
        "publication:checkpoint_target",
    )
    known = _known_commit(repository, request["publication_id"])
    require(
        _git(repository, "rev-parse", "HEAD") == request["expected_Git_parent"]
        or known is not None,
        "publication:parent",
    )
    connection = K0b02Store.connect(database)
    try:
        previous = connection.execute(
            "SELECT git_commit,git_tree,snapshot_sha256,snapshot_bytes,receipt_seq FROM k0b02_publication_results WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchone()
        if previous:
            binding = connection.execute(
                "SELECT phase_id,partition_digest FROM k0b02_publication_phase_bindings WHERE publication_id=?",
                (request["publication_id"],),
            ).fetchall()
            require(
                checkpoint_target.is_file()
                and sha256(checkpoint_target.read_bytes()) == previous[2]
                and sha256(_blob_raw(repository, previous[0], checkpoint_path))
                == previous[2],
                "publication:terminal_checkpoint_drift",
            )
            require(
                binding == [(request["phase_id"], request["partition_digest"])]
                and request["phase_id"] in profile["phases"],
                "publication:phase_binding",
            )
            attempts = connection.execute(
                "SELECT boundary,durable_marker_sha256,effect_commit FROM k0b02_publication_attempts WHERE publication_id=?",
                (request["publication_id"],),
            ).fetchall()
            require(
                len(attempts) == 1
                and attempts[0][0].startswith("terminal_")
                and attempts[0][1] == previous[2]
                and attempts[0][2] == previous[0],
                "publication:attempt_terminal",
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
            dirty <= {*publication_paths, checkpoint_temp_path},
            "publication:dirty_tree",
        )
        intent = connection.execute(
            "SELECT run_id,phase_id,partition_digest,source_seq,status FROM k0b02_publication_intents WHERE publication_id=?",
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
            sha256((repository / pair_paths[0]).read_bytes()) == pair[1]
            and sha256((repository / pair_paths[1]).read_bytes()) == pair[2],
            "publication:pair_files",
        )
        connection.execute("BEGIN IMMEDIATE")
        if intent is None:
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
            connection.execute(
                "INSERT INTO k0b02_publication_phase_bindings(publication_id,phase_id,partition_digest) VALUES(?,?,?)",
                (
                    request["publication_id"],
                    request["phase_id"],
                    request["partition_digest"],
                ),
            )
        else:
            require(
                intent[:4]
                == (
                    request["run_id"],
                    request["phase_id"],
                    request["partition_digest"],
                    request["source_seq"],
                )
                and intent[4] == "begun",
                "publication:intent_drift",
            )
        binding = connection.execute(
            "SELECT phase_id,partition_digest FROM k0b02_publication_phase_bindings WHERE publication_id=?",
            (request["publication_id"],),
        ).fetchall()
        require(
            binding == [(request["phase_id"], request["partition_digest"])]
            and request["phase_id"] in profile["phases"],
            "publication:phase_binding",
        )
        attempts = connection.execute(
            "SELECT attempt_id FROM k0b02_publication_attempts WHERE publication_id=? ORDER BY attempt_id",
            (request["publication_id"],),
        ).fetchall()
        if not attempts:
            require(profile["projection_attempt_cap"] >= 1, "publication:attempt_cap")
            connection.execute(
                "INSERT INTO k0b02_publication_attempts(attempt_id,publication_id,boundary,durable_marker_sha256,effect_commit,created_at) VALUES(?,?,'begun',?,NULL,?)",
                (
                    request["publication_id"] + "-attempt-1",
                    request["publication_id"],
                    sha256(json_bytes(request)),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        else:
            require(
                len(attempts) == 1 and profile["projection_attempt_cap"] == 1,
                "publication:attempt_cap",
            )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    known = _known_commit(repository, request["publication_id"])
    if known:
        raw = checkpoint_target.read_bytes()
        require(
            sha256(_blob_raw(repository, known, checkpoint_path)) == sha256(raw),
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
    snapshot = (
        _verified_snapshot(checkpoint_temp)
        if checkpoint_temp.exists()
        else store.snapshot(database, checkpoint_temp)
    )
    _attempt_boundary(
        database,
        request["publication_id"],
        "backup_verified",
        marker_sha256=snapshot["sha256"],
    )
    if observer:
        observer("backup_verified")
    checkpoint_target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(checkpoint_temp, checkpoint_target)
    _attempt_boundary(
        database,
        request["publication_id"],
        "snapshot_replaced",
        marker_sha256=snapshot["sha256"],
    )
    if observer:
        observer("snapshot_replaced")
    require(
        sha256(checkpoint_target.read_bytes()) == snapshot["sha256"],
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
    _git(repository, "add", "--", *publication_paths)
    staged = tuple(
        value
        for value in _git(repository, "diff", "--cached", "--name-only").splitlines()
        if value
    )
    require(
        len(staged) == 3 and set(staged) == set(publication_paths),
        "publication:exact_paths",
    )
    result = _git_process(
        [
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
        ],
        extra_env={
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        },
        check=False,
    )
    require(result.returncode == 0, "publication:Git_commit")
    commit = _git(repository, "rev-parse", "HEAD")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    require(
        _known_commit(repository, request["publication_id"]) == commit,
        "publication:footer_readback",
    )
    for path, expected in zip(pair_paths, (pair[1], pair[2])):
        blob_raw = _git_bytes(repository, "show", "HEAD:" + path)
        require(
            sha256(blob_raw) == expected
            and sha256((repository / path).read_bytes()) == expected,
            "publication:blob_worktree",
        )
    _attempt_boundary(
        database,
        request["publication_id"],
        "coordination_Git_commit_before_DB_result",
        marker_sha256=snapshot["sha256"],
        effect_commit=commit,
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
