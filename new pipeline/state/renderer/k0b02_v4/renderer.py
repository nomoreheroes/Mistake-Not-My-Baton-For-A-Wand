from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
from datetime import datetime, timezone
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.tokens import AliasToken, AnchorToken


SHA = re.compile(r"^[0-9a-f]{64}$")
DRIVE = re.compile(r"^[A-Za-z]:[/\\]")


class RendererError(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RendererError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path, label: str) -> tuple[bytes, str]:
    reject_reparse(path, label)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RendererError(f"{label}:read") from exc
    require(not data.startswith(b"\xef\xbb\xbf"), f"{label}:BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RendererError(f"{label}:UTF8") from exc
    require("\r" not in text, f"{label}:line_endings")
    require(text.endswith("\n") and not text.endswith("\n\n"), f"{label}:final_LF")
    return data, text


def load_yaml(text: str, label: str) -> dict[str, Any]:
    yaml = YAML(typ="safe", pure=True)
    yaml.allow_duplicate_keys = False
    try:
        require(
            not any(isinstance(t, (AliasToken, AnchorToken)) for t in yaml.scan(text)),
            f"{label}:aliases",
        )
        value = yaml.load(text)
    except RendererError:
        raise
    except Exception as exc:
        raise RendererError(f"{label}:YAML") from exc
    require(isinstance(value, dict), f"{label}:object")
    return value


def validate_schema(
    schema: Any, depth: int, maximum: int, definitions: dict[str, Any]
) -> None:
    require(depth <= maximum and isinstance(schema, dict), "profile:schema")
    if "schema_ref" in schema:
        require(
            set(schema) == {"schema_ref"} and schema["schema_ref"] in definitions,
            "profile:schema_ref",
        )
        validate_schema(
            definitions[schema["schema_ref"]], depth + 1, maximum, definitions
        )
        return
    if "any_of" in schema:
        require(set(schema) == {"any_of"}, "profile:union_fields")
        require(
            isinstance(schema["any_of"], list) and schema["any_of"], "profile:union"
        )
        for item in schema["any_of"]:
            validate_schema(item, depth + 1, maximum, definitions)
        return
    kind = schema.get("type")
    if kind == "object":
        require(set(schema) == {"type", "properties", "required"}, "profile:object")
        props = schema["properties"]
        required = schema["required"]
        require(
            isinstance(props, dict) and isinstance(required, list), "profile:fields"
        )
        require(all(isinstance(k, str) for k in props), "profile:field_names")
        require(
            len(required) == len(set(required)) and set(required) <= set(props),
            "profile:required",
        )
        for child in props.values():
            validate_schema(child, depth + 1, maximum, definitions)
    elif kind == "array":
        require(set(schema) == {"type", "items"}, "profile:array")
        validate_schema(schema["items"], depth + 1, maximum, definitions)
    else:
        require(
            kind in {"string", "integer", "number", "boolean", "null"}, "profile:type"
        )
        require(set(schema) <= {"type", "pattern"}, "profile:scalar")
        if "pattern" in schema:
            require(
                kind == "string" and schema["pattern"] == SHA.pattern, "profile:pattern"
            )


def validate_value(
    value: Any, schema: dict[str, Any], location: str, definitions: dict[str, Any]
) -> None:
    code = f"source:schema:{location}"
    if "schema_ref" in schema:
        validate_value(value, definitions[schema["schema_ref"]], location, definitions)
        return
    if "any_of" in schema:
        for item in schema["any_of"]:
            try:
                validate_value(value, item, location, definitions)
                return
            except RendererError:
                continue
        raise RendererError(code)
    kind = schema["type"]
    if kind == "object":
        require(isinstance(value, dict), code)
        props = schema["properties"]
        require(set(schema["required"]) <= set(value) <= set(props), code)
        require(list(value) == [k for k in props if k in value], code + ":order")
        for key, item in value.items():
            validate_value(item, props[key], location + "/" + key, definitions)
    elif kind == "array":
        require(isinstance(value, list), code)
        for item in value:
            validate_value(item, schema["items"], location + "/*", definitions)
    elif kind == "string":
        require(isinstance(value, str), code)
        if "pattern" in schema:
            require(SHA.fullmatch(value) is not None, code + ":SHA")
    elif kind == "integer":
        require(type(value) is int, code)
    elif kind == "number":
        require(type(value) in {int, float} and math.isfinite(value), code)
    elif kind == "boolean":
        require(type(value) is bool, code)
    else:
        require(value is None, code)


def load_profile(path: Path) -> tuple[dict[str, Any], str]:
    data, text = read_text(path, "profile")
    profile = load_yaml(text, "profile")
    require(
        set(profile)
        == {
            "profile_id",
            "schema_version",
            "projection_version",
            "status",
            "repository_paths",
            "limits",
            "source_schema",
            "schema_definitions",
            "reference_contract",
            "gate_contract",
            "document_contract",
            "canonicalization",
            "cli_contract",
            "non_authorizations",
            "transition_contract",
        },
        "profile:fields",
    )
    require(
        profile["profile_id"] == "pipeline-v2.state-projection-profile-v4", "profile:id"
    )
    require(
        type(profile["schema_version"]) is int and profile["schema_version"] == 1,
        "profile:version",
    )
    require(
        profile["projection_version"] == "4.0.0" and profile["status"] == "active",
        "profile:status",
    )
    paths = profile["repository_paths"]
    require(
        paths
        == {
            "source": "new pipeline/state/state.yaml",
            "projection": "new pipeline/state/STATE.md",
            "profile": "new pipeline/state/renderer/k0b02_v4/projection-profile-v4.yaml",
        },
        "profile:paths",
    )
    limits = profile["limits"]
    require(
        set(limits) == {"maximum_schema_depth", "maximum_source_bytes"},
        "profile:limits",
    )
    require(
        all(type(v) is int and v > 0 for v in limits.values()), "profile:limit_values"
    )
    definitions = profile["schema_definitions"]
    require(isinstance(definitions, dict) and definitions, "profile:definitions")
    validate_schema(
        profile["source_schema"], 0, limits["maximum_schema_depth"], definitions
    )
    for node in definitions.values():
        validate_schema(node, 0, limits["maximum_schema_depth"], definitions)
    refs = profile["reference_contract"]
    require(
        set(refs) == {"allowed_repository_paths", "digest", "reparse_points"},
        "profile:references",
    )
    require(
        refs["digest"] == "SHA-256" and refs["reparse_points"] == "forbidden",
        "profile:reference_values",
    )
    allowed = refs["allowed_repository_paths"]
    require(
        isinstance(allowed, list) and len(allowed) == len(set(allowed)),
        "profile:allowlist",
    )
    require(
        all(isinstance(p, str) and p.startswith("new pipeline/") for p in allowed),
        "profile:allowlist_paths",
    )
    require(
        profile["canonicalization"]
        == {
            "encoding": "UTF-8-without-BOM",
            "line_endings": "LF",
            "final_newline_count": 1,
            "timestamps": "source_values_only",
            "environment_values": "forbidden",
        },
        "profile:canonicalization",
    )
    require(
        profile["cli_contract"]
        == {
            "modes": ["render", "check"],
            "render_output": "explicit_required",
            "check_mode_writes": False,
            "success_exit_code": 0,
            "validation_error_exit_code": 1,
            "invalid_input_exit_code": 2,
        },
        "profile:CLI",
    )
    require(
        profile["document_contract"]
        == {
            "heading": "# Pipeline v2 state projection",
            "notice": "Generated projection; do not edit this file directly.",
            "normative_body": "complete_source_YAML_bytes",
            "fence": "yaml",
        },
        "profile:document",
    )
    gates = profile["gate_contract"]
    require(
        set(gates)
        == {
            "open_statuses",
            "blocked_status",
            "implementation_statuses",
            "bounded_implementation_authority",
            "five_K0b_01_gate_ids",
            "closed_record_schemas",
            "validated_status_required_evidence_keys",
        },
        "profile:gate_contract",
    )
    require(
        len(gates["five_K0b_01_gate_ids"])
        == len(set(gates["five_K0b_01_gate_ids"]))
        == 5,
        "profile:five_gates",
    )
    for node in gates["closed_record_schemas"].values():
        validate_schema(node, 0, limits["maximum_schema_depth"], definitions)
    validate_transition_profile(profile)
    return profile, digest(data)


TARGET_GATES = (
    "G-K0B02-K0B01-COMPLETE",
    "G-K0B02-SINGLE-SOURCE-CONFIRMATION",
)
OWNER_REF = {
    "path": "new pipeline/decisions/k0b-02-prerequisite-transition-owner-disposition-v1.yaml",
    "sha256": "4532c26b67fa33da04a4464c413963b7b1131896e421c9ee9935851f2b932eaf",
}
REQUEST_REF = {
    "path": "new pipeline/requests/k0b-02-prerequisite-transition-approval-request-v1.yaml",
    "sha256": "33ffc19e51b866cbd66b844c7582e237660020a2b9da3c3a2afc62782717a8f3",
}
PRESERVED_SECTIONS = (
    "state_id",
    "schema_version",
    "baseline",
    "supporting_review_evidence",
    "root_plan_status",
    "status_index",
)
CLOSURE_CONDITIONS = {
    TARGET_GATES[0]: "K0b_01_completion_receipt_exists",
    TARGET_GATES[
        1
    ]: "confirm_single_JSON_registry_and_projection_ownership_before_K0b_02",
}


def reject_reparse(path: Path, label: str) -> None:
    candidate = path.absolute()
    for item in (candidate, *candidate.parents):
        try:
            info = item.lstat()
        except OSError as exc:
            raise RendererError(f"{label}:read") from exc
        require(
            not stat.S_ISLNK(info.st_mode)
            and not (getattr(info, "st_file_attributes", 0) & 0x400),
            f"{label}:reparse",
        )


def validate_transition_profile(profile: dict[str, Any]) -> None:
    contract = profile["transition_contract"]
    require(
        isinstance(contract, dict)
        and set(contract)
        == {
            "baseline_source",
            "bindings",
            "preserved_sections",
            "expected_active_authority",
            "expected_work_items",
            "expected_open_gates",
            "preserved_closed_gates",
            "expected_scope",
        },
        "profile:transition",
    )
    require(
        contract["baseline_source"]
        == {
            "path": "new pipeline/state/state.yaml",
            "sha256": "977cc6c681d4cd0f3c80a3e514aacbc66e293b84fff16f7755c1f92216d74ef3",
            "bytes": 30082,
        },
        "profile:baseline",
    )
    require(
        set(contract["bindings"])
        == {
            "approval_request",
            "owner_disposition",
            "completion_receipt",
            "single_source_confirmation",
            "gate_closure_proposal",
            "planning_package",
        }
        and contract["bindings"]["owner_disposition"] == OWNER_REF
        and contract["bindings"]["approval_request"] == REQUEST_REF,
        "profile:authority",
    )
    require(
        set(contract["preserved_sections"]) == set(PRESERVED_SECTIONS),
        "profile:preserved_sections",
    )
    require(
        len(contract["preserved_closed_gates"]) == 8
        and len(contract["expected_open_gates"]) == 7,
        "profile:transition_inventory",
    )


def validate_transition(source: dict[str, Any], profile: dict[str, Any]) -> None:
    contract = profile["transition_contract"]
    require(
        source["status"]
        == "K0b_02_prerequisites_complete_implementation_not_authorized",
        "source:K0b_02_root_status",
    )
    scope = source["scope"]
    require(
        scope["runtime_authority"] == "none"
        and scope["K0b_02_implementation_authority"] == "none"
        and scope["K0b_02_runtime_authority"] == "none",
        "source:K0b_02_authority",
    )
    require(scope == contract["expected_scope"], "source:preserved_scope")
    require(
        source["active_authority"] == contract["expected_active_authority"]
        and source["active_authority"]["K0b_02_prerequisite_transition"] == OWNER_REF,
        "source:K0b_02_disposition",
    )
    for name in PRESERVED_SECTIONS:
        require(
            source[name] == contract["preserved_sections"][name],
            "source:preserved:" + name,
        )
    require(
        source["work_items"] == contract["expected_work_items"],
        "source:preserved_work_items",
    )
    require(
        source["open_gates"] == contract["expected_open_gates"],
        "source:foreign_gate_change",
    )
    preserved = contract["preserved_closed_gates"]
    require(
        source["closed_gates"][: len(preserved)] == preserved
        and [g["gate_id"] for g in source["closed_gates"][len(preserved) :]]
        == list(TARGET_GATES),
        "source:closed_transition",
    )
    for item in source["work_items"]:
        expected = [
            g["gate_id"]
            for g in source["open_gates"]
            if any(
                block == item["work_item_id"]
                or block.startswith(item["work_item_id"] + "_")
                for block in g["blocks"]
            )
        ]
        require(item["open_gate_ids"] == expected, "source:gate_work_item_consistency")
    item = next(w for w in source["work_items"] if w["work_item_id"] == "K0b-02")
    require(
        item["status"] == "prerequisites_complete_implementation_not_authorized"
        and item["open_gate_ids"] == []
        and item["authority_path"] == OWNER_REF["path"]
        and item["authority_sha256"] == OWNER_REF["sha256"],
        "source:K0b_02_ready",
    )
    try:
        recorded = datetime.fromisoformat(source["generated_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise RendererError("source:transition_time") from exc
    require(
        recorded.tzinfo is not None
        and recorded.utcoffset() == timezone.utc.utcoffset(recorded),
        "source:transition_time",
    )
    profile_ref = source["projection_profile"]
    closure_ref = None
    for gate in source["closed_gates"][len(preserved) :]:
        require(
            gate["closure_condition"] == CLOSURE_CONDITIONS[gate["gate_id"]]
            and gate["closed_by"] == "workspace_owner"
            and gate["closed_at"] == source["generated_at"],
            "source:K0b_02_closure",
        )
        evidence = gate["evidence"]
        for name, ref in contract["bindings"].items():
            require(evidence[name] == ref, "source:K0b_02_evidence:" + name)
        require(
            evidence["projection_profile"] == profile_ref
            and evidence["gate_closure"]["path"]
            == "new pipeline/evidence/k0b-02-prerequisite-gate-closure-v1.yaml",
            "source:K0b_02_evidence_binding",
        )
        if closure_ref is not None:
            require(evidence["gate_closure"] == closure_ref, "source:closure_pair")
        closure_ref = evidence["gate_closure"]


def reference(path: Any, sha: Any, root: Path, profile: dict[str, Any]) -> None:
    require(
        isinstance(path, str)
        and isinstance(sha, str)
        and SHA.fullmatch(sha) is not None,
        "source:reference_shape",
    )
    require(
        path in profile["reference_contract"]["allowed_repository_paths"],
        "source:reference_scope",
    )
    require("\\" not in path and not DRIVE.match(path), "source:path_style")
    posix = PurePosixPath(path)
    require(
        not posix.is_absolute() and ".." not in posix.parts and str(posix) == path,
        "source:path_escape",
    )
    reject_reparse(root, "source:reference_root")
    candidate = root.resolve()
    for part in posix.parts:
        candidate /= part
        try:
            info = candidate.lstat()
        except OSError as exc:
            raise RendererError("source:reference_missing") from exc
        require(
            not stat.S_ISLNK(info.st_mode)
            and not (getattr(info, "st_file_attributes", 0) & 0x400),
            "source:reference_reparse",
        )
    require(candidate.is_file(), "source:reference_missing")
    require(digest(candidate.read_bytes()) == sha, "source:reference_hash")


def walk_references(value: Any, root: Path, profile: dict[str, Any]) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            reference(value["path"], value["sha256"], root, profile)
        for item in value.values():
            walk_references(item, root, profile)
    elif isinstance(value, list):
        for item in value:
            walk_references(item, root, profile)
    elif isinstance(value, str):
        require(not DRIVE.match(value), "source:absolute_path")


def validate_gates(source: dict[str, Any], profile: dict[str, Any]) -> None:
    work = source["work_items"]
    sequence = [w["sequence"] for w in work]
    ids = [w["work_item_id"] for w in work]
    require(
        len(sequence) == len(set(sequence)) and sequence == sorted(sequence),
        "source:sequence",
    )
    require(len(ids) == len(set(ids)), "source:work_item_ids")
    opened = [g["gate_id"] for g in source["open_gates"]]
    closed = [g["gate_id"] for g in source["closed_gates"]]
    require(
        len(opened) == len(set(opened)) and opened == sorted(opened),
        "source:open_gate_ids",
    )
    require(len(closed) == len(set(closed)), "source:closed_gate_ids")
    require(not set(opened) & set(closed), "source:gate_overlap")
    gates = profile["gate_contract"]
    for gate in source["closed_gates"]:
        require(
            gate["gate_id"] in gates["closed_record_schemas"],
            "source:unknown_closed_gate",
        )
        validate_value(
            gate,
            gates["closed_record_schemas"][gate["gate_id"]],
            "closed_gate",
            profile["schema_definitions"],
        )
    require(
        all(g["status"] in gates["open_statuses"] for g in source["open_gates"]),
        "source:open_status",
    )
    require(
        all(g["status"] == "closed" for g in source["closed_gates"]),
        "source:closed_status",
    )
    for item in work:
        item_gates = item["open_gate_ids"]
        require(
            len(item_gates) == len(set(item_gates)) and set(item_gates) <= set(opened),
            "source:work_item_gates",
        )
        if item["work_item_id"] == "K0b-01":
            expected = [g for g in opened if g.startswith("G-K0B01-")]
            require(item_gates == expected, "source:K0b_01_gates")
            scope = source["scope"]
            require(scope["runtime_authority"] == "none", "source:runtime_authority")
            require(
                scope["K0b_01_remaining_open_prerequisites"] == len(expected),
                "source:prerequisite_count",
            )
            status = item["status"]
            if expected:
                require(
                    status == gates["blocked_status"]
                    and scope["implementation_authority"] == "none",
                    "source:blocked_authority",
                )
            else:
                require(
                    status in gates["implementation_statuses"]
                    and scope["implementation_authority"]
                    == gates["bounded_implementation_authority"],
                    "source:implementation_authority",
                )
                authority = source["active_authority"].get(
                    "K0b_01_final_implementation_disposition"
                )
                require(
                    isinstance(authority, dict)
                    and item["authority_path"] == authority["path"]
                    and item["authority_sha256"] == authority["sha256"],
                    "source:authority_consistency",
                )
                require(
                    set(gates["five_K0b_01_gate_ids"]) <= set(closed),
                    "source:five_gate_inventory",
                )
                if status == "implemented_validated_runtime_not_authorized":
                    require(
                        set(gates["validated_status_required_evidence_keys"])
                        <= set(source["supporting_review_evidence"]),
                        "source:missing_implementation_evidence",
                    )


def render_bytes(
    *, source_path: Path, profile_path: Path, repository_root: Path
) -> tuple[bytes, dict[str, str]]:
    data, text = read_text(source_path, "source")
    source = load_yaml(text, "source")
    profile, profile_sha = load_profile(profile_path)
    require(len(data) <= profile["limits"]["maximum_source_bytes"], "source:size")
    require("```" not in text, "source:fence")
    validate_value(source, profile["source_schema"], "", profile["schema_definitions"])
    require(
        source["schema_version"] == 1
        and source["projection_version"] == profile["projection_version"],
        "source:version",
    )
    require(
        source["projection_profile"]
        == {"path": profile["repository_paths"]["profile"], "sha256": profile_sha},
        "source:profile_binding",
    )
    validate_gates(source, profile)
    validate_transition(source, profile)
    walk_references(source, repository_root, profile)
    for item in source["work_items"]:
        reference(
            item["authority_path"], item["authority_sha256"], repository_root, profile
        )
    paths = profile["repository_paths"]
    doc = profile["document_contract"]
    output = (
        f"{doc['heading']}\n\nSource: `{paths['source']}`\n\n"
        f"Source SHA-256: `{digest(data)}`\n\nProjection profile: `{paths['profile']}`\n\n"
        f"Projection profile SHA-256: `{profile_sha}`\n\n"
        f"Projection version: `{profile['projection_version']}`\n\n{doc['notice']}\n\n"
        f"```yaml\n{text}```\n"
    ).encode("utf-8")
    return output, {
        "source_sha256": digest(data),
        "profile_sha256": profile_sha,
        "projection_sha256": digest(output),
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
    actual, _ = read_text(projection_path, "projection")
    require(actual == expected, "projection:byte_mismatch")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="state-renderer-v4")
    modes = parser.add_subparsers(dest="command", required=True)
    for mode in ("render", "check"):
        sub = modes.add_parser(mode)
        sub.add_argument("--source", type=Path, required=True)
        sub.add_argument("--profile", type=Path, required=True)
        sub.add_argument("--repository-root", type=Path, required=True)
        sub.add_argument(
            "--output" if mode == "render" else "--projection", type=Path, required=True
        )
    args = parser.parse_args()
    kwargs = {
        "source_path": args.source,
        "profile_path": args.profile,
        "repository_root": args.repository_root,
    }
    try:
        if args.command == "render":
            require(
                args.output.resolve()
                not in {args.source.resolve(), args.profile.resolve()},
                "output:input_collision",
            )
            output, summary = render_bytes(**kwargs)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
        else:
            summary = check_projection(**kwargs, projection_path=args.projection)
        print(
            json.dumps(
                {"result": "pass", **summary}, sort_keys=True, separators=(",", ":")
            )
        )
        return 0
    except RendererError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"invalid_input:{type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
