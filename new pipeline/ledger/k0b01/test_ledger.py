from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import ledger

LEDGER_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = LEDGER_ROOT.parents[2]
SCHEMA_PATH = LEDGER_ROOT / "schema-profile-v1.yaml"
EVENTS_PATH = LEDGER_ROOT / "events"
INDEX_PATH = LEDGER_ROOT / "index-v1.yaml"
FIXTURE_PATHS = tuple(
    sorted(
        (LEDGER_ROOT / "fixtures").glob("*/*.yaml"),
        key=lambda path: path.as_posix(),
    )
)


def _records() -> list[tuple[str, str, dict[str, Any]]]:
    return ledger.load_and_validate_events(SCHEMA_PATH, EVENTS_PATH, REPOSITORY_ROOT)


def _copy_corpus(tmp_path: Path) -> tuple[Path, Path]:
    schema_path = tmp_path / "schema-profile-v1.yaml"
    events_path = tmp_path / "events"
    events_path.mkdir()
    shutil.copyfile(SCHEMA_PATH, schema_path)
    for source in EVENTS_PATH.glob("*.yaml"):
        shutil.copyfile(source, events_path / source.name)
    return schema_path, events_path


def _descend(document: Any, dotted: str) -> tuple[Any, str]:
    parts = dotted.split(".")
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def _set_dotted(document: Any, dotted: str, value: Any) -> None:
    parent, key = _descend(document, dotted)
    if isinstance(parent, list):
        parent[int(key)] = value
    else:
        parent[key] = value


def _delete_dotted(document: Any, dotted: str) -> None:
    parent, key = _descend(document, dotted)
    if isinstance(parent, list):
        del parent[int(key)]
    else:
        del parent[key]


def _write_yaml(path: Path, document: Any) -> None:
    path.write_bytes(ledger.dump_yaml_bytes(document))


def _append_terminal_chains(events_path: Path) -> None:
    template = ledger.load_yaml(
        events_path / "2001-implementation-ledger-invocation-v1.yaml"
    )
    specifications = (
        ("3000", "3001", "REJECTED", "rejected", "rejection"),
        ("3100", "3101", "SUPERSEDED", "superseded", "supersession"),
        ("3200", "3201", "STALE", "stale", "stale"),
    )
    for root_number, terminal_number, suffix, state, reason_field in specifications:
        root = copy.deepcopy(template)
        root_id = f"{root_number}-fixture-{state}-declared-v1"
        root["event_id"] = root_id
        root["unit_id"] = f"K0B01-INCIDENT-FIXTURE-{suffix}"
        root["event_type"] = "transition"
        root["historical"]["classification"] = "synthetic_fixture_declared"
        root_path = events_path / f"{root_id}.yaml"
        _write_yaml(root_path, root)

        terminal = copy.deepcopy(root)
        terminal_id = f"{terminal_number}-fixture-{state}-v1"
        terminal["event_id"] = terminal_id
        terminal["event_type"] = {
            "rejected": "rejection",
            "superseded": "supersession",
            "stale": "stale_marker",
        }[state]
        terminal["resulting_state"] = state
        terminal["predecessor"] = {
            "kind": "workspace_file",
            "path": f"new pipeline/ledger/k0b01/events/{root_path.name}",
            "sha256": hashlib.sha256(root_path.read_bytes()).hexdigest(),
        }
        terminal["reason"][reason_field] = f"synthetic_{state}_reason"
        terminal["historical"]["classification"] = f"synthetic_fixture_{state}"
        _write_yaml(events_path / f"{terminal_id}.yaml", terminal)


def _apply_fixture(
    fixture: dict[str, Any], schema_path: Path, events_path: Path
) -> None:
    operation = fixture["operation"]
    operation_type = operation["type"]
    if operation_type == "no_change":
        return
    if operation_type == "append_terminal_chains":
        _append_terminal_chains(events_path)
        return
    if operation_type == "set_schema_field":
        document = ledger.load_yaml(schema_path)
        _set_dotted(document, operation["field"], operation["value"])
        _write_yaml(schema_path, document)
        return

    source = events_path / operation["event"]
    if operation_type == "duplicate_event":
        shutil.copyfile(source, events_path / operation["new_filename"])
        return
    if operation_type == "rename_event":
        source.rename(events_path / operation["new_filename"])
        return

    document = ledger.load_yaml(source)
    if operation_type == "set_event_field":
        _set_dotted(document, operation["field"], operation["value"])
    elif operation_type == "delete_event_field":
        _delete_dotted(document, operation["field"])
    elif operation_type == "duplicate_evidence":
        document["evidence"].append(copy.deepcopy(document["evidence"][0]))
    else:
        raise AssertionError(f"unknown fixture operation: {operation_type}")
    _write_yaml(source, document)


def _fixture_result(fixture: dict[str, Any], tmp_path: Path) -> tuple[str, str]:
    schema_path, events_path = _copy_corpus(tmp_path)
    _apply_fixture(fixture, schema_path, events_path)
    try:
        ledger.load_and_validate_events(schema_path, events_path, REPOSITORY_ROOT)
    except ledger.LedgerError as exc:
        reason = str(exc)
        result = "zero_credit" if reason.startswith("zero_credit:") else "fail_closed"
        return result, reason
    operation_type = fixture["operation"]["type"]
    reason = (
        "validated_terminal_chains"
        if operation_type == "append_terminal_chains"
        else "validated_canonical_population"
    )
    return "pass", reason


