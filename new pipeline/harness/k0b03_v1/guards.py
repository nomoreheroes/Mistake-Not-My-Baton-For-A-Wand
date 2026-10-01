from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from contract import ContractError, validate_invocation_envelope


FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class GuardError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def stat_is_reparse(info: os.stat_result | SimpleNamespace) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def _check_component(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or path.is_symlink():
        raise GuardError("PATH_SYMLINK", "symlink is forbidden")
    if stat_is_reparse(info):
        raise GuardError("PATH_REPARSE_POINT", "reparse point is forbidden")


def reject_reparse_ancestry(path: Path) -> None:
    absolute = path.absolute()
    existing: list[Path] = []
    current = absolute
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for component in reversed(existing):
        _check_component(component)


def guarded_repository_path(repository_root: Path, relative_path: str, *, output: bool = False) -> Path:
    if not repository_root.exists():
        raise GuardError("ROOT_MISSING", "repository root is missing")
    reject_reparse_ancestry(repository_root)
    raw = Path(relative_path)
    if raw.is_absolute() or not relative_path or "\x00" in relative_path:
        raise GuardError("PATH_NOT_RELATIVE", "closed relative path required")
    if any(part in {"", ".", ".."} for part in raw.parts):
        raise GuardError("PATH_ESCAPE", "path traversal is forbidden")
    resolved_root = repository_root.resolve(strict=True)
    candidate = repository_root.joinpath(raw)
    probe = candidate if candidate.exists() or candidate.is_symlink() else candidate.parent
    while not (probe.exists() or probe.is_symlink()):
        if probe == repository_root or probe.parent == probe:
            break
        probe = probe.parent
    if probe.exists() or probe.is_symlink():
        reject_reparse_ancestry(probe)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise GuardError("PATH_ESCAPE", "resolved path escapes repository") from exc
    if candidate.exists() or candidate.is_symlink():
        reject_reparse_ancestry(candidate)
    if output and candidate.exists() and candidate.is_dir():
        raise GuardError("OUTPUT_IS_DIRECTORY", "output file cannot be a directory")
    return candidate


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_environment(environment: dict[str, str], allowed_names: set[str], forbidden_name_pattern: str = r"(?i)(secret|token|password|credential|api[_-]?key)") -> None:
    if set(environment) - allowed_names:
        raise GuardError("ENV_NOT_ALLOWLISTED", "environment contains an unapproved name")
    pattern = re.compile(forbidden_name_pattern)
    if any(pattern.search(name) for name in environment):
        raise GuardError("ENV_CREDENTIAL_NAME", "credential-like environment names are forbidden")


def _path_identity(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def validate_invocation(
    envelope: dict[str, Any],
    policy: dict[str, Any],
    allowed_environment: set[str],
    allowed_arguments: set[str],
    admitted_executables: dict[str, dict[str, str]],
    allowed_working_directories: set[str],
) -> dict[str, Any]:
    try:
        validate_invocation_envelope(envelope)
    except ContractError as exc:
        raise GuardError("ENVELOPE_INVALID", str(exc)) from exc
    executable = Path(envelope["executable"])
    if not executable.is_absolute():
        raise GuardError("EXECUTABLE_NOT_ABSOLUTE", "exact absolute executable path required")
    reject_reparse_ancestry(executable)
    if not executable.is_file():
        raise GuardError("EXECUTABLE_MISSING", "executable file is missing")
    executable_identity = _path_identity(executable)
    admitted = admitted_executables.get(executable_identity)
    if admitted is None:
        raise GuardError("EXECUTABLE_NOT_ADMITTED", "executable path is outside the exact allowlist")
    if envelope["executable_version"] != admitted["version"]:
        raise GuardError("EXECUTABLE_VERSION_MISMATCH", "executable version mismatch")
    if envelope["executable_sha256"] != admitted["sha256"] or file_sha256(executable) != admitted["sha256"]:
        raise GuardError("EXECUTABLE_HASH_MISMATCH", "executable hash mismatch")
    working_directory = Path(envelope["working_directory"])
    if not working_directory.is_absolute():
        raise GuardError("WORKING_DIRECTORY_NOT_ABSOLUTE", "exact absolute working directory required")
    reject_reparse_ancestry(working_directory)
    if not working_directory.is_dir():
        raise GuardError("WORKING_DIRECTORY_MISSING", "working directory is missing")
    allowed_working_identities = {_path_identity(Path(path)) for path in allowed_working_directories}
    if _path_identity(working_directory) not in allowed_working_identities:
        raise GuardError("WORKING_DIRECTORY_NOT_ADMITTED", "working directory is outside the exact allowlist")
    if any(argument not in allowed_arguments for argument in envelope["arguments"]):
        raise GuardError("ARGUMENT_NOT_ALLOWED", "argument is outside closed grammar")
    validate_environment(envelope["environment"], allowed_environment)
    process_policy = policy["process"]
    if envelope["owned_process_tree"] is not True or not process_policy["owned_declared_tree_only"]:
        raise GuardError("PROCESS_TREE_NOT_OWNED", "only a declared owned process tree is admissible")
    limit_bindings = {
        "timeout_seconds": "timeout_seconds_maximum",
        "cpu_seconds_maximum": "cpu_seconds_maximum",
        "memory_bytes_maximum": "memory_bytes_maximum",
        "process_count_maximum": "process_count_maximum",
        "output_bytes_maximum": "output_bytes_maximum",
    }
    for envelope_key, policy_key in limit_bindings.items():
        if envelope[envelope_key] > process_policy[policy_key]:
            raise GuardError("RESOURCE_LIMIT_EXCEEDED", f"{envelope_key} exceeds the closed policy maximum")
    if envelope["expected_result"] not in process_policy["allowed_expected_results"]:
        raise GuardError("EXPECTED_RESULT_NOT_ALLOWED", "expected result is outside the closed enum")
    if policy["egress"]["allowed_hosts"]:
        raise GuardError("EGRESS_POLICY_NOT_CLOSED", "K0b-03 egress set must be empty")
    return {
        "schema_version": "1.0.0",
        "result": "admissible_for_next_guard",
        "authorized": False,
        "code": "GUARDS_PASSED_NOT_AUTHORIZED",
        "sanitized_evidence": {"effect_id": envelope["effect_id"], "argument_count": len(envelope["arguments"])},
    }
