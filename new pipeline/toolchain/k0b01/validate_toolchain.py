from __future__ import annotations

import argparse
import _sqlite3
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

SUCCESS = 0
INVALID_INPUT = 2
TOOLCHAIN_MISMATCH = 4

EXPECTED_LOCK_SHA256 = (
    "3ba58d66cb338256b92387c5b6f621f9b35adad3607ced3d7e2942c7359eafc0"
)
EXPECTED_SQLITE = {
    "extension_module": {
        "filename": "_sqlite3.pyd",
        "sha256": "da8f0c093caf4462f434615de95cc7a60f6d4595962688df1112e515963b9626",
    },
    "library": {
        "bytes": 1_596_176,
        "filename": "sqlite3.dll",
        "sha256": "0ca33a3cdbd4f54084e64e8ca71ae986f6d738a20d38400470011cd794ec9c02",
        "version": "3.45.3",
    },
    "python_module_version": "2.6.0",
}
EXPECTED_PACKAGES = {
    "colorama": (
        "0.4.6",
        "colorama-0.4.6-py2.py3-none-any.whl",
        "4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6",
    ),
    "iniconfig": (
        "1.1.1",
        "iniconfig-1.1.1-py2.py3-none-any.whl",
        "011e24c64b7f47f6ebd835bb12a743f2fbe9a26d4cecaa7f53bc4f35ee9da8b3",
    ),
    "packaging": (
        "24.1",
        "packaging-24.1-py3-none-any.whl",
        "5b8f2217dbdbd2f7f384c41c628544e6d52f2d0f53c6d0c3ea61aa5d1d7ff124",
    ),
    "pip": (
        "24.2",
        "pip-24.2-py3-none-any.whl",
        "2cd581cf58ab7fcfca4ce8efa6dcacd0de5bf8d0a3eb9ec927e07405f4d9e2a2",
    ),
    "pluggy": (
        "1.6.0",
        "pluggy-1.6.0-py3-none-any.whl",
        "e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746",
    ),
    "pygments": (
        "2.15.1",
        "Pygments-2.15.1-py3-none-any.whl",
        "db2db3deb4b4179f399a09054b023b6a586b76499d36965813c71aa8ed7b5fd1",
    ),
    "pytest": (
        "9.0.2",
        "pytest-9.0.2-py3-none-any.whl",
        "711ffd45bf766d5264d487b917733b453d917afd2b0ad65223959f59089f875b",
    ),
    "ruamel.yaml": (
        "0.18.6",
        "ruamel.yaml-0.18.6-py3-none-any.whl",
        "57b53ba33def16c4f3d807c0ccbc00f8a6081827e81ba2491691b76882d0c636",
    ),
    "ruamel.yaml.clib": (
        "0.2.8",
        "ruamel.yaml.clib-0.2.8-cp312-cp312-win_amd64.whl",
        "1758ce7d8e1a29d23de54a16ae867abd370f01b5a69e1a3ba75223eaa3ca1a1b",
    ),
    "ruff": (
        "0.15.1",
        "ruff-0.15.1-py3-none-win_amd64.whl",
        "c820fef9dd5d4172a6570e5721704a96c6679b80cf7be41659ed439653f62336",
    ),
    "setuptools": (
        "75.1.0",
        "setuptools-75.1.0-py3-none-any.whl",
        "35ab7fd3bcd95e6b7fd704e4a1539513edad446c097797f2985e0e4b960772f2",
    ),
    "wheel": (
        "0.44.0",
        "wheel-0.44.0-py3-none-any.whl",
        "2376a90c98cc337d18623527a97c31797bd02bad0033d41547043a1cbfbe448f",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _emit(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(_canonical_bytes(value))


def _expected_requirement_lines() -> list[str]:
    return [
        f"{name}=={version} --hash=sha256:{digest}"
        for name, (version, _wheel, digest) in sorted(EXPECTED_PACKAGES.items())
    ]


def _has_absolute_normative_string(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_absolute_normative_string(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_absolute_normative_string(item) for item in value)
    if not isinstance(value, str):
        return False
    return len(value) >= 3 and value[1:3] in {":/", ":\\"}


def _command_output(arguments: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def validate(toolchain_root: Path, wheelhouse: Path) -> tuple[int, dict[str, Any]]:
    lock_path = toolchain_root / "toolchain-lock-v1.json"
    requirements_path = toolchain_root / "requirements-v1.lock"
    if not toolchain_root.is_dir() or not wheelhouse.is_dir():
        return INVALID_INPUT, {
            "exit_code": INVALID_INPUT,
            "result": "invalid_input",
        }
    if not lock_path.is_file() or not requirements_path.is_file():
        return INVALID_INPUT, {
            "exit_code": INVALID_INPUT,
            "result": "invalid_input",
        }

    failures: list[str] = []
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return TOOLCHAIN_MISMATCH, {
            "exit_code": TOOLCHAIN_MISMATCH,
            "failures": ["lock:invalid_json"],
            "result": "toolchain_mismatch",
        }

    lock_hash = _sha256(lock_path)
    if lock_hash != EXPECTED_LOCK_SHA256:
        failures.append("lock:sha256")
    if lock.get("profile_id") != "pipeline-v2.k0b01-toolchain-lock-v1":
        failures.append("lock:profile_id")
    if lock.get("profile_version") != 1:
        failures.append("lock:profile_version")
    if _has_absolute_normative_string(lock):
        failures.append("lock:absolute_normative_value")

    expected_canonicalization = {
        "encoding": "UTF-8",
        "final_newline_count": 1,
        "line_endings": "LF",
        "locale": "invariant",
        "sorting": "ordinal",
        "timezone": "UTC",
    }
    if lock.get("canonicalization") != expected_canonicalization:
        failures.append("lock:canonicalization")
    expected_exit_codes = {
        "budget_evidence_invalid": 5,
        "invalid_input": 2,
        "prerequisite_not_materialized": 3,
        "success": 0,
        "toolchain_mismatch": 4,
    }
    if lock.get("exit_codes") != expected_exit_codes:
        failures.append("lock:exit_codes")
    expected_commands = {
        "bootstrap": "invoke.ps1 -Command bootstrap",
        "check": "invoke.ps1 -Command check",
        "format_check": "invoke.ps1 -Command format-check",
        "lint": "invoke.ps1 -Command lint",
        "render": "invoke.ps1 -Command render",
        "test": "invoke.ps1 -Command test",
        "validate": "invoke.ps1 -Command validate",
        "validate_budget": "invoke.ps1 -Command validate-budget",
    }
    if lock.get("commands") != expected_commands:
        failures.append("lock:commands")
    expected_ci_manifest = {
        "ci_execution_claim": False,
        "manifest_role": "toolchain_and_ci_prerequisite",
        "supported_validation_entry_point": "invoke.ps1 -Command validate",
    }
    if lock.get("ci_manifest") != expected_ci_manifest:
        failures.append("lock:ci_manifest")
    expected_import_root = {
        "ambient_pythonpath": "forbidden",
        "frozen_k0b01_provenance_on_import_path": "forbidden",
        "future_runtime_import_root": "requires_separate_exact_owner_authority",
        "repository_root_as_implicit_import_root": "forbidden",
        "strategy": "explicit_entry_point_directory",
        "toolchain_root": "new pipeline/toolchain/k0b01",
    }
    if lock.get("import_root") != expected_import_root:
        failures.append("lock:import_root")
    expected_quality_tools = {
        "formatter": {
            "command": "invoke.ps1 -Command format-check",
            "package": "ruff",
            "version": "0.15.1",
        },
        "linter": {
            "command": "invoke.ps1 -Command lint",
            "package": "ruff",
            "version": "0.15.1",
        },
        "owned_python_files": [
            "test_budget_evidence.py",
            "test_toolchain.py",
            "validate_budget_evidence.py",
            "validate_toolchain.py",
        ],
    }
    if lock.get("quality_tools") != expected_quality_tools:
        failures.append("lock:quality_tools")
    if lock.get("sqlite") != EXPECTED_SQLITE:
        failures.append("lock:sqlite")

    observed_packages = lock.get("packages")
    expected_package_document = {
        name: {"sha256": digest, "version": version, "wheel": wheel}
        for name, (version, wheel, digest) in EXPECTED_PACKAGES.items()
    }
    if observed_packages != expected_package_document:
        failures.append("lock:packages")

    try:
        requirements_bytes = requirements_path.read_bytes()
        requirements_text = requirements_bytes.decode("utf-8")
    except (OSError, UnicodeError):
        requirements_bytes = b""
        requirements_text = ""
        failures.append("requirements:utf8")
    expected_requirements = "\n".join(_expected_requirement_lines()) + "\n"
    if requirements_text != expected_requirements:
        failures.append("requirements:content")
    if b"\r" in requirements_bytes:
        failures.append("requirements:line_endings")

    if sys.version_info[:3] != (3, 12, 7):
        failures.append("runtime:version")
    if platform.python_implementation() != "CPython":
        failures.append("runtime:implementation")
    if sys.platform != "win32":
        failures.append("platform:family")
    if platform.machine().upper() != "AMD64":
        failures.append("platform:architecture")
    if platform.version() != "10.0.20348":
        failures.append("platform:tested_host_os")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        sqlite_module_version = sqlite3.version
    if sqlite_module_version != EXPECTED_SQLITE["python_module_version"]:
        failures.append("sqlite:python_module_version")
    if sqlite3.sqlite_version != EXPECTED_SQLITE["library"]["version"]:
        failures.append("sqlite:library_version")
    sqlite_extension_path = Path(_sqlite3.__file__)
    if sqlite_extension_path.name != EXPECTED_SQLITE["extension_module"]["filename"]:
        failures.append("sqlite:extension_filename")
    elif (
        _sha256(sqlite_extension_path) != EXPECTED_SQLITE["extension_module"]["sha256"]
    ):
        failures.append("sqlite:extension_sha256")
    sqlite_library_path = Path(sys.base_prefix) / "Library" / "bin" / "sqlite3.dll"
    if not sqlite_library_path.is_file():
        failures.append("sqlite:library_missing")
    else:
        if sqlite_library_path.name != EXPECTED_SQLITE["library"]["filename"]:
            failures.append("sqlite:library_filename")
        if sqlite_library_path.stat().st_size != EXPECTED_SQLITE["library"]["bytes"]:
            failures.append("sqlite:library_bytes")
        if _sha256(sqlite_library_path) != EXPECTED_SQLITE["library"]["sha256"]:
            failures.append("sqlite:library_sha256")

    for name, (version, _wheel, _digest) in EXPECTED_PACKAGES.items():
        try:
            observed_version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            failures.append(f"package:{name}:missing")
            continue
        if observed_version != version:
            failures.append(f"package:{name}:version")

    wheel_records: list[dict[str, Any]] = []
    expected_wheel_names = {item[1] for item in EXPECTED_PACKAGES.values()}
    actual_wheel_names = {item.name for item in wheelhouse.iterdir() if item.is_file()}
    if actual_wheel_names != expected_wheel_names:
        failures.append("wheelhouse:file_set")
    for name, (_version, wheel, expected_hash) in sorted(EXPECTED_PACKAGES.items()):
        wheel_path = wheelhouse / wheel
        if not wheel_path.is_file():
            failures.append(f"wheel:{name}:missing")
            continue
        observed_hash = _sha256(wheel_path)
        if observed_hash != expected_hash:
            failures.append(f"wheel:{name}:sha256")
        wheel_records.append(
            {
                "name": name,
                "sha256": observed_hash,
                "size_bytes": wheel_path.stat().st_size,
                "wheel": wheel,
            }
        )

    shell_path_text = shutil.which("powershell.exe")
    if shell_path_text is None:
        failures.append("shell:missing")
    else:
        shell_path = Path(shell_path_text)
        if _sha256(shell_path) != lock.get("shell", {}).get(
            "executable_sha256_observed"
        ):
            failures.append("shell:sha256")
        shell_version = _command_output(
            [
                shell_path_text,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ]
        )
        if shell_version != lock.get("shell", {}).get("version"):
            failures.append("shell:version")

    git_path_text = shutil.which("git.exe")
    if git_path_text is None:
        failures.append("git:missing")
    else:
        git_path = Path(git_path_text)
        if _sha256(git_path) != lock.get("git", {}).get("executable_sha256_observed"):
            failures.append("git:sha256")
        git_output = _command_output([git_path_text, "--version"])
        if git_output != f"git version {lock.get('git', {}).get('version')}":
            failures.append("git:version")

    wheel_set_hash = hashlib.sha256(_canonical_bytes(wheel_records)).hexdigest()
    if failures:
        return TOOLCHAIN_MISMATCH, {
            "exit_code": TOOLCHAIN_MISMATCH,
            "failures": sorted(set(failures)),
            "profile_id": lock.get("profile_id"),
            "result": "toolchain_mismatch",
        }
    return SUCCESS, {
        "exit_code": SUCCESS,
        "package_count": len(EXPECTED_PACKAGES),
        "profile_id": lock["profile_id"],
        "requirements_sha256": hashlib.sha256(requirements_bytes).hexdigest(),
        "result": "pass",
        "sqlite_library_version": sqlite3.sqlite_version,
        "sqlite_python_module_version": sqlite_module_version,
        "toolchain_lock_sha256": lock_hash,
        "wheel_count": len(wheel_records),
        "wheel_set_sha256": wheel_set_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolchain-root", required=True, type=Path)
    parser.add_argument("--wheelhouse", required=True, type=Path)
    arguments = parser.parse_args(argv)
    exit_code, result = validate(arguments.toolchain_root, arguments.wheelhouse)
    _emit(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