@pytest.mark.parametrize("fixture_path", FIXTURE_PATHS, ids=lambda path: path.stem)
def test_fixture_exercises_production_validator(
    fixture_path: Path, tmp_path: Path
) -> None:
    assert len(FIXTURE_PATHS) == 22
    fixture = ledger.load_yaml(fixture_path)
    actual_result, actual_reason = _fixture_result(fixture, tmp_path)
    assert fixture["expected"] == {
        "result": actual_result,
        "reason": actual_reason,
    }


def test_schema_profile_enforces_contract() -> None:
    schema = ledger.validate_schema(ledger.load_yaml(SCHEMA_PATH))
    assert schema["lifecycle"]["no_state_implies_the_next"] is True
    assert schema["lifecycle"]["committed_implies_runtime_authorized"] is False
    assert schema["index_profile"]["authoritative"] is False


def test_index_generation_is_byte_deterministic() -> None:
    records = _records()
    first = ledger.dump_yaml_bytes(
        ledger.index_document(
            records,
            schema_path=SCHEMA_PATH,
            repository_root=REPOSITORY_ROOT,
        )
    )
    second = ledger.dump_yaml_bytes(
        ledger.index_document(
            records,
            schema_path=SCHEMA_PATH,
            repository_root=REPOSITORY_ROOT,
        )
    )
    assert first == second


def test_index_is_non_authoritative_and_cannot_grant_credit() -> None:
    document = ledger.load_yaml(INDEX_PATH)
    assert document["generated_index_authoritative"] is False
    assert document["grants_authority_credit_or_runtime_effect"] is False


def test_actual_check_index_rejects_tampered_index(tmp_path: Path) -> None:
    tampered = tmp_path / "tampered-index.yaml"
    output = tmp_path / "index-check.json"
    tampered.write_bytes(INDEX_PATH.read_bytes() + b"# tampered\n")
    result = ledger.main(
        [
            "check-index",
            "--schema",
            str(SCHEMA_PATH),
            "--events",
            str(EVENTS_PATH),
            "--repository-root",
            str(REPOSITORY_ROOT),
            "--index",
            str(tampered),
            "--output",
            str(output),
        ]
    )
    assert result == ledger.INDEX_STALE
    assert json.loads(output.read_text(encoding="utf-8"))["result"] == "stale"


def test_canonical_population_and_summary_are_computed() -> None:
    records = _records()
    summary = ledger.validation_summary(records)
    assert len(records) == 26
    assert summary == {
        "closed_gates": ["G-K0B01-HUMAN-SIGNOFF"],
        "credited_event_count": 1,
        "event_count": 26,
        "human_signoff_state": "credited",
        "implementation_invocation_count": 1,
        "incident_count": 19,
        "result": "pass",
        "runtime_authorized": False,
    }


def test_event_0006_uses_committed_state_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = ledger.load_yaml(EVENTS_PATH / "0006-human-signoff-credited-v1.yaml")
    state_dependencies = [
        reference
        for reference in event["dependencies"]
        if reference["kind"] == "git_blob"
    ]
    assert len(state_dependencies) == 2
    fake_state = tmp_path / "changed-working-state.yaml"
    fake_state.write_text("changed: true\n", encoding="utf-8", newline="\n")
    original = ledger._safe_workspace_path

    def redirected(repository_root: Path, relative_path: str) -> Path:
        if relative_path in (
            "new pipeline/state/state.yaml",
            "new pipeline/state/STATE.md",
        ):
            return fake_state
        return original(repository_root, relative_path)

    monkeypatch.setattr(ledger, "_safe_workspace_path", redirected)
    assert len(_records()) == 26


def test_valid_future_event_with_new_authority_is_appendable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_path, events_path = _copy_corpus(tmp_path)
    future_request = tmp_path / "future-approval-request.yaml"
    future_request.write_text("status: confirmed\n", encoding="utf-8", newline="\n")
    logical_request = "new pipeline/requests/future-approval-request.yaml"
    request_sha = hashlib.sha256(future_request.read_bytes()).hexdigest()
    original = ledger._safe_workspace_path

    def redirected(repository_root: Path, relative_path: str) -> Path:
        if relative_path == logical_request:
            return future_request
        return original(repository_root, relative_path)

    monkeypatch.setattr(ledger, "_safe_workspace_path", redirected)
    event = ledger.load_yaml(
        events_path / "2001-implementation-ledger-invocation-v1.yaml"
    )
    event["event_id"] = "2997-future-authorized-event-v1"
    event["unit_id"] = "K0B01-STATE-RENDERER"
    event["event_type"] = "transition"
    request_reference = {
        "kind": "workspace_file",
        "path": logical_request,
        "sha256": request_sha,
    }
    event["materialization_authority"]["request"] = copy.deepcopy(request_reference)
    event["materialization_authority"]["confirmation"] = {
        "source": "synthetic_separate_owner_confirmation",
        "repeated_request_sha256": request_sha,
        "exact_match": True,
        "exact_scope_authorized": True,
        "actor": "workspace_owner",
    }
    event["subject_authority"] = copy.deepcopy(request_reference)
    event["evidence"] = [copy.deepcopy(request_reference)]
    event["historical"]["classification"] = "synthetic_future_append"
    event["historical"]["implementation_authority"] = "future_exact_scope_only"
    _write_yaml(events_path / "2997-future-authorized-event-v1.yaml", event)
    assert (
        len(ledger.load_and_validate_events(schema_path, events_path, REPOSITORY_ROOT))
        == 27
    )


def test_canonical_population_makes_no_forbidden_claim() -> None:
    for _, _, event in _records():
        snapshot = event["budget_snapshot"]
        assert snapshot["f15_authoritative_worst_case_object_count"] is None
        assert snapshot["f15_size_stress_claim"] is False
        assert snapshot["phase_completion_claim"] is False
        assert event["historical"]["runtime_authority"] == "none"
