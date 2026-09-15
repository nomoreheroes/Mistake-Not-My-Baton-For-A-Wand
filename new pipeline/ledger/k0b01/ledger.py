from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.tokens import AliasToken, AnchorToken

SUCCESS = 0
VALIDATION_FAILED = 5
INDEX_STALE = 7

LEDGER_ROOT = Path(__file__).resolve().parent
DEFAULT_SCHEMA_PATH = LEDGER_ROOT / "schema-profile-v1.yaml"
DEFAULT_REPOSITORY_ROOT = LEDGER_ROOT.parents[2]
EVENT_PATH_PREFIX = "new pipeline/ledger/k0b01/events/"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EVENT_ID_RE = re.compile(r"^[0-9]{4}-[a-z0-9][a-z0-9-]*-v[0-9]+$")


class LedgerError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_text(data: bytes, *, label: str) -> str:
    _require(not data.startswith(b"\xef\xbb\xbf"), f"{label}:BOM_forbidden")
    _require(b"\r" not in data, f"{label}:LF_required")
    _require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{label}:final_LF")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LedgerError(f"{label}:UTF_8_required") from exc


def _yaml() -> YAML:
    parser = YAML(typ="safe", pure=True)
    parser.allow_duplicate_keys = False
    return parser


def load_yaml(path: Path) -> Any:
    data = path.read_bytes()
    text = _canonical_text(data, label=path.name)
    parser = _yaml()
    try:
        for token in parser.scan(text):
            _require(
                not isinstance(token, (AliasToken, AnchorToken)),
                f"{path.name}:anchors_and_aliases_forbidden",
            )
        parser = _yaml()
        return parser.load(text)
    except LedgerError:
        raise
    except Exception as exc:
        raise LedgerError(f"{path.name}:YAML_parse:{type(exc).__name__}") from exc


def dump_yaml_bytes(document: Any) -> bytes:
    parser = YAML(typ="safe", pure=True)
    parser.allow_unicode = False
    parser.default_flow_style = False
    parser.width = 4096
    parser.indent(mapping=2, sequence=4, offset=2)
    stream = io.StringIO()
    parser.dump(document, stream)
    return stream.getvalue().replace("\r\n", "\n").encode("utf-8")


def _json_bytes(document: Any) -> bytes:
    return (
        json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _write_output(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _valid_commit(value: Any) -> bool:
    return isinstance(value, str) and COMMIT_RE.fullmatch(value) is not None


def _safe_workspace_path(repository_root: Path, relative_path: str) -> Path:
    _require("\\" not in relative_path, "reference:forward_slash_required")
    posix = PurePosixPath(relative_path)
    _require(not posix.is_absolute(), "reference:relative_path_required")
    _require(".." not in posix.parts, "reference:path_escape")
    candidate = (repository_root / Path(*posix.parts)).resolve()
    root = repository_root.resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(candidate))))
    except ValueError as exc:
        raise LedgerError("reference:path_escape") from exc
    _require(common == root, "reference:path_escape")
    return candidate


def _reference(value: Any, *, field: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{field}:object_required")
    kind = value.get("kind")
    if kind == "workspace_file":
        _require(set(value) == {"kind", "path", "sha256"}, f"{field}:shape")
    elif kind == "git_blob":
        _require(
            set(value) == {"kind", "commit", "path", "sha256"},
            f"{field}:shape",
        )
        _require(_valid_commit(value.get("commit")), f"{field}:commit")
    else:
        raise LedgerError(f"{field}:unknown_reference_kind")
    path = value.get("path")
    _require(isinstance(path, str) and bool(path), f"{field}:path")
    _require(_valid_sha(value.get("sha256")), f"{field}:sha256")
    _require(
        "\\" not in path and ".." not in PurePosixPath(path).parts,
        f"{field}:path",
    )
    return dict(value)


def _allowed_workspace_path(path: str, schema: dict[str, Any]) -> bool:
    prefixes = schema["reference_contract"]["allowed_workspace_prefixes"]
    return any(path.startswith(prefix) for prefix in prefixes)


def _git_blob_bytes(repository_root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "cat-file", "blob", f"{commit}:{path}"],
        check=False,
        capture_output=True,
    )
    _require(result.returncode == 0, "reference:git_blob_missing")
    return result.stdout


