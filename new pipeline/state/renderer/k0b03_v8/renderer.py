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
PROFILE_ID = "pipeline-v2.state-projection-profile-v8"
PROJECTION_VERSION = "8.0.0"
RENDERER_VERSION = "8.0.0"
PROFILE_PATH = "new pipeline/state/renderer/k0b03_v8/projection-profile-v8.yaml"
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


def _decode_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RendererError(f"{label}:JSON") from exc
    require(isinstance(value, dict), f"{label}:object")
    return value


def load_profile(
    path: Path, repository_root: Path
) -> tuple[dict[str, Any], str, frozenset[str]]:
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
        base
        == {
            "path": "new pipeline/state/renderer/k0b03_v7/projection-profile-v7.yaml",
            "sha256": "864703ab7fe2b820737d68d0d723869dd58bfe2f184fb5c5dea75486c1051b5a",
            "bytes": 8008,
            "allowed_repository_path_count": 373,
            "transition_pin_count": 10,
        },
        "profile:base_contract",
    )
    base_profile = _decode_json(
        repository_file(
            repository_root,
            base["path"],
            base["sha256"],
            base["bytes"],
            "base_profile",
        ),
        "base_profile",
    )
    v6_contract = base_profile["base_profile_contract"]
    v6_profile = _decode_json(
        repository_file(
            repository_root,
            v6_contract["path"],
            v6_contract["sha256"],
            v6_contract["bytes"],
            "base_profile_v6",
        ),
        "base_profile_v6",
    )
    v6_paths = v6_profile["reference_contract"]["allowed_repository_paths"]
    v7_additions = base_profile["reference_contract"]["allowed_path_additions"]
    base_paths = sorted([*v6_paths, *v7_additions])
    require(
        len(v6_paths) == 365
        and len(v7_additions) == 8
        and len(base_paths) == len(set(base_paths)) == 373,
        "base_profile:allowed_count",
    )
    require(
        len(base_profile["reference_contract"]["transition_pins"]) == 10,
        "base_profile:pin_count",
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
    additions = refs["allowed_path_additions"]
    require(
        refs["digest"] == "SHA-256"
        and refs["reparse_points"] == "forbidden"
        and isinstance(additions, list)
        and len(additions) == 11
        and additions == sorted(additions)
        and len(additions) == len(set(additions))
        and not set(additions).intersection(base_paths),
        "profile:allowed_additions",
    )
    allowed = sorted([*base_paths, *additions])
    require(
        refs["base_allowed_path_count"] == 373
        and refs["effective_allowed_path_count"] == len(allowed) == 384,
        "profile:effective_allowed_count",
    )
    pins = refs["transition_pins"]
    require(
        isinstance(pins, list)
        and len(pins) == 12
        and [item["path"] for item in pins] == sorted(item["path"] for item in pins)
        and len({item["path"] for item in pins}) == 12,
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
    return profile, digest(raw), frozenset(allowed)


def _work_item(source: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    items = [item for item in source["work_items"] if item["work_item_id"] == work_item_id]
    require(len(items) == 1, "source:work_item_identity")
    return items[0]


def _gate(source: dict[str, Any], collection: str, gate_id: str) -> dict[str, Any]:
    matches = [item for item in source[collection] if item.get("gate_id") == gate_id]
    require(len(matches) == 1, f"source:{collection}_gate_identity")
    return matches[0]


def _reference_pair(item: dict[str, Any]) -> dict[str, str]:
    return {"path": item["path"], "sha256": item["sha256"]}


def validate_transition(
    source: dict[str, Any], profile: dict[str, Any], profile_sha: str
) -> None:
    contract = profile["delta_contract"]
    expected_whitelist = [
        "generated_at",
        "projection_version",
        "projection_profile.path",
        "projection_profile.sha256",
        "active_authority.development_plan_v0_14_adoption",
        "supporting_review_evidence.development_plan_v0_14_adoption",
        "root_plan_status.development_plan.path",
        "root_plan_status.development_plan.sha256",
        "root_plan_status.development_plan.internal_label",
        "root_plan_status.development_plan.effective_status",
        "work_items[work_item_id=K0b-03].authority_path",
        "work_items[work_item_id=K0b-03].authority_sha256",
        "work_items[work_item_id=N1].authority_path",
        "work_items[work_item_id=N1].authority_sha256",
    ]
    require(contract["delta_whitelist"] == expected_whitelist, "profile:delta_whitelist")
    state = profile["state_contract"]
    target = contract["target_plan"]
    owner_ref = _reference_pair(contract["references"]["owner_disposition"])
    evidence_ref = _reference_pair(contract["references"]["adoption_evidence"])

    require(source["generated_at"] == contract["generated_at"], "source:transition_time")
    try:
        recorded = datetime.fromisoformat(source["generated_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise RendererError("source:transition_time") from exc
    require(
        recorded.tzinfo is not None
        and recorded.utcoffset() == timezone.utc.utcoffset(recorded),
        "source:transition_time",
    )
    require(source["projection_version"] == PROJECTION_VERSION, "source:version")
    require(
        source["projection_profile"] == {"path": PROFILE_PATH, "sha256": profile_sha},
        "source:profile_binding",
    )
    require(source["status"] == state["root_status"], "source:root_status")
    require(source["scope"]["runtime_authority"] == state["runtime_authority"], "source:runtime")
    require(
        source["active_authority"].get("development_plan_v0_14_adoption") == owner_ref,
        "source:active_authority",
    )
    require(
        source["supporting_review_evidence"].get("development_plan_v0_14_adoption")
        == evidence_ref,
        "source:supporting_evidence",
    )
    development = source["root_plan_status"]["development_plan"]
    for field in ("path", "sha256", "internal_label", "effective_status"):
        require(development[field] == target[field], f"source:development_plan_{field}")
    for work_item_id in ("K0b-03", "N1"):
        item = _work_item(source, work_item_id)
        require(
            item["authority_path"] == target["path"]
            and item["authority_sha256"] == target["sha256"],
            f"source:{work_item_id}_authority",
        )
    k0b03 = _work_item(source, "K0b-03")
    require(
        k0b03["status"] == state["expected_K0b03_status"]
        and k0b03["open_gate_ids"] == state["expected_K0b03_open_gate_ids"],
        "source:K0b03_status",
    )
    open_ids = [gate.get("gate_id") for gate in source["open_gates"]]
    closed_ids = [gate.get("gate_id") for gate in source["closed_gates"]]
    require(
        all(isinstance(item, str) for item in [*open_ids, *closed_ids])
        and len(open_ids) == len(set(open_ids)) == state["expected_open_gate_count"]
        and len(closed_ids) == len(set(closed_ids)) == state["expected_closed_gate_count"]
        and not set(open_ids).intersection(closed_ids),
        "source:gate_inventory",
    )
    require(
        _gate(source, "closed_gates", "G-K0B03-K0B01-COMPLETE")["status"]
        == state["expected_predecessor_gate_status"],
        "source:predecessor_gate",
    )
    require(
        _gate(source, "open_gates", "G-K0B03-UNTRUSTED-SHAPES")["status"]
        == state["expected_untrusted_shapes_gate_status"],
        "source:untrusted_shapes_gate",
    )

    reversed_source = copy.deepcopy(source)
    baseline = contract["baseline_value"]
    reversed_source["generated_at"] = baseline["generated_at"]
    reversed_source["projection_version"] = baseline["projection_version"]
    reversed_source["projection_profile"] = copy.deepcopy(baseline["projection_profile"])
    del reversed_source["active_authority"]["development_plan_v0_14_adoption"]
    del reversed_source["supporting_review_evidence"]["development_plan_v0_14_adoption"]
    baseline_development = baseline["root_plan_status"]["development_plan"]
    reversed_development = reversed_source["root_plan_status"]["development_plan"]
    for field in ("path", "sha256", "internal_label", "effective_status"):
        reversed_development[field] = copy.deepcopy(baseline_development[field])
    for work_item_id in ("K0b-03", "N1"):
        old_item = _work_item(baseline, work_item_id)
        item = _work_item(reversed_source, work_item_id)
        item["authority_path"] = old_item["authority_path"]
        item["authority_sha256"] = old_item["authority_sha256"]
    require(typed_equal(reversed_source, baseline), "source:outside_delta_whitelist")


def reference(
    path: Any, sha: Any, repository_root: Path, allowed_paths: frozenset[str]
) -> None:
    require(
        isinstance(path, str)
        and isinstance(sha, str)
        and SHA.fullmatch(sha) is not None,
        "source:reference_shape",
    )
    require(path in allowed_paths, "source:reference_scope")
    require(path == ".gitattributes" or path.startswith("new pipeline/"), "source:root_reference")
    repository_file(repository_root, path, sha, -1, "source_reference")


def walk_references(
    value: Any,
    repository_root: Path,
    allowed_paths: frozenset[str],
    observed_paths: set[str],
) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            reference(value["path"], value["sha256"], repository_root, allowed_paths)
            observed_paths.add(value["path"])
        for item in value.values():
            walk_references(item, repository_root, allowed_paths, observed_paths)
    elif isinstance(value, list):
        for item in value:
            walk_references(item, repository_root, allowed_paths, observed_paths)
    elif isinstance(value, str):
        require(not DRIVE.match(value), "source:absolute_path")


def render_bytes(
    *, source_path: Path, profile_path: Path, repository_root: Path
) -> tuple[bytes, dict[str, Any]]:
    reject_reparse(repository_root, "repository_root")
    source_raw, source = read_json(source_path, "source")
    profile, profile_sha, allowed_paths = load_profile(profile_path, repository_root)
    require(len(source_raw) <= profile["limits"]["maximum_source_bytes"], "source:size")
    validate_transition(source, profile, profile_sha)
    observed_paths: set[str] = set()
    walk_references(source, repository_root, allowed_paths, observed_paths)
    for item in source["work_items"]:
        reference(item["authority_path"], item["authority_sha256"], repository_root, allowed_paths)
        observed_paths.add(item["authority_path"])
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
    require(len(output) <= profile["limits"]["maximum_projection_bytes"], "projection:size")
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
    parser = argparse.ArgumentParser(prog="state-renderer-v8")
    modes = parser.add_subparsers(dest="command", required=True)
    for mode in ("render", "check"):
        sub = modes.add_parser(mode)
        sub.add_argument("--source", type=Path, required=True)
        sub.add_argument("--profile", type=Path, required=True)
        sub.add_argument("--repository-root", type=Path, required=True)
        sub.add_argument("--output" if mode == "render" else "--projection", type=Path, required=True)
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
                args.output.resolve() not in {args.source.resolve(), args.profile.resolve()},
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
