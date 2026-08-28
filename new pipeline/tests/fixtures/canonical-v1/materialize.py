#!/usr/bin/env python3
"""Materialize the Pipeline v2 canonical fixture as a deterministic Git repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any


FIXTURE_ROOT = Path(__file__).resolve().parent
SPEC_PATH = FIXTURE_ROOT / "fixture-spec.json"
WINDOWS_RESERVED_NAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
SAFE_COMPONENT = re.compile(r"^[a-z0-9._-]+$")


class MaterializationError(RuntimeError):
    """Raised when an input or materialized repository fails closed."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"cannot read canonical JSON {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise MaterializationError(f"top-level JSON value must be an object: {path}")
    return parsed


def require_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise MaterializationError(f"{key} must be a non-empty string")
    return value


def validate_relative_path(raw_path: str) -> PurePosixPath:
    path = PurePosixPath(raw_path)
    if path.is_absolute() or str(path) != raw_path or "\\" in raw_path:
        raise MaterializationError(f"path is not canonical POSIX-relative: {raw_path!r}")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise MaterializationError(f"path contains an unsafe component: {raw_path!r}")
    for part in path.parts:
        if not SAFE_COMPONENT.fullmatch(part) or part.endswith((".", " ")):
            raise MaterializationError(f"path component is not Windows-safe: {part!r}")
        stem = part.split(".", 1)[0].casefold()
        if stem in WINDOWS_RESERVED_NAMES:
            raise MaterializationError(f"path component uses a reserved Windows name: {part!r}")
    return path


def git_environment(spec: dict[str, Any]) -> dict[str, str]:
    git_spec = spec.get("git")
    if not isinstance(git_spec, dict):
        raise MaterializationError("git must be an object")
    timestamp = git_spec.get("timestamp_unix")
    timezone = require_string(git_spec, "timezone")
    if not isinstance(timestamp, int) or timestamp < 0:
        raise MaterializationError("git.timestamp_unix must be a non-negative integer")
    if not re.fullmatch(r"[+-][0-9]{4}", timezone):
        raise MaterializationError("git.timezone must have the form +HHMM or -HHMM")

    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": require_string(git_spec, "author_name"),
            "GIT_AUTHOR_EMAIL": require_string(git_spec, "author_email"),
            "GIT_AUTHOR_DATE": f"@{timestamp} {timezone}",
            "GIT_COMMITTER_NAME": require_string(git_spec, "committer_name"),
            "GIT_COMMITTER_EMAIL": require_string(git_spec, "committer_email"),
            "GIT_COMMITTER_DATE": f"@{timestamp} {timezone}",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
    )
    return environment


def run_git(
    repository: Path,
    environment: dict[str, str],
    *arguments: str,
) -> str:
    command = ["git", "-C", str(repository), *arguments]
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
    except FileNotFoundError as exc:
        raise MaterializationError("git executable is unavailable") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise MaterializationError(f"git command failed ({' '.join(arguments)}): {stderr}") from exc
    return result.stdout.decode("ascii").strip()


def validate_spec(expected_spec_sha256: str | None) -> tuple[dict[str, Any], Path, dict[str, Any], str]:
    spec_bytes = SPEC_PATH.read_bytes()
    spec_sha256 = sha256_bytes(spec_bytes)
    if expected_spec_sha256 is not None and spec_sha256 != expected_spec_sha256:
        raise MaterializationError(
            f"fixture spec SHA-256 mismatch: expected {expected_spec_sha256}, got {spec_sha256}"
        )
    spec = load_json(SPEC_PATH)
    if spec.get("schema_version") != 1:
        raise MaterializationError("unsupported fixture spec schema_version")

    materializer = spec.get("materializer")
    if not isinstance(materializer, dict):
        raise MaterializationError("materializer must be an object")
    if require_string(materializer, "path") != "materialize.py":
        raise MaterializationError("materializer.path must resolve to materialize.py")
    actual_materializer_hash = sha256_file(Path(__file__).resolve())
    expected_materializer_hash = require_string(materializer, "sha256")
    if actual_materializer_hash != expected_materializer_hash:
        raise MaterializationError(
            "materializer SHA-256 mismatch: "
            f"expected {expected_materializer_hash}, got {actual_materializer_hash}"
        )

    manifest_path = FIXTURE_ROOT / validate_relative_path(require_string(spec, "expected_tree_manifest"))
    actual_manifest_hash = sha256_file(manifest_path)
    expected_manifest_hash = require_string(spec, "expected_tree_manifest_sha256")
    if actual_manifest_hash != expected_manifest_hash:
        raise MaterializationError(
            f"expected-tree manifest SHA-256 mismatch: expected {expected_manifest_hash}, "
            f"got {actual_manifest_hash}"
        )
    manifest = load_json(manifest_path)
    return spec, manifest_path, manifest, spec_sha256