def _check_reference(
    value: Any,
    *,
    field: str,
    repository_root: Path,
    event_paths: dict[str, Path],
    schema: dict[str, Any],
) -> dict[str, str]:
    reference = _reference(value, field=field)
    path = reference["path"]
    if reference["kind"] == "workspace_file":
        _require(_allowed_workspace_path(path, schema), f"{field}:path_not_allowed")
        target = event_paths.get(path)
        if target is None:
            target = _safe_workspace_path(repository_root, path)
        _require(target.is_file(), f"{field}:missing")
        data = target.read_bytes()
    else:
        allowed = schema["reference_contract"]["git_blob_allowed_paths"]
        _require(path in allowed, f"{field}:git_blob_path_not_allowed")
        data = _git_blob_bytes(repository_root, reference["commit"], path)
    _require(sha256_bytes(data) == reference["sha256"], f"{field}:sha256_mismatch")
    return reference


def _field(document: Any, dotted_path: str) -> Any:
    value = document
    for key in dotted_path.split("."):
        _require(
            isinstance(value, dict) and key in value,
            f"budget_source:missing:{dotted_path}",
        )
        value = value[key]
    return value


def validate_schema(document: Any) -> dict[str, Any]:
    _require(isinstance(document, dict), "schema:object_required")
    required = {
        "profile_id",
        "schema_profile_version",
        "status",
        "canonicalization",
        "immutability",
        "lifecycle",
        "checkpoint_budget_phases",
        "known_gates",
        "known_event_types",
        "known_unit_rules",
        "required_event_fields",
        "reference_contract",
        "authority_contract",
        "budget_profile",
        "index_profile",
        "current_population",
        "non_authorizations",
    }
    _require(set(document) == required, "schema:fields")
    _require(document["schema_profile_version"] == 1, "schema:version")
    lifecycle = document["lifecycle"]
    _require(
        lifecycle["ordered_states"]
        == [
            "declared",
            "authorized",
            "materialized",
            "validated",
            "committed",
            "credited",
        ],
        "schema:lifecycle_order",
    )
    _require(
        lifecycle["additional_states"] == ["rejected", "superseded", "stale"],
        "schema:additional_states",
    )
    phases = document["checkpoint_budget_phases"]
    _require(
        phases["exact_order"]
        == ["K0b-runtime-operational", "K0b-F15-exact-measurement"],
        "schema:phase_order",
    )
    _require(phases["chronological"] is True, "schema:phase_chronological")
    _require(phases["contiguous"] is True, "schema:phase_contiguous")
    _require(phases["non_overlapping"] is True, "schema:phase_non_overlapping")
    _require(phases["exhaustive"] is True, "schema:phase_exhaustive")
    _require(
        document["index_profile"]["authoritative"] is False,
        "schema:index_authority",
    )
    _require(
        document["index_profile"]["grants_authority_credit_or_runtime_effect"] is False,
        "schema:index_effect",
    )
    _require(
        document["non_authorizations"]["gate_closure"] is False,
        "schema:gate_closure",
    )
    _require(
        document["non_authorizations"]["runtime_authority"] is False,
        "schema:runtime",
    )
    return document


def _budget_input_digest(snapshot: dict[str, Any]) -> str:
    keys = (
        "assumed_mean_object_bytes",
        "forecast_worst_by_count_bytes",
        "max_publication_bytes",
        "nominal_expected_bytes",
        "runtime_phase_publications",
        "size_stressed_bytes",
        "worst_case_object_count",
    )
    payload = {key: snapshot.get(key) for key in keys}
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256_bytes(raw.encode("utf-8"))


