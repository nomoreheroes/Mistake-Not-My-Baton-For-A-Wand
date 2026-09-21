from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
from typing import Any, Callable


REPOSITORY = Path(os.environ["K0B02_REPOSITORY_ROOT"]).resolve()
RUNTIME_ROOT = Path(os.environ["K0B02_RUNTIME_ROOT"]).resolve()
ENVIRONMENT = os.environ["K0B02_ENVIRONMENT"]
REPORT = Path(os.environ["K0B02_CASE_REPORT"]).resolve()
MANIFEST = (
    REPOSITORY / "new pipeline/evidence/k0b-02-implementation-input-manifest-v1.yaml"
)
FIXTURES = REPOSITORY / "new pipeline/tests/fixtures/k0b02_v1"
PACKAGE_PARENT = REPOSITORY / "new pipeline/harness"
if str(PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_PARENT))

from k0b02_v1.canonical import ContractError as ContractError, json_bytes, sha256  # noqa: E402
from k0b02_v1.contract import InputContext  # noqa: E402
from k0b02_v1.outbox import claim  # noqa: E402
from k0b02_v1.projector import project  # noqa: E402
from k0b02_v1.publisher import _git, publish, verify_git_policy  # noqa: E402
from k0b02_v1.store import K0b02Store  # noqa: E402
from k0b02_v1.transaction_writer import admit  # noqa: E402


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_bytes())


def context() -> InputContext:
    return InputContext(REPOSITORY, MANIFEST)


def case_root(case_id: str, variant: str = "positive") -> Path:
    assert variant in {"positive", "exception", "process_loss"}
    path = RUNTIME_ROOT / ".tmp/runtime/cases" / case_id / variant
    assert path.resolve().is_relative_to(RUNTIME_ROOT.resolve())
    if path.exists():

        def remove_readonly(
            function: Callable[..., Any], target: str, error: BaseException
        ) -> None:
            candidate = Path(target).resolve()
            assert candidate.is_relative_to(RUNTIME_ROOT.resolve())
            os.chmod(candidate, stat.S_IWRITE)
            function(target)

        shutil.rmtree(path, onexc=remove_readonly)
    path.mkdir(parents=True)
    return path


def store_for(root: Path) -> K0b02Store:
    return K0b02Store(context(), RUNTIME_ROOT, RUNTIME_ROOT)


def database_for(
    case_id: str, version: int = 6, variant: str = "positive"
) -> tuple[Path, Path, K0b02Store]:
    root = case_root(case_id, variant)
    database = root / "active.sqlite3"
    store = store_for(root)
    store.initialize_to_version(database, version)
    return root, database, store


def run_git(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
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
    )
    if check and result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", "replace"))
    return result


def init_coordination(
    root: Path, *, envelope: dict[str, Any] | None = None
) -> tuple[Path, str, str]:
    repo = root / "coord-producer"
    repo.mkdir()
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "init",
            "-b",
            "main",
            str(repo),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    for key, value in (
        ("core.autocrlf", "false"),
        ("core.eol", "lf"),
        ("core.hooksPath", "NUL"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
        ("user.name", "K0b02 Fixture"),
        ("user.email", "k0b02-fixture@example.invalid"),
    ):
        run_git(repo, "config", "--local", key, value)
    envelope_value = (
        fixture("replay-envelope-v1.json") if envelope is None else envelope
    )
    envelope_path = repo / ".pipeline/replay/invocation-envelope.json"
    envelope_path.parent.mkdir(parents=True)
    envelope_raw = json_bytes(envelope_value)
    envelope_path.write_bytes(envelope_raw)
    (repo / "unrelated.txt").write_bytes(b"fixture seed\n")
    run_git(
        repo, "add", "--", ".pipeline/replay/invocation-envelope.json", "unrelated.txt"
    )
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )
    commit = subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "-C",
            str(repo),
            "commit",
            "--no-gpg-sign",
            "-m",
            "fixture seed",
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert commit.returncode == 0, commit.stderr.decode("utf-8", "replace")
    assert run_git(repo, "remote").stdout == b""
    verify_git_policy(repo)
    return repo, _git(repo, "rev-parse", "HEAD"), sha256(envelope_raw)


def intent(
    case_id: str, source_seq: int = 1, decision: dict[str, Any] | None = None
) -> dict[str, Any]:
    value = fixture("projection-request-v1.json")
    value["run_id"] = "run-" + case_id
    value["decision_version_id"] = "decision-" + case_id
    value["stable_identity"] = value["decision_version_id"]
    value["idempotency_key"] = (
        value["run_id"] + "|" + value["decision_version_id"] + "|" + str(source_seq)
    )
    value["source_seq"] = source_seq
    if decision is not None:
        value.update(decision)
    return value


def ready_pair(case_id: str) -> dict[str, Any]:
    root, database, store = database_for(case_id)
    repository, parent, envelope_sha = init_coordination(root)
    admitted = admit(database, intent(case_id))
    claimed = claim(database, admitted["outbox_id"])
    assert claimed["result"] == "claimed"
    projected = project(database, admitted["outbox_id"], repository)
    assert projected["ready"] is True
    return {
        "root": root,
        "database": database,
        "store": store,
        "repository": repository,
        "parent": parent,
        "envelope_sha256": envelope_sha,
        "admitted": admitted,
        "projected": projected,
    }


def publication_request(
    bundle: dict[str, Any], publication_id: str = "publication-v1"
) -> dict[str, Any]:
    projected = bundle["projected"]
    pair_set = {
        "projection_id": projected["projection_id"],
        "yaml_sha256": projected["yaml_sha256"],
        "markdown_sha256": projected["markdown_sha256"],
        "source_seq": bundle["admitted"]["source_seq"],
    }
    return {
        "publication_id": publication_id,
        "run_id": bundle["admitted"]["event"]["payload"]["run_id"],
        "phase_id": "K0b-runtime-operational",
        "partition_digest": "1" * 64,
        "source_seq": bundle["admitted"]["source_seq"],
        "receipt_high_water": projected["receipt_seq"],
        "outbox_high_water": bundle["admitted"]["source_seq"],
        "ready_pair_set_sha256": sha256(json_bytes(pair_set)),
        "checkpoint_target": ".pipeline/history/pipeline-checkpoint.sqlite3",
        "projection_profile_sha256": "2" * 64,
        "expected_Git_parent": bundle["parent"],
        "predecessor_publication_id": None,
    }


def published(
    case_id: str, publication_id: str = "publication-v1"
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bundle = ready_pair(case_id)
    request = publication_request(bundle, publication_id)
    result = publish(bundle["store"], bundle["database"], bundle["repository"], request)
    assert result["result"] in {"committed", "original", "recovered"}
    return bundle, request, result


def record(case_id: str, result: str = "pass", **facts: Any) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    row = {"case_id": case_id, "environment": ENVIRONMENT, "result": result, **facts}
    with REPORT.open("ab") as stream:
        stream.write(json_bytes(row))


def measured(case_id: str, operation: Callable[[], Any]) -> tuple[Any, float]:
    started = time.monotonic()
    value = operation()
    elapsed = time.monotonic() - started
    record(case_id, elapsed_seconds=elapsed)
    return value, elapsed


def complete_file(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
