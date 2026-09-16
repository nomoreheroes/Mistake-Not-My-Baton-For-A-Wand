from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


SUCCESS = 0
VALIDATION_ERROR = 1
INVALID_INPUT = 2
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[/\\]")
_PROFILE_FIELDS = {
    "profile_id",
    "schema_version",
    "status",
    "projection_version",
    "repository_paths",
    "source_contract",
    "record_contracts",
    "reference_contract",
    "gate_contract",
    "document_contract",
    "canonicalization",
    "cli_contract",
    "non_authorizations",
}
_SOURCE_TOP_LEVEL_ORDER = [
    "state_id",
    "schema_version",
    "projection_version",
    "generated_at",
    "status",
    "projection_profile",
    "baseline",
    "active_authority",
    "supporting_review_evidence",
    "root_plan_status",
    "work_items",
    "open_gates",
    "closed_gates",
    "status_index",
    "scope",
]


class RendererError(Exception):
    pass


def _fail(code: str) -> None:
    raise RendererError(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        _fail(code)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_utf8_lf(path: Path, *, label: str) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RendererError(f"{label}:read:{exc.__class__.__name__}") from exc
    _require(not data.startswith(b"\xef\xbb\xbf"), f"{label}:BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RendererError(f"{label}:UTF8") from exc
    _require("\r" not in text, f"{label}:line_endings")
    _require(text.endswith("\n") and not text.endswith("\n\n"), f"{label}:final_LF")
    return data, text


def _load_yaml_text(text: str, *, label: str) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    try:
        document = yaml.load(text)
    except Exception as exc:
        raise RendererError(f"{label}:YAML") from exc
    _require(isinstance(document, dict), f"{label}:object")
    return document


def _shape(value: Any) -> Any:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return {"sequence": [_shape(item) for item in value]}
    if isinstance(value, dict):
        return {"mapping": [[key, _shape(item)] for key, item in value.items()]}
    _fail("source:unsupported_scalar")


def shape_digest(document: dict[str, Any]) -> str:
    payload = json.dumps(
        _shape(document),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def load_profile(path: Path) -> tuple[dict[str, Any], str]:
    data, text = _read_utf8_lf(path, label="profile")
    profile = _load_yaml_text(text, label="profile")
    _require(set(profile) == _PROFILE_FIELDS, "profile:fields")
    _require(
        profile["profile_id"] == "pipeline-v2.state-projection-profile-v2", "profile:id"
    )
    _require(profile["schema_version"] == 1, "profile:schema_version")
    _require(profile["status"] == "active", "profile:status")
    _require(profile["projection_version"] == "2.0.0", "profile:projection_version")
    paths = profile["repository_paths"]
    _require(
        isinstance(paths, dict) and set(paths) == {"source", "projection", "profile"},
        "profile:repository_paths",
    )
    _require(
        paths["source"] == "new pipeline/state/state.yaml"
        and paths["projection"] == "new pipeline/state/STATE.md"
        and paths["profile"]
        == "new pipeline/state/renderer/k0b01/projection-profile-v2.yaml",
        "profile:repository_path_values",
    )
    source_contract = profile["source_contract"]
    _require(
        isinstance(source_contract, dict)
        and set(source_contract)
        == {
            "supported_schema_versions",
            "exact_top_level_order",
            "allowed_shape_sha256",
            "absolute_host_paths",
            "mapping_order",
            "unknown_fields",
        },
        "profile:source_contract",
    )
    _require(
        source_contract["supported_schema_versions"] == [1], "profile:source_versions"
    )
    _require(
        source_contract["exact_top_level_order"] == _SOURCE_TOP_LEVEL_ORDER,
        "profile:source_field_coverage",
    )
    shapes = source_contract["allowed_shape_sha256"]
    _require(
        isinstance(shapes, list)
        and len(shapes) == 3
        and len(set(shapes)) == 3
        and all(
            isinstance(item, str) and _SHA256_RE.fullmatch(item) for item in shapes
        ),
        "profile:shape_hashes",
    )
    _require(
        source_contract["absolute_host_paths"] == "forbidden", "profile:absolute_paths"
    )
    _require(
        source_contract["mapping_order"] == "profile_exact", "profile:mapping_order"
    )
    _require(
        source_contract["unknown_fields"] == "fail_closed", "profile:unknown_fields"
    )
    _validate_profile_contracts(profile)
    return profile, _sha256_bytes(data)


def _validate_profile_contracts(profile: dict[str, Any]) -> None:
    records = profile["record_contracts"]
    _require(
        isinstance(records, dict)
        and set(records) == {"work_item", "open_gate", "closed_gate", "status_index"},
        "profile:record_contracts",
    )
    for name, contract in records.items():
        _require(
            isinstance(contract, dict)
            and set(contract) == {"required_fields", "optional_fields"},
            f"profile:{name}_contract",
        )
        required = contract["required_fields"]
        optional = contract["optional_fields"]
        _require(
            isinstance(required, list)
            and isinstance(optional, list)
            and all(isinstance(item, str) for item in required + optional)
            and not set(required).intersection(optional),
            f"profile:{name}_fields",
        )
    references = profile["reference_contract"]
    _require(
        references
        == {
            "digest": "SHA-256",
            "path_style": "repository_relative_forward_slash",
            "missing_path": "fail_closed",
            "hash_mismatch": "fail_closed",
        },
        "profile:reference_contract",
    )
    gates = profile["gate_contract"]
    _require(
        isinstance(gates, dict)
        and set(gates)
        == {
            "open_statuses",
            "closed_status",
            "cross_set_overlap",
            "work_item_reference",
        },
        "profile:gate_contract",
    )
    _require(
        gates["closed_status"] == "closed"
        and gates["cross_set_overlap"] == "forbidden"
        and gates["work_item_reference"] == "required",
        "profile:gate_values",
    )
    _require(
        gates["open_statuses"]
        == [
            "open_blocking",
            "blocked_by_predecessor",
            "future_open",
            "blocked_by_predecessors",
        ],
        "profile:open_gate_statuses",
    )
    document = profile["document_contract"]
    _require(
        isinstance(document, dict)
        and set(document)
        == {"heading", "notice", "normative_body", "fence", "preamble_order"},
        "profile:document_contract",
    )
    _require(
        document["heading"] == "# Pipeline v2 state projection"
        and document["notice"]
        == "Generated projection; do not edit this file directly."
        and document["normative_body"] == "complete_source_YAML_bytes"
        and document["fence"] == "yaml",
        "profile:document_values",
    )
    _require(
        document["preamble_order"]
        == [
            "heading",
            "source_path",
            "source_sha256",
            "profile_path",
            "profile_sha256",
            "projection_version",
            "notice",
            "normative_body",
        ],
        "profile:preamble_order",
    )
    canonical = profile["canonicalization"]
    _require(
        canonical
        == {
            "encoding": "UTF-8-without-BOM",
            "line_endings": "LF",
            "final_newline_count": 1,
            "timestamps_in_output": "source_values_only",
            "environment_values_in_output": "forbidden",
            "locale_values_in_output": "forbidden",
        },
        "profile:canonicalization",
    )
    cli = profile["cli_contract"]
    _require(
        cli
        == {
            "modes": ["render", "check"],
            "render_output": "explicit_required",
            "check_mode_writes": False,
            "success_exit_code": 0,
            "validation_error_exit_code": 1,
            "invalid_input_exit_code": 2,
        },
        "profile:cli_contract",
    )


def _validate_record_fields(
    records: Any,
    *,
    name: str,
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    _require(isinstance(records, list), f"source:{name}_list")
    required = set(contract["required_fields"])
    allowed = required.union(contract["optional_fields"])
    for record in records:
        _require(isinstance(record, dict), f"source:{name}_record")
        keys = set(record)
        _require(
            required.issubset(keys) and keys.issubset(allowed), f"source:{name}_fields"
        )
    return records


def _validate_identifiers_and_gates(
    document: dict[str, Any], profile: dict[str, Any]
) -> None:
    contracts = profile["record_contracts"]
    work_items = _validate_record_fields(
        document["work_items"], name="work_item", contract=contracts["work_item"]
    )
    open_gates = _validate_record_fields(
        document["open_gates"], name="open_gate", contract=contracts["open_gate"]
    )
    closed_gates = _validate_record_fields(
        document["closed_gates"], name="closed_gate", contract=contracts["closed_gate"]
    )
    _validate_record_fields(
        document["status_index"],
        name="status_index",
        contract=contracts["status_index"],
    )

    sequences = [item["sequence"] for item in work_items]
    _require(
        all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in sequences
        ),
        "source:sequence_type",
    )
    _require(len(sequences) == len(set(sequences)), "source:duplicate_sequence")
    _require(sequences == sorted(sequences), "source:sequence_order")

    work_ids = [item["work_item_id"] for item in work_items]
    _require(
        all(isinstance(value, str) for value in work_ids), "source:work_item_id_type"
    )
    _require(len(work_ids) == len(set(work_ids)), "source:duplicate_work_item_id")

    open_ids = [item["gate_id"] for item in open_gates]
    closed_ids = [item["gate_id"] for item in closed_gates]
    _require(
        all(isinstance(value, str) for value in open_ids + closed_ids),
        "source:gate_id_type",
    )
    _require(len(open_ids) == len(set(open_ids)), "source:duplicate_open_gate_id")
    _require(len(closed_ids) == len(set(closed_ids)), "source:duplicate_closed_gate_id")
    _require(not set(open_ids).intersection(closed_ids), "source:gate_overlap")
    _require(open_ids == sorted(open_ids), "source:open_gate_order")

    allowed_open_statuses = profile["gate_contract"]["open_statuses"]
    _require(
        all(item["status"] in allowed_open_statuses for item in open_gates),
        "source:open_gate_status",
    )
    _require(
        all(
            item["status"] == profile["gate_contract"]["closed_status"]
            for item in closed_gates
        ),
        "source:closed_gate_status",
    )
    for item in work_items:
        gate_ids = item["open_gate_ids"]
        _require(isinstance(gate_ids, list), "source:work_item_gates_list")
        _require(len(gate_ids) == len(set(gate_ids)), "source:work_item_gate_duplicate")
        _require(
            all(gate_id in open_ids for gate_id in gate_ids),
            "source:work_item_gate_missing",
        )
    k0b01 = [item for item in work_items if item["work_item_id"] == "K0b-01"]
    if k0b01:
        expected = [gate_id for gate_id in open_ids if gate_id.startswith("G-K0B01-")]
        _require(k0b01[0]["open_gate_ids"] == expected, "source:K0b_01_gate_projection")


def _resolve_repository_path(repository_root: Path, value: str) -> Path:
    _require(
        value != "" and "\\" not in value and not value.startswith("/"),
        "source:path_style",
    )
    _require(not _DRIVE_PATH_RE.match(value), "source:absolute_path")
    root = repository_root.resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RendererError("source:path_escape") from exc
    return candidate


def _validate_reference(
    path_value: Any, hash_value: Any, repository_root: Path
) -> None:
    _require(isinstance(path_value, str), "source:reference_path_type")
    _require(
        isinstance(hash_value, str) and _SHA256_RE.fullmatch(hash_value),
        "source:reference_hash_type",
    )
    candidate = _resolve_repository_path(repository_root, path_value)
    _require(candidate.is_file(), "source:reference_missing")
    _require(
        _sha256_bytes(candidate.read_bytes()) == hash_value, "source:reference_hash"
    )


def _walk_references(value: Any, repository_root: Path) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            _validate_reference(value["path"], value["sha256"], repository_root)
        for item in value.values():
            _walk_references(item, repository_root)
    elif isinstance(value, list):
        for item in value:
            _walk_references(item, repository_root)
    elif isinstance(value, str):
        _require(not _DRIVE_PATH_RE.match(value), "source:absolute_path")


def validate_source(
    document: dict[str, Any],
    *,
    profile: dict[str, Any],
    profile_sha256: str,
    repository_root: Path,
) -> None:
    source_contract = profile["source_contract"]
    expected_top = source_contract["exact_top_level_order"]
    _require(list(document) == expected_top, "source:top_fields")
    _require(
        isinstance(document["schema_version"], int)
        and not isinstance(document["schema_version"], bool)
        and document["schema_version"] in source_contract["supported_schema_versions"],
        "source:schema_version",
    )
    _require(
        document["projection_version"] == profile["projection_version"],
        "source:projection_version",
    )
    projection_profile = document["projection_profile"]
    _require(
        isinstance(projection_profile, dict)
        and set(projection_profile) == {"path", "sha256"},
        "source:projection_profile_fields",
    )
    _require(
        projection_profile["path"] == profile["repository_paths"]["profile"],
        "source:projection_profile_path",
    )
    _require(
        projection_profile["sha256"] == profile_sha256, "source:projection_profile_hash"
    )
    _validate_identifiers_and_gates(document, profile)
    _walk_references(document, repository_root)
    for work_item in document["work_items"]:
        _validate_reference(
            work_item["authority_path"],
            work_item["authority_sha256"],
            repository_root,
        )
    _require(
        shape_digest(document) in source_contract["allowed_shape_sha256"],
        "source:shape",
    )


def _preamble(
    *,
    profile: dict[str, Any],
    profile_sha256: str,
    source_sha256: str,
) -> str:
    paths = profile["repository_paths"]
    document = profile["document_contract"]
    return (
        f"{document['heading']}\n\n"
        f"Source: `{paths['source']}`\n\n"
        f"Source SHA-256: `{source_sha256}`\n\n"
        f"Projection profile: `{paths['profile']}`\n\n"
        f"Projection profile SHA-256: `{profile_sha256}`\n\n"
        f"Projection version: `{profile['projection_version']}`\n\n"
        f"{document['notice']}\n\n"
        f"```{document['fence']}\n"
    )


def render_bytes(
    *,
    source_path: Path,
    profile_path: Path,
    repository_root: Path,
) -> tuple[bytes, dict[str, str]]:
    source_data, source_text = _read_utf8_lf(source_path, label="source")
    _require("```" not in source_text, "source:fence_collision")
    source = _load_yaml_text(source_text, label="source")
    profile, profile_sha256 = load_profile(profile_path)
    validate_source(
        source,
        profile=profile,
        profile_sha256=profile_sha256,
        repository_root=repository_root,
    )
    source_sha256 = _sha256_bytes(source_data)
    output = (
        _preamble(
            profile=profile,
            profile_sha256=profile_sha256,
            source_sha256=source_sha256,
        )
        + source_text
        + "```\n"
    ).encode("utf-8")
    return output, {
        "profile_sha256": profile_sha256,
        "projection_sha256": _sha256_bytes(output),
        "source_sha256": source_sha256,
    }


def check_projection(
    *,
    source_path: Path,
    profile_path: Path,
    projection_path: Path,
    repository_root: Path,
) -> dict[str, str]:
    expected, summary = render_bytes(
        source_path=source_path,
        profile_path=profile_path,
        repository_root=repository_root,
    )
    actual, actual_text = _read_utf8_lf(projection_path, label="projection")
    _require(actual == expected, "projection:byte_mismatch")

    _, source_text = _read_utf8_lf(source_path, label="source")
    profile, profile_sha256 = load_profile(profile_path)
    prefix = _preamble(
        profile=profile,
        profile_sha256=profile_sha256,
        source_sha256=summary["source_sha256"],
    )
    _require(
        actual_text.startswith(prefix) and actual_text.endswith("```\n"),
        "projection:structure",
    )
    embedded = actual_text[len(prefix) : -4]
    _require(embedded == source_text, "projection:embedded_bytes")
    embedded_document = _load_yaml_text(embedded, label="projection_body")
    source_document = _load_yaml_text(source_text, label="source")
    _require(embedded_document == source_document, "projection:semantic_mismatch")
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="state-renderer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("render", "check"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--profile", type=Path, required=True)
        subparser.add_argument("--source", type=Path, required=True)
        subparser.add_argument("--repository-root", type=Path, required=True)
        if command == "render":
            subparser.add_argument("--output", type=Path, required=True)
        else:
            subparser.add_argument("--projection", type=Path, required=True)
    return parser


def _emit(summary: dict[str, str]) -> None:
    payload = {"result": "pass", **summary}
    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "render":
            _require(
                args.output.resolve()
                not in {args.source.resolve(), args.profile.resolve()},
                "output:input_collision",
            )
            output, summary = render_bytes(
                source_path=args.source,
                profile_path=args.profile,
                repository_root=args.repository_root,
            )
            try:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(output)
            except OSError as exc:
                raise RendererError(f"output:write:{exc.__class__.__name__}") from exc
            _emit(summary)
            return SUCCESS
        summary = check_projection(
            source_path=args.source,
            profile_path=args.profile,
            projection_path=args.projection,
            repository_root=args.repository_root,
        )
        _emit(summary)
        return SUCCESS
    except RendererError as exc:
        sys.stderr.write(str(exc) + "\n")
        return VALIDATION_ERROR
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"invalid_input:{exc.__class__.__name__}\n")
        return INVALID_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