def _validate_budget_sources(
    snapshot: dict[str, Any],
    *,
    schema: dict[str, Any],
    repository_root: Path,
    event_paths: dict[str, Path],
) -> None:
    provenance = snapshot.get("source_provenance")
    expected = schema["budget_profile"]["provenance_sources"]
    _require(
        isinstance(provenance, dict) and set(provenance) == set(expected),
        "budget:source_set",
    )
    documents: dict[str, Any] = {}
    for name, bound in expected.items():
        reference = _check_reference(
            provenance[name],
            field=f"budget:source:{name}",
            repository_root=repository_root,
            event_paths=event_paths,
            schema=schema,
        )
        _require(reference["path"] == bound["path"], f"budget:source_path:{name}")
        _require(reference["sha256"] == bound["sha256"], f"budget:source_sha256:{name}")
        documents[name] = load_yaml(
            _safe_workspace_path(repository_root, reference["path"])
        )

    updated = documents["updated_forecast_v3"]
    reconciled = documents["forecast_binary_reconciliation_v3"]
    recalculation = documents["binary_size_recalculation_v1"]
    values = {
        "nominal_expected_bytes": _field(
            updated, "binary_budget_preserved.seed_bytes_nested.nominal"
        ),
        "forecast_worst_by_count_bytes": _field(
            updated, "binary_budget_preserved.seed_bytes_nested.worst_case"
        ),
        "max_publication_bytes": _field(
            recalculation, "selected_inputs.non_binary_worst_bytes"
        ),
        "worst_case_object_count": _field(
            recalculation, "selected_inputs.worst_case_object_count"
        ),
        "runtime_phase_publications": _field(
            recalculation,
            "selected_inputs.K0b_runtime_operational_phase_publications",
        ),
        "size_stressed_bytes": _field(
            recalculation, "exact_calculation.size_stressed_binary_bytes"
        ),
    }
    _require(
        _field(
            reconciled,
            "preserved_B01_D04_and_call_budget.binary_seed_bytes.nominal",
        )
        == values["nominal_expected_bytes"],
        "budget:nominal_source_disagreement",
    )
    _require(
        _field(
            reconciled,
            "preserved_B01_D04_and_call_budget.binary_seed_bytes.worst_case",
        )
        == values["forecast_worst_by_count_bytes"],
        "budget:worst_source_disagreement",
    )
    for document, field_path in (
        (updated, "binary_budget_preserved.logical_seed_count.worst_case"),
        (
            reconciled,
            "preserved_B01_D04_and_call_budget.binary_seed_count.worst_case",
        ),
    ):
        _require(
            _field(document, field_path) == values["worst_case_object_count"],
            "budget:count_source_disagreement",
        )
    for document, field_path in (
        (
            updated,
            "checkpoint_budget_phase_forecasts.K0b-runtime-operational.publications.worst_case",
        ),
        (
            reconciled,
            "phase_arithmetic.K0b-runtime-operational.publications.worst_case",
        ),
    ):
        _require(
            _field(document, field_path) == values["runtime_phase_publications"],
            "budget:publication_source_disagreement",
        )
    values["assumed_mean_object_bytes"] = values["nominal_expected_bytes"] // 6
    _require(
        values["forecast_worst_by_count_bytes"] // values["worst_case_object_count"]
        == values["assumed_mean_object_bytes"],
        "budget:mean_derivation",
    )
    for key, value in values.items():
        _require(snapshot.get(key) == value, f"budget:value:{key}")


