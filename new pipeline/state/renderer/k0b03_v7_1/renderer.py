from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SHA = re.compile(r"^[0-9a-f]{64}$")
DRIVE = re.compile(r"^[A-Za-z]:[/\\]")
PROFILE_ID = "pipeline-v2.state-projection-profile-v7"
PROJECTION_VERSION = "7.0.0"
RENDERER_VERSION = "7.1.0"
PROFILE_PATH = "new pipeline/state/renderer/k0b03_v7/projection-profile-v7.yaml"
SOURCE_PATH = "new pipeline/state/state.yaml"
PROJECTION_PATH = "new pipeline/state/STATE.md"
REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class RendererError(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RendererError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_reparse(info: Any) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & REPARSE_ATTRIBUTE
    )


def reject_reparse(path: Path, label: str, *, allow_missing: bool = False) -> None:
    candidate = path.absolute()
    for item in (candidate, *candidate.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            require(allow_missing, f"{label}:read")
            continue
        except OSError as exc:
            raise RendererError(f"{label}:read") from exc
        require(not _is_reparse(info), f"{label}:reparse")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_key:{key}")
        result[key] = value
    return result


def read_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    reject_reparse(path, label)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RendererError(f"{label}:read") from exc
    require(not raw.startswith(b"\xef\xbb\xbf"), f"{label}:BOM")
    require(
        b"\r" not in raw and raw.endswith(b"\n") and not raw.endswith(b"\n\n"),
        f"{label}:canonical_text",
    )
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RendererError(f"{label}:JSON") from exc
    require(isinstance(value, dict), f"{label}:object")
    return raw, value


def canonical_json(value: dict[str, Any]) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        )
    except (TypeError, ValueError) as exc:
        raise RendererError("source:canonical_JSON") from exc
    return (text + "\n").encode("utf-8")


def typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def load_profile(
    path: Path, repository_root: Path
) -> tuple[dict[str, Any], str, frozenset[str], dict[str, Any]]:
    raw, profile = read_json(path, "profile")
    require(
        set(profile)
        == {
            "profile_id",
            "schema_version",
            "projection_version",
            "status",
            "repository_paths",
            "limits",
            "canonicalization",
            "base_profile_contract",
            "reference_contract",
            "document_contract",
            "delta_contract",
            "state_contract",
            "non_authorizations",
        },
        "profile:fields",
    )
    require(profile["profile_id"] == PROFILE_ID, "profile:id")
    require(
        profile["schema_version"] == 1
        and profile["projection_version"] == PROJECTION_VERSION
        and profile["status"] == "active",
        "profile:version",
    )
    require(
        profile["repository_paths"]
        == {
            "source": SOURCE_PATH,
            "projection": PROJECTION_PATH,
            "profile": PROFILE_PATH,
        },
        "profile:repository_paths",
    )
    require(
        profile["canonicalization"]
        == {
            "encoding": "UTF-8-without-BOM",
            "line_endings": "LF",
            "final_newline_count": 1,
            "JSON_duplicate_keys": "forbidden",
            "timestamps": "source_values_only",
            "environment_values": "forbidden",
        },
        "profile:canonicalization",
    )

    base = profile["base_profile_contract"]
    require(
        set(base)
        == {
            "path",
            "sha256",
            "bytes",
            "allowed_repository_path_count",
            "transition_pin_count",
        },
        "profile:base_contract",
    )
    base_raw = repository_file(
        repository_root,
        base["path"],
        base["sha256"],
        base["bytes"],
        "base_profile",
    )
    try:
        base_profile = json.loads(base_raw, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RendererError("base_profile:JSON") from exc
    base_paths = base_profile["reference_contract"]["allowed_repository_paths"]
    base_pins = base_profile["reference_contract"]["pins"]
    require(
        len(base_paths) == base["allowed_repository_path_count"] == 365,
        "base_profile:allowed_count",
    )
    require(
        len(base_pins) == base["transition_pin_count"] == 26,
        "base_profile:pin_count",
    )
    require(
        base_paths == sorted(base_paths) and len(base_paths) == len(set(base_paths)),
        "base_profile:allowed_order",
    )

    refs = profile["reference_contract"]
    require(
        set(refs)
        == {
            "digest",
            "base_allowed_path_count",
            "allowed_path_additions",
            "effective_allowed_path_count",
            "transition_pins",
            "reparse_points",
        },
        "profile:reference_contract",
    )
    require(refs["digest"] == "SHA-256", "profile:digest")
    additions = refs["allowed_path_additions"]
    require(
        isinstance(additions, list)
        and len(additions) == 8
        and additions == sorted(additions)
        and len(additions) == len(set(additions))
        and not set(additions).intersection(base_paths),
        "profile:allowed_additions",
    )
    allowed = sorted([*base_paths, *additions])
    require(
        refs["base_allowed_path_count"] == 365
        and refs["effective_allowed_path_count"] == len(allowed) == 373,
        "profile:effective_allowed_count",
    )
    pins = refs["transition_pins"]
    require(
        isinstance(pins, list)
        and len(pins) == 10
        and [item["path"] for item in pins] == sorted(item["path"] for item in pins)
        and len({item["path"] for item in pins}) == len(pins),
        "profile:transition_pins",
    )
    for item in pins:
        require(
            set(item) == {"path", "sha256", "bytes"}
            and SHA.fullmatch(item["sha256"]) is not None
            and type(item["bytes"]) is int,
            "profile:transition_pin_shape",
        )
        repository_file(
            repository_root,
            item["path"],
            item["sha256"],
            item["bytes"],
            "transition_pin",
        )
    return profile, digest(raw), frozenset(allowed), base_profile


def _work_item(source: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    items = [item for item in source["work_items"] if item["work_item_id"] == work_item_id]
    require(len(items) == 1, "source:work_item_identity")
    return items[0]


def _gate_ids(records: list[dict[str, Any]], label: str) -> list[str]:
    ids = [item.get("gate_id") for item in records]
    require(all(isinstance(item, str) for item in ids), f"source:{label}_gate_shape")
    require(len(ids) == len(set(ids)), f"source:{label}_gate_duplicate")
    return ids


def _reference_pair(path: str, sha256: str) -> dict[str, str]:
    return {"path": path, "sha256": sha256}


def _reconstruct_v6_source(
    base_profile: dict[str, Any], generated_at: str, projection_profile: dict[str, str]
) -> dict[str, Any]:
    contract = base_profile["delta_contract"]
    expected = copy.deepcopy(contract["baseline_value"])
    patch = contract["expected_patch"]
    require(isinstance(patch, dict), "base_profile:expected_patch")
    for dotted, value in patch.items():
        if dotted.startswith("work_items[work_item_id=K0b-02]."):
            field = dotted.rsplit(".", 1)[1]
            item = _work_item(expected, "K0b-02")
            require(field in item, "base_profile:patch_path")
            item[field] = copy.deepcopy(value)
            continue
        parts = dotted.split(".")
        cursor: dict[str, Any] = expected
        for part in parts[:-1]:
            require(isinstance(cursor, dict), "base_profile:patch_path")
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = copy.deepcopy(value)
    expected["generated_at"] = generated_at
    expected["projection_profile"] = copy.deepcopy(projection_profile)
    return expected


def validate_transition(
    source: dict[str, Any],
    profile: dict[str, Any],
    profile_sha: str,
    base_profile: dict[str, Any],
) -> None:
    contract = profile["delta_contract"]
    require(
        contract["delta_whitelist"]
        == [
            "generated_at",
            "projection_version",
            "projection_profile.path",
            "projection_profile.sha256",
            "active_authority.K0b_03_predecessor_gate_transition",
            "supporting_review_evidence.K0b_03_predecessor_gate_closure",
            "work_items[work_item_id=K0b-03].open_gate_ids",
            "open_gates",
            "closed_gates",
        ],
        "profile:delta_whitelist",
    )
    state = profile["state_contract"]
    require(source["projection_version"] == PROJECTION_VERSION, "source:version")
    require(
        source["projection_profile"]
        == {"path": PROFILE_PATH, "sha256": profile_sha},
        "source:profile_binding",
    )
    try:
        recorded = datetime.fromisoformat(source["generated_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise RendererError("source:transition_time") from exc
    require(
        recorded.tzinfo is not None
        and recorded.utcoffset() == timezone.utc.utcoffset(recorded),
        "source:transition_time",
    )
    require(source["status"] == state["root_status"], "source:root_status")
    require(source["scope"]["runtime_authority"] == "none", "source:runtime")

    owner_ref = _reference_pair(
        state["references"]["owner_disposition"]["path"],
        state["references"]["owner_disposition"]["sha256"],
    )
    closure_ref = _reference_pair(
        state["references"]["gate_closure"]["path"],
        state["references"]["gate_closure"]["sha256"],
    )
    require(
        source["active_authority"].get("K0b_03_predecessor_gate_transition")
        == owner_ref,
        "source:active_authority",
    )
    require(
        source["supporting_review_evidence"].get(
            "K0b_03_predecessor_gate_closure"
        )
        == closure_ref,
        "source:supporting_evidence",
    )

    item = _work_item(source, "K0b-03")
    require(
        item["status"] == "blocked"
        and item["authority_path"] == state["K0b03_authority"]["path"]
        and item["authority_sha256"] == state["K0b03_authority"]["sha256"]
        and item["open_gate_ids"] == ["G-K0B03-UNTRUSTED-SHAPES"],
        "source:K0b03",
    )

    open_ids = _gate_ids(source["open_gates"], "open")
    closed_ids = _gate_ids(source["closed_gates"], "closed")
    require(not set(open_ids).intersection(closed_ids), "source:gate_overlap")
    require(
        len(open_ids) == 6
        and open_ids == state["expected_open_gate_ids"]
        and len(closed_ids) == 11
        and closed_ids[-1] == "G-K0B03-K0B01-COMPLETE",
        "source:gate_inventory",
    )
    require(
        "G-K0B03-K0B01-COMPLETE" not in open_ids,
        "source:target_still_open",
    )
    untrusted = next(
        gate for gate in source["open_gates"] if gate["gate_id"] == "G-K0B03-UNTRUSTED-SHAPES"
    )
    require(
        typed_equal(untrusted, state["untrusted_shapes_gate"]),
        "source:untrusted_shapes",
    )

    refs = state["references"]
    expected_closed = {
        "gate_id": "G-K0B03-K0B01-COMPLETE",
        "status": "closed",
        "closure_condition": "K0b_01_completion_receipt_exists",
        "closed_by": "workspace_owner",
        "closed_at": source["generated_at"],
        "evidence": {
            "approval_request": _reference_pair(
                refs["approval_request"]["path"], refs["approval_request"]["sha256"]
            ),
            "owner_disposition": owner_ref,
            "completion_receipt": _reference_pair(
                refs["completion_receipt"]["path"],
                refs["completion_receipt"]["sha256"],
            ),
            "planning_owner_disposition": _reference_pair(
                refs["planning_owner_disposition"]["path"],
                refs["planning_owner_disposition"]["sha256"],
            ),
            "gate_closure_proposal": _reference_pair(
                refs["gate_closure_proposal"]["path"],
                refs["gate_closure_proposal"]["sha256"],
            ),
            "planning_package_v1": _reference_pair(
                refs["planning_package_v1"]["path"],
                refs["planning_package_v1"]["sha256"],
            ),
            "planning_overlay_v1_1": _reference_pair(
                refs["planning_overlay_v1_1"]["path"],
                refs["planning_overlay_v1_1"]["sha256"],
            ),
            "gate_closure": closure_ref,
            "projection_profile": {"path": PROFILE_PATH, "sha256": profile_sha},
        },
    }
    require(
        typed_equal(source["closed_gates"][-1], expected_closed),
        "source:closed_record",
    )

    reversed_source = copy.deepcopy(source)
    reversed_source["generated_at"] = contract["baseline_generated_at"]
    reversed_source["projection_version"] = "6.0.0"
    reversed_source["projection_profile"] = copy.deepcopy(
        contract["baseline_projection_profile"]
    )
    del reversed_source["active_authority"]["K0b_03_predecessor_gate_transition"]
    del reversed_source["supporting_review_evidence"][
        "K0b_03_predecessor_gate_closure"
    ]
    _work_item(reversed_source, "K0b-03")["open_gate_ids"] = [
        "G-K0B03-K0B01-COMPLETE",
        "G-K0B03-UNTRUSTED-SHAPES",
    ]
    reversed_source["open_gates"] = [
        copy.deepcopy(contract["baseline_target_open_gate"]),
        *reversed_source["open_gates"],
    ]
    removed = reversed_source["closed_gates"].pop()
    require(
        removed["gate_id"] == "G-K0B03-K0B01-COMPLETE",
        "source:reverse_closed_record",
    )
    expected_baseline = _reconstruct_v6_source(
        base_profile,
        contract["baseline_generated_at"],
        contract["baseline_projection_profile"],
    )
    require(
        typed_equal(reversed_source, expected_baseline),
        "source:outside_delta_whitelist",
    )


def reference(
    path: Any,
    sha: Any,
    repository_root: Path,
    allowed_paths: frozenset[str],
) -> None:
    require(
        isinstance(path, str)
        and isinstance(sha, str)
        and SHA.fullmatch(sha) is not None,
        "source:reference_shape",
    )
    require(path in allowed_paths, "source:reference_scope")
    require(
        path == ".gitattributes" or path.startswith("new pipeline/"),
        "source:root_reference",
    )
    raw = repository_file(repository_root, path, sha, -1, "source_reference")
    require(raw is not None, "source:reference_missing")


def repository_file(
    root: Path, path: str, expected_sha: str, expected_bytes: int, label: str
) -> bytes:
    require(isinstance(path, str) and "\\" not in path, f"{label}:path_style")
    require(not DRIVE.match(path), f"{label}:absolute")
    posix = PurePosixPath(path)
    require(
        not posix.is_absolute() and ".." not in posix.parts and str(posix) == path,
        f"{label}:escape",
    )
    reject_reparse(root, "repository_root")
    candidate = root.resolve(strict=True)
    for part in posix.parts:
        candidate /= part
        reject_reparse(candidate, label)
    require(candidate.is_file(), f"{label}:missing")
    raw = candidate.read_bytes()
    if expected_bytes >= 0:
        require(len(raw) == expected_bytes, f"{label}:bytes")
    require(digest(raw) == expected_sha, f"{label}:hash")
    return raw


def walk_references(
    value: Any, repository_root: Path, allowed_paths: frozenset[str]
) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            reference(value["path"], value["sha256"], repository_root, allowed_paths)
        for item in value.values():
            walk_references(item, repository_root, allowed_paths)
    elif isinstance(value, list):
        for item in value:
            walk_references(item, repository_root, allowed_paths)
    elif isinstance(value, str):
        require(not DRIVE.match(value), "source:absolute_path")


def render_bytes(
    *, source_path: Path, profile_path: Path, repository_root: Path
) -> tuple[bytes, dict[str, Any]]:
    reject_reparse(repository_root, "repository_root")
    source_raw, source = read_json(source_path, "source")
    profile, profile_sha, allowed_paths, base_profile = load_profile(
        profile_path, repository_root
    )
    require(
        len(source_raw) <= profile["limits"]["maximum_source_bytes"],
        "source:size",
    )
    validate_transition(source, profile, profile_sha, base_profile)
    walk_references(source, repository_root, allowed_paths)
    for item in source["work_items"]:
        reference(
            item["authority_path"],
            item["authority_sha256"],
            repository_root,
            allowed_paths,
        )
    doc = profile["document_contract"]
    output = (
        f"{doc['heading']}\n\nSource: `{SOURCE_PATH}`\n\n"
        f"Source SHA-256: `{digest(source_raw)}`\n\n"
        f"Projection profile: `{PROFILE_PATH}`\n\n"
        f"Projection profile SHA-256: `{profile_sha}`\n\n"
        f"Projection version: `{PROJECTION_VERSION}`\n\n"
        f"{doc['notice']}\n\n```yaml\n".encode("utf-8")
        + source_raw
        + b"```\n"
    )
    return output, {
        "source_sha256": digest(source_raw),
        "profile_sha256": profile_sha,
        "projection_sha256": digest(output),
        "open_gate_count": len(source["open_gates"]),
        "closed_gate_count": len(source["closed_gates"]),
    }


def check_projection(
    *,
    source_path: Path,
    profile_path: Path,
    projection_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    expected, summary = render_bytes(
        source_path=source_path,
        profile_path=profile_path,
        repository_root=repository_root,
    )
    reject_reparse(projection_path, "projection")
    try:
        actual = projection_path.read_bytes()
    except OSError as exc:
        raise RendererError("projection:read") from exc
    require(actual == expected, "projection:byte_mismatch")
    return summary


def write_projection(output_path: Path, output: bytes) -> None:
    reject_reparse(output_path, "output", allow_missing=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reject_reparse(output_path.parent, "output")
    reject_reparse(output_path, "output", allow_missing=True)
    output_path.write_bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(prog="state-renderer-v7")
    modes = parser.add_subparsers(dest="command", required=True)
    for mode in ("render", "check"):
        sub = modes.add_parser(mode)
        sub.add_argument("--source", type=Path, required=True)
        sub.add_argument("--profile", type=Path, required=True)
        sub.add_argument("--repository-root", type=Path, required=True)
        sub.add_argument(
            "--output" if mode == "render" else "--projection",
            type=Path,
            required=True,
        )
    args = parser.parse_args()
    try:
        kwargs = {
            "source_path": args.source,
            "profile_path": args.profile,
            "repository_root": args.repository_root,
        }
        if args.command == "render":
            reject_reparse(args.repository_root, "repository_root")
            reject_reparse(args.source, "source")
            reject_reparse(args.profile, "profile")
            reject_reparse(args.output, "output", allow_missing=True)
            require(
                args.output.resolve()
                not in {args.source.resolve(), args.profile.resolve()},
                "output:input_collision",
            )
            output, summary = render_bytes(**kwargs)
            write_projection(args.output, output)
        else:
            summary = check_projection(**kwargs, projection_path=args.projection)
        print(json.dumps({"result": "pass", **summary}, sort_keys=True))
        return 0
    except RendererError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print(f"invalid_input:{type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
