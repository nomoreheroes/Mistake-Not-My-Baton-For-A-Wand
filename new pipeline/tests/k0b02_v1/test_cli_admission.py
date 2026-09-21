from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from fixture_support import (
    ENVIRONMENT,
    MANIFEST,
    REPOSITORY,
    RUNTIME_ROOT,
    case_root,
    record,
    sha256,
)


CLI = REPOSITORY / "new pipeline/harness/k0b02_v1/cli.py"
TOOLCHAIN = (
    "new pipeline/toolchain/k0b01/requirements-v1.lock",
    "new pipeline/toolchain/k0b01/bootstrap.ps1",
    "new pipeline/toolchain/k0b01/invoke.ps1",
    "new pipeline/toolchain/k0b01/prepare-wheelhouse.ps1",
    "new pipeline/toolchain/k0b02/invoke-v1.ps1",
)


def _cli(mode: str, runtime: Path, *extra: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(CLI),
            mode,
            "--repository-root",
            str(REPOSITORY),
            "--manifest",
            str(MANIFEST),
            "--runtime-root",
            str(runtime),
            "--environment",
            ENVIRONMENT,
            *extra,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_path_escape_denied_before_output() -> None:
    case_root("path_escape", "exception")
    escaped = RUNTIME_ROOT.parent / "k0b02-escaped.sqlite3"
    assert not escaped.exists()
    result = _cli("init-db", RUNTIME_ROOT, "--database", str(escaped))
    assert result.returncode == 1 and b"CLI:escape" in result.stderr
    assert not escaped.exists()
    record("path_escape")


def test_cli_denied_root() -> None:
    denied = RUNTIME_ROOT / ".tmp"
    denied.mkdir(exist_ok=True)
    result = _cli("validate-inputs", denied)
    assert result.returncode == 1 and b"CLI:denied_root" in result.stderr
    record("cli_denied_root")


def test_cli_input_output_collision() -> None:
    result = _cli("compile-all", RUNTIME_ROOT, "--output-dir", str(RUNTIME_ROOT))
    assert result.returncode == 1 and b"CLI:output_dir" in result.stderr
    record("cli_input_output_collision")


def _git(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check:
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result


def _eol_fixture(case_id: str, positive: bool) -> tuple[dict[str, str], dict[str, str]]:
    root = case_root(case_id)
    producer, clone = root / "coord-producer", root / "coord-clone"
    producer.mkdir()
    _git(producer, "init", "-b", "main")
    for key, value in (
        ("core.autocrlf", "true"),
        ("core.eol", "lf"),
        ("core.hooksPath", "NUL"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
        ("user.name", "K0b02 EOL Fixture"),
        ("user.email", "k0b02-eol@example.invalid"),
    ):
        _git(producer, "config", "--local", key, value)
    if positive:
        attributes = (REPOSITORY / ".gitattributes").read_bytes()
    else:
        attributes = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY),
                "show",
                "de1dce970acb0e83eff34f9e8a429a451e478c5c:.gitattributes",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
    (producer / ".gitattributes").write_bytes(attributes)
    expected: dict[str, str] = {}
    for relative in TOOLCHAIN:
        raw = (REPOSITORY / relative).read_bytes()
        expected[relative] = sha256(raw)
        target = producer / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    _git(producer, "add", "--", ".gitattributes", *TOOLCHAIN)
    _git(producer, "commit", "--no-gpg-sign", "-m", "EOL fixture seed")
    cloned = subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=true",
            "-c",
            "core.eol=lf",
            "clone",
            "--no-hardlinks",
            "--no-checkout",
            str(producer),
            str(clone),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert cloned.returncode == 0, cloned.stderr.decode("utf-8", "replace")
    for key, value in (
        ("core.autocrlf", "true"),
        ("core.eol", "lf"),
        ("core.hooksPath", "NUL"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        _git(clone, "config", "--local", key, value)
    _git(clone, "remote", "remove", "origin")
    assert _git(clone, "remote").stdout == b""
    _git(clone, "checkout", "--force", "HEAD")
    actual = {
        relative: sha256((clone / relative).read_bytes()) for relative in TOOLCHAIN
    }
    return expected, actual


def test_eol_checkout_invariance_with_authorized_attributes() -> None:
    expected, actual = _eol_fixture("eol_checkout_invariance", True)
    assert actual == expected
    record("eol_checkout_invariance", toolchain_files=len(actual))


def test_missing_attributes_detected_before_scope_mutation() -> None:
    expected, actual = _eol_fixture("eol_missing_attributes_rejected", False)
    drifted = sorted(path for path in TOOLCHAIN if actual[path] != expected[path])
    assert drifted and all(path.endswith((".ps1", ".lock")) for path in drifted)
    record("eol_missing_attributes_rejected", drifted=drifted, scope_mutations=0)