def validate_budget_snapshot(
    snapshot: Any,
    *,
    schema: dict[str, Any],
    schema_path: Path,
    schema_digest: str,
    repository_root: Path,
    event_paths: dict[str, Path],
    resulting_state: str,
) -> None:
    _require(isinstance(snapshot, dict), "budget:object_required")
    required = {
        "assumed_mean_object_bytes",
        "nominal_expected_bytes",
        "forecast_worst_by_count_bytes",
        "size_stressed_bytes",
        "max_publication_bytes",
        "worst_case_object_count",
        "runtime_phase_publications",
        "input_provenance",
        "source_provenance",
        "input_sha256",
        "runtime_phase_publications_reforecast_sensitive",
        "f15_authoritative_worst_case_object_count",
        "f15_authority",
        "f15_size_stress_claim",
        "phase_completion_claim",
    }
    _require(set(snapshot) == required, "budget:fields")
    expected_values = schema["budget_profile"]["required_snapshot_values"]
    changed = any(snapshot.get(key) != value for key, value in expected_values.items())
    if changed:
        _require(
            resulting_state == "stale"
            and snapshot.get("runtime_phase_publications_reforecast_sensitive") is True,
            "budget:reforecast_sensitive_change_not_staled",
        )
    provenance = _check_reference(
        snapshot["input_provenance"],
        field="budget:input_provenance",
        repository_root=repository_root,
        event_paths=event_paths,
        schema=schema,
    )
    canonical_schema_path = "new pipeline/ledger/k0b01/schema-profile-v1.yaml"
    _require(provenance["path"] == canonical_schema_path, "budget:schema_path")
    _require(provenance["sha256"] == schema_digest, "budget:schema_sha256")
    _validate_budget_sources(
        snapshot,
        schema=schema,
        repository_root=repository_root,
        event_paths=event_paths,
    )
    _require(
        snapshot["input_sha256"] == _budget_input_digest(snapshot),
        "budget:input_sha256",
    )
    _require(
        snapshot["runtime_phase_publications_reforecast_sensitive"] is True,
        "budget:reforecast_sensitive",
    )
    if snapshot["f15_authoritative_worst_case_object_count"] is None:
        _require(snapshot["f15_authority"] is None, "budget:f15_authority")
        _require(snapshot["f15_size_stress_claim"] is False, "budget:f15_size_claim")
        _require(snapshot["phase_completion_claim"] is False, "budget:phase_completion")
    _require(schema_path.is_file(), "budget:schema_missing")