def validate_seed(spec: dict[str, Any], manifest: dict[str, Any]) -> tuple[Path, list[dict[str, str]]]:
    if manifest.get("schema_version") != 1:
        raise MaterializationError("unsupported expected-tree schema_version")
    if manifest.get("fixture_id") != spec.get("fixture_id"):
        raise MaterializationError("fixture_id differs between spec and expected-tree manifest")
    if manifest.get("fixture_version") != spec.get("fixture_version"):
        raise MaterializationError("fixture_version differs between spec and expected-tree manifest")

    seed_root = FIXTURE_ROOT / validate_relative_path(require_string(spec, "seed_root"))
    if not seed_root.is_dir() or seed_root.is_symlink():
        raise MaterializationError("seed_root must be a real directory")
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise MaterializationError("expected-tree entries must be a non-empty array")

    entries: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    seen_casefolded: set[str] = set()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise MaterializationError("each expected-tree entry must be an object")
        path_text = require_string(raw_entry, "path")
        validate_relative_path(path_text)
        if path_text in seen_paths or path_text.casefold() in seen_casefolded:
            raise MaterializationError(f"duplicate or case-colliding expected path: {path_text}")
        seen_paths.add(path_text)
        seen_casefolded.add(path_text.casefold())
        mode = require_string(raw_entry, "mode")
        digest = require_string(raw_entry, "sha256")
        if mode != "100644":
            raise MaterializationError(f"unsupported fixture mode for {path_text}: {mode}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise MaterializationError(f"invalid SHA-256 for {path_text}")
        entries.append({"path": path_text, "mode": mode, "sha256": digest})

    if [entry["path"] for entry in entries] != sorted(seen_paths):
        raise MaterializationError("expected-tree entries must be sorted by path")

    actual_paths: list[str] = []
    for candidate in seed_root.rglob("*"):
        if candidate.is_symlink():
            raise MaterializationError(f"symlinks are forbidden in canonical seed: {candidate}")
        if candidate.is_file():
            actual_paths.append(candidate.relative_to(seed_root).as_posix())
    if sorted(actual_paths) != sorted(seen_paths):
        missing = sorted(seen_paths - set(actual_paths))
        unexpected = sorted(set(actual_paths) - seen_paths)
        raise MaterializationError(f"seed tree mismatch: missing={missing}, unexpected={unexpected}")

    for entry in entries:
        source = seed_root / PurePosixPath(entry["path"])
        actual_digest = sha256_file(source)
        if actual_digest != entry["sha256"]:
            raise MaterializationError(
                f"seed SHA-256 mismatch for {entry['path']}: "
                f"expected {entry['sha256']}, got {actual_digest}"
            )
        if source.suffix in {".json", ".md", ".txt", ".yaml", ".yml"} or source.name in {
            ".gitattributes",
            ".gitignore",
        }:
            payload = source.read_bytes()
            if payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
                raise MaterializationError(f"text seed is not BOM-free LF: {entry['path']}")
    return seed_root, entries


def materialize(
    output: Path,
    expected_spec_sha256: str | None,
    expected_commit: str | None,
) -> dict[str, Any]:
    spec, manifest_path, manifest, spec_sha256 = validate_spec(expected_spec_sha256)
    seed_root, entries = validate_seed(spec, manifest)
    if output.exists():
        raise MaterializationError(f"output path already exists: {output}")

    output.mkdir(parents=True)
    for entry in entries:
        destination = output / PurePosixPath(entry["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(seed_root / PurePosixPath(entry["path"]), destination)
        os.chmod(destination, 0o644)

    git_spec = spec["git"]
    environment = git_environment(spec)
    object_format = require_string(git_spec, "object_format")
    initial_branch = require_string(git_spec, "initial_branch")
    run_git(
        output,
        environment,
        "init",
        "--quiet",
        f"--object-format={object_format}",
        f"--initial-branch={initial_branch}",
    )
    run_git(output, environment, "config", "--local", "core.autocrlf", "false")
    run_git(output, environment, "config", "--local", "core.filemode", "false")
    run_git(output, environment, "config", "--local", "commit.gpgsign", "false")
    run_git(output, environment, "add", "--all")

    tree_oid = run_git(output, environment, "write-tree")
    expected_tree_oid = require_string(manifest, "git_tree_oid")
    if tree_oid != expected_tree_oid:
        raise MaterializationError(
            f"fixture Git tree mismatch: expected {expected_tree_oid}, got {tree_oid}"
        )
    actual_object_format = run_git(output, environment, "rev-parse", "--show-object-format")
    if actual_object_format != object_format:
        raise MaterializationError(
            f"fixture Git object format mismatch: expected {object_format}, got {actual_object_format}"
        )

    commit_message = require_string(git_spec, "commit_message")
    declared_commit = require_string(git_spec, "expected_commit")
    if expected_commit is not None and expected_commit != declared_commit:
        raise MaterializationError(
            f"caller/spec fixture commit mismatch: caller {expected_commit}, spec {declared_commit}"
        )
    commit_oid = run_git(output, environment, "commit-tree", tree_oid, "-m", commit_message)
    if commit_oid != declared_commit:
        raise MaterializationError(
            f"fixture commit mismatch: expected {declared_commit}, got {commit_oid}"
        )
    run_git(output, environment, "update-ref", f"refs/heads/{initial_branch}", commit_oid)
    run_git(output, environment, "symbolic-ref", "HEAD", f"refs/heads/{initial_branch}")

    head_oid = run_git(output, environment, "rev-parse", "HEAD")
    head_tree_oid = run_git(output, environment, "rev-parse", "HEAD^{tree}")
    status = run_git(output, environment, "status", "--porcelain=v1")
    run_git(output, environment, "fsck", "--full", "--strict")
    if head_oid != commit_oid or head_tree_oid != tree_oid or status:
        raise MaterializationError("materialized fixture did not finish at a clean expected HEAD/tree")

    return {
        "fixture_commit": commit_oid,
        "fixture_id": spec.get("fixture_id"),
        "fixture_spec_sha256": spec_sha256,
        "fixture_tree": tree_oid,
        "manifest_path": manifest_path.name,
        "object_format": object_format,
        "status": "clean",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for the materialized fixture Git")
    parser.add_argument("--expected-spec-sha256", help="fail unless fixture-spec.json has this SHA-256")
    parser.add_argument("--expected-commit", help="fail unless the deterministic commit has this OID")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        result = materialize(
            arguments.output.resolve(),
            arguments.expected_spec_sha256,
            arguments.expected_commit,
        )
    except MaterializationError as exc:
        print(f"materialization failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
