from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLCHAIN_ROOT = Path(__file__).resolve().parent
LOCK_PATH = TOOLCHAIN_ROOT / "toolchain-lock-v1.json"
REQUIREMENTS_PATH = TOOLCHAIN_ROOT / "requirements-v1.lock"
VALIDATOR_PATH = TOOLCHAIN_ROOT / "validate_toolchain.py"
INVOKE_PATH = TOOLCHAIN_ROOT / "invoke.ps1"
EXPECTED_LOCK_SHA256 = (
    "3ba58d66cb338256b92387c5b6f621f9b35adad3607ced3d7e2942c7359eafc0"
)


def _wheelhouse() -> Path:
    value = os.environ.get("PIPELINE_V2_WHEELHOUSE")
    if value is None:
        pytest.fail("PIPELINE_V2_WHEELHOUSE is required")
    return Path(value)


def _run_validator(root: Path = TOOLCHAIN_ROOT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            str(root / "validate_toolchain.py"),
            "--toolchain-root",
            str(root),
            "--wheelhouse",
            str(_wheelhouse()),
        ],
        check=False,
        capture_output=True,
    )


def test_lock_hash_and_requirement_hashes_are_exact() -> None:
    assert hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest() == EXPECTED_LOCK_SHA256
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    requirement_lines = REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
    expected_lines = [
        f"{name}=={item['version']} --hash=sha256:{item['sha256']}"
        for name, item in sorted(lock["packages"].items())
    ]
    assert requirement_lines == expected_lines
    assert REQUIREMENTS_PATH.read_bytes().endswith(b"\n")
    assert b"\r" not in REQUIREMENTS_PATH.read_bytes()
    assert lock["sqlite"]["python_module_version"] == "2.6.0"
    assert lock["sqlite"]["library"]["version"] == "3.45.3"
    assert lock["quality_tools"]["linter"]["version"] == "0.15.1"
    assert lock["quality_tools"]["formatter"]["version"] == "0.15.1"
    assert lock["import_root"]["ambient_pythonpath"] == "forbidden"
    assert lock["ci_manifest"] == {
        "ci_execution_claim": False,
        "manifest_role": "toolchain_and_ci_prerequisite",
        "supported_validation_entry_point": "invoke.ps1 -Command validate",
    }


def test_validator_output_is_byte_deterministic_and_path_free() -> None:
    first = _run_validator()
    second = _run_validator()
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["result"] == "pass"
    assert result["package_count"] == 12
    assert result["wheel_count"] == 12
    assert result["sqlite_python_module_version"] == "2.6.0"
    assert result["sqlite_library_version"] == "3.45.3"
    assert str(TOOLCHAIN_ROOT).encode() not in first.stdout
    assert str(_wheelhouse()).encode() not in first.stdout


def test_validator_fails_closed_for_a_changed_lock(tmp_path: Path) -> None:
    for name in (
        "requirements-v1.lock",
        "toolchain-lock-v1.json",
        "validate_toolchain.py",
    ):
        shutil.copyfile(TOOLCHAIN_ROOT / name, tmp_path / name)
    lock_path = tmp_path / "toolchain-lock-v1.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["profile_version"] = 2
    lock_path.write_text(
        json.dumps(lock, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    completed = _run_validator(tmp_path)
    assert completed.returncode == 4
    result = json.loads(completed.stdout)
    assert result["result"] == "toolchain_mismatch"
    assert "lock:sha256" in result["failures"]


@pytest.mark.parametrize("command", ["render", "check"])
def test_unmaterialized_commands_fail_closed(command: str) -> None:
    powershell = shutil.which("powershell.exe")
    assert powershell is not None
    completed = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INVOKE_PATH),
            "-Command",
            command,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    assert completed.returncode == 3
    result = json.loads(completed.stdout)
    assert result == {
        "command": command,
        "exit_code": 3,
        "result": "prerequisite_not_materialized",
    }


@pytest.mark.parametrize("command", ["lint", "format-check"])
def test_locked_quality_commands_pass(command: str) -> None:
    powershell = shutil.which("powershell.exe")
    assert powershell is not None
    completed = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INVOKE_PATH),
            "-Command",
            command,
            "-PythonPath",
            sys.executable,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