def _validate_event_shape(
    event: Any,
    *,
    schema: dict[str, Any],
    schema_path: Path,
    schema_digest: str,
    repository_root: Path,
    event_paths: dict[str, Path],
) -> None:
    _require(isinstance(event, dict), "event:object_required")
    _require(set(event) == set(schema["required_event_fields"]), "event:fields")
    _require(
        event["schema_profile_version"] == schema["schema_profile_version"],
        "event:schema_version",
    )
    _require(
        isinstance(event["event_id"], str)
        and EVENT_ID_RE.fullmatch(event["event_id"]) is not None,
        "event:id",
    )
    _require(event["gate_id"] in schema["known_gates"], "event:unknown_gate")
    unit = event["unit_id"]
    units = schema["known_unit_rules"]
    _require(
        unit in units["exact_units"]
        or (isinstance(unit, str) and unit.startswith(units["incident_prefix"])),
        "event:unknown_unit",
    )
    _require(event["event_type"] in schema["known_event_types"], "event:unknown_type")
    states = (
        schema["lifecycle"]["ordered_states"] + schema["lifecycle"]["additional_states"]
    )
    _require(event["resulting_state"] in states, "event:unknown_state")
    _require(
        event["checkpoint_budget_phase"]
        in schema["checkpoint_budget_phases"]["exact_order"],
        "event:unknown_phase",
    )
    for field in ("dependencies", "artifacts", "evidence"):
        _require(isinstance(event[field], list), f"event:{field}:list_required")

    authority = event["materialization_authority"]
    _require(
        isinstance(authority, dict) and set(authority) == {"request", "confirmation"},
        "event:materialization_authority",
    )
    request = _check_reference(
        authority["request"],
        field="event:materialization_request",
        repository_root=repository_root,
        event_paths=event_paths,
        schema=schema,
    )
    _require(request["path"].startswith("new pipeline/requests/"), "event:request_path")
    confirmation = authority["confirmation"]
    required_confirmation = set(schema["authority_contract"]["confirmation_fields"])
    _require(
        isinstance(confirmation, dict) and set(confirmation) == required_confirmation,
        "event:confirmation",
    )
    _require(
        confirmation["repeated_request_sha256"] == request["sha256"],
        "event:confirmation_sha256",
    )
    _require(confirmation["exact_match"] is True, "event:confirmation_exact_match")
    _require(
        confirmation["exact_scope_authorized"] is True,
        "event:materialized_without_exact_authority",
    )
    _require(
        confirmation["actor"] == schema["authority_contract"]["required_actor"],
        "event:owner_authority",
    )
    _require(
        isinstance(confirmation["source"], str) and bool(confirmation["source"]),
        "event:confirmation_source",
    )

    _check_reference(
        event["subject_authority"],
        field="event:subject_authority",
        repository_root=repository_root,
        event_paths=event_paths,
        schema=schema,
    )

    historical = event["historical"]
    required_historical = {
        "recorder",
        "classification",
        "containing_commit",
        "gate_closed",
        "implementation_authority",
        "runtime_authority",
    }
    _require(
        isinstance(historical, dict) and set(historical) == required_historical,
        "event:historical",
    )
    _require(
        isinstance(historical["recorder"], str) and bool(historical["recorder"]),
        "event:recorder",
    )
    _require(
        historical["recorder"] != confirmation["actor"],
        "event:self_authorization",
    )
    _require(
        isinstance(historical["classification"], str)
        and bool(historical["classification"]),
        "event:classification",
    )
    _require(
        historical["containing_commit"] is None
        or _valid_commit(historical["containing_commit"]),
        "event:containing_commit",
    )
    _require(isinstance(historical["gate_closed"], bool), "event:gate_closed")
    _require(
        historical["runtime_authority"] == "none",
        "event:runtime_authority_forbidden",
    )

    evidence_paths = []
    for collection in ("dependencies", "artifacts", "evidence"):
        seen: set[tuple[str, str, str]] = set()
        for index, value in enumerate(event[collection]):
            reference = _reference(value, field=f"event:{collection}:{index}")
            identity = (
                reference["kind"],
                reference.get("commit", ""),
                reference["path"],
            )
            if collection == "evidence":
                evidence_paths.append(identity)
            if collection == "evidence" and identity in seen:
                raise LedgerError("zero_credit:ambiguous_evidence")
            _require(identity not in seen, f"event:{collection}:ambiguous_reference")
            seen.add(identity)
            _check_reference(
                value,
                field=f"event:{collection}:{index}",
                repository_root=repository_root,
                event_paths=event_paths,
                schema=schema,
            )

    credit = event["credit"]
    _require(
        isinstance(credit, dict) and set(credit) == {"eligible", "value"},
        "event:credit",
    )
    _require(
        isinstance(credit["eligible"], bool) and credit["value"] in (0, 1),
        "event:credit_values",
    )
    if event["resulting_state"] == "credited":
        if not event["evidence"]:
            raise LedgerError("zero_credit:missing_evidence")
        if len(evidence_paths) != len(set(evidence_paths)):
            raise LedgerError("zero_credit:ambiguous_evidence")
        _require(credit == {"eligible": True, "value": 1}, "event:credited_value")
    else:
        _require(credit == {"eligible": False, "value": 0}, "event:premature_credit")

    reason = event["reason"]
    _require(
        isinstance(reason, dict)
        and set(reason) == {"zero_credit", "stale", "rejection", "supersession"},
        "event:reason",
    )
    state = event["resulting_state"]
    if state == "rejected":
        _require(
            isinstance(reason["rejection"], str) and bool(reason["rejection"]),
            "event:rejection_reason",
        )
    if state == "superseded":
        _require(
            isinstance(reason["supersession"], str) and bool(reason["supersession"]),
            "event:supersession_reason",
        )
    if state == "stale":
        _require(
            isinstance(reason["stale"], str) and bool(reason["stale"]),
            "event:stale_reason",
        )

    validate_budget_snapshot(
        event["budget_snapshot"],
        schema=schema,
        schema_path=schema_path,
        schema_digest=schema_digest,
        repository_root=repository_root,
        event_paths=event_paths,
        resulting_state=state,
    )


def _logical_event_paths(events_path: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(events_path.glob("*.yaml"), key=lambda item: item.name):
        logical = EVENT_PATH_PREFIX + path.name
        _require(logical not in paths, "event:duplicate_path")
        paths[logical] = path
    return paths


def load_and_validate_events(
    schema_path: Path, events_path: Path, repository_root: Path
) -> list[tuple[str, str, dict[str, Any]]]:
    schema = validate_schema(load_yaml(schema_path))
    schema_digest = sha256_bytes(schema_path.read_bytes())
    event_paths = _logical_event_paths(events_path)
    _require(bool(event_paths), "event:empty_population")

    loaded: list[tuple[str, str, dict[str, Any]]] = []
    ids: dict[str, str] = {}
    for logical_path, physical_path in event_paths.items():
        event = load_yaml(physical_path)
        _require(isinstance(event, dict), "event:object_required")
        event_id = event.get("event_id")
        _require(isinstance(event_id, str), "event:id")
        _require(event_id not in ids, "event:duplicate_event_id")
        ids[event_id] = logical_path
        _require(physical_path.name == f"{event_id}.yaml", "event:filename_mismatch")
        loaded.append((logical_path, sha256_bytes(physical_path.read_bytes()), event))

    for _, _, event in loaded:
        _validate_event_shape(
            event,
            schema=schema,
            schema_path=schema_path,
            schema_digest=schema_digest,
            repository_root=repository_root,
            event_paths=event_paths,
        )

    by_path = {path: event for path, _, event in loaded}
    lifecycle = schema["lifecycle"]["ordered_states"]
    additional = schema["lifecycle"]["additional_states"]
    states_by_unit: dict[str, list[str]] = {}
    phase_indexes: list[int] = []
    phases = schema["checkpoint_budget_phases"]["exact_order"]
    for _, _, event in loaded:
        predecessor = event["predecessor"]
        state = event["resulting_state"]
        phase_indexes.append(phases.index(event["checkpoint_budget_phase"]))
        if predecessor is None:
            _require(state == "declared", "event:root_must_be_declared")
            _require(event["unit_id"] not in states_by_unit, "event:duplicate_root")
        else:
            reference = _check_reference(
                predecessor,
                field="event:predecessor",
                repository_root=repository_root,
                event_paths=event_paths,
                schema=schema,
            )
            _require(reference["path"] in by_path, "event:broken_predecessor")
            prior = by_path[reference["path"]]
            _require(prior["unit_id"] == event["unit_id"], "event:predecessor_unit")
            prior_state = prior["resulting_state"]
            if state in lifecycle:
                _require(
                    prior_state in lifecycle,
                    "event:invalid_lifecycle_predecessor",
                )
                expected = lifecycle.index(prior_state) + 1
                _require(
                    expected < len(lifecycle) and lifecycle[expected] == state,
                    "event:skipped_required_state",
                )
            else:
                _require(state in additional, "event:unknown_state")
                _require(prior_state not in additional, "event:terminal_predecessor")
        states_by_unit.setdefault(event["unit_id"], []).append(state)

    _require(phase_indexes[0] == 0, "phase:gap")
    seen_f15 = False
    for index in phase_indexes:
        if index == 1:
            seen_f15 = True
        elif seen_f15:
            raise LedgerError("phase:nonchronological_or_overlap")

    human = states_by_unit.get("K0B01-HUMAN-SIGNOFF")
    _require(human == lifecycle, "population:human_signoff_chain")
    return loaded


def validation_summary(
    records: list[tuple[str, str, dict[str, Any]]],
) -> dict[str, Any]:
    human_states = [
        event["resulting_state"]
        for _, _, event in records
        if event["unit_id"] == "K0B01-HUMAN-SIGNOFF"
    ]
    incidents = [
        event
        for _, _, event in records
        if event["event_type"] == "historical_incident_disclosure"
    ]
    invocations = [
        event
        for _, _, event in records
        if event["event_type"] == "implementation_invocation"
    ]
    closed_gates = sorted(
        {
            event["gate_id"]
            for _, _, event in records
            if event["historical"]["gate_closed"] is True
        }
    )
    return {
        "closed_gates": closed_gates,
        "credited_event_count": sum(
            event["credit"]["value"] for _, _, event in records
        ),
        "event_count": len(records),
        "human_signoff_state": human_states[-1] if human_states else None,
        "implementation_invocation_count": len(invocations),
        "incident_count": len(incidents),
        "result": "pass",
        "runtime_authorized": any(
            event["historical"]["runtime_authority"] != "none"
            for _, _, event in records
        ),
    }


def index_document(
    records: list[tuple[str, str, dict[str, Any]]],
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repository_root: Path = DEFAULT_REPOSITORY_ROOT,
) -> dict[str, Any]:
    schema_relative = "new pipeline/ledger/k0b01/schema-profile-v1.yaml"
    validator_relative = "new pipeline/ledger/k0b01/ledger.py"
    validator_path = _safe_workspace_path(repository_root, validator_relative)
    return {
        "index_id": "pipeline-v2.k0b01-ledger-index-v1",
        "generated_index_authoritative": False,
        "grants_authority_credit_or_runtime_effect": False,
        "schema_profile": {
            "path": schema_relative,
            "sha256": sha256_bytes(schema_path.read_bytes()),
        },
        "validator": {
            "path": validator_relative,
            "sha256": sha256_bytes(validator_path.read_bytes()),
        },
        "event_count": len(records),
        "events": [
            {
                "event_id": event["event_id"],
                "event_path": path,
                "event_sha256": digest,
                "unit_id": event["unit_id"],
                "gate_id": event["gate_id"],
                "checkpoint_budget_phase": event["checkpoint_budget_phase"],
                "event_type": event["event_type"],
                "resulting_state": event["resulting_state"],
                "credit_eligible": event["credit"]["eligible"],
                "credit_value": event["credit"]["value"],
                "dependency_count": len(event["dependencies"]),
                "artifact_count": len(event["artifacts"]),
                "evidence_count": len(event["evidence"]),
            }
            for path, digest, event in records
        ],
    }


def _command(args: argparse.Namespace) -> int:
    try:
        records = load_and_validate_events(
            args.schema, args.events, args.repository_root
        )
        if args.command == "validate":
            _write_output(args.output, _json_bytes(validation_summary(records)))
            return SUCCESS
        expected = dump_yaml_bytes(
            index_document(
                records,
                schema_path=args.schema,
                repository_root=args.repository_root,
            )
        )
        if args.command == "build-index":
            _write_output(args.output, expected)
            return SUCCESS
        actual = args.index.read_bytes()
        result = {
            "actual_sha256": sha256_bytes(actual),
            "expected_sha256": sha256_bytes(expected),
            "result": "pass" if actual == expected else "stale",
        }
        _write_output(args.output, _json_bytes(result))
        return SUCCESS if actual == expected else INDEX_STALE
    except LedgerError as exc:
        _write_output(
            args.output,
            _json_bytes({"error": str(exc), "result": "fail_closed"}),
        )
        return VALIDATION_FAILED


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "build-index", "check-index"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--schema", type=Path, required=True)
        sub.add_argument("--events", type=Path, required=True)
        sub.add_argument("--repository-root", type=Path, required=True)
        sub.add_argument("--output", type=Path, required=True)
        if command == "check-index":
            sub.add_argument("--index", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    return _command(_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
