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
PROFILE_ID = "pipeline-v2.state-projection-profile-v8-1"
PROJECTION_VERSION = "8.1.0"
RENDERER_VERSION = "8.1.0"
PROFILE_PATH = "new pipeline/state/renderer/k0b03_v8_1/projection-profile-v8-1.yaml"
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


def _validate_embedded_manifest(
    contract: Any,
    repository_root: Path,
    allowed_paths: frozenset[str],
    *,
    expected_count: int,
    expected_content_bytes: int,
    expected_manifest_bytes: int,
    expected_manifest_sha256: str,
    label: str,
) -> None:
    require(
        isinstance(contract, dict)
        and set(contract)
        == {
            "ordering",
            "path_count",
            "content_bytes",
            "manifest_bytes",
            "manifest_sha256",
            "entries",
        },
        f"profile:{label}_shape",
    )
    entries = contract["entries"]
    require(
        contract["ordering"] == "ordinal_path"
        and isinstance(entries, list)
        and len(entries) == expected_count
        and contract["path_count"] == expected_count
        and contract["content_bytes"] == expected_content_bytes
        and contract["manifest_bytes"] == expected_manifest_bytes
        and contract["manifest_sha256"] == expected_manifest_sha256,
        f"profile:{label}_metadata",
    )
    paths: list[str] = []
    manifest = bytearray()
    content_bytes = 0
    for entry in entries:
        require(
            isinstance(entry, dict)
            and set(entry) == {"path", "sha256", "bytes"}
            and isinstance(entry["path"], str)
            and isinstance(entry["sha256"], str)
            and SHA.fullmatch(entry["sha256"]) is not None
            and type(entry["bytes"]) is int
            and entry["bytes"] >= 0,
            f"profile:{label}_entry",
        )
        require(entry["path"] in allowed_paths, f"profile:{label}_scope")
        paths.append(entry["path"])
        content_bytes += entry["bytes"]
        manifest.extend(
            f"{entry['path']}\t{entry['sha256']}\t{entry['bytes']}\n".encode("utf-8")
        )
        repository_file(
            repository_root,
            entry["path"],
            entry["sha256"],
            entry["bytes"],
            label,
        )
    require(
        paths == sorted(paths)
        and len(paths) == len(set(paths))
        and content_bytes == expected_content_bytes
        and len(manifest) == expected_manifest_bytes
        and digest(bytes(manifest)) == expected_manifest_sha256,
        f"profile:{label}_root",
    )


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
            "path": "new pipeline/state/renderer/k0b03_v8/projection-profile-v8.yaml",
            "sha256": "fdc11f15dc7b9f98a240026f47de5a639c9ba702ee90931051e9e7cc9ada440a",
            "bytes": 56669,
            "allowed_repository_path_count": 384,
            "transition_pin_count": 12,
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
    require(
        base_profile.get("profile_id") == "pipeline-v2.state-projection-profile-v8"
        and base_profile.get("projection_version") == "8.0.0",
        "base_profile:identity",
    )
    v7_contract = base_profile["base_profile_contract"]
    v7_profile = _decode_json(
        repository_file(
            repository_root,
            v7_contract["path"],
            v7_contract["sha256"],
            v7_contract["bytes"],
            "base_profile_v7",
        ),
        "base_profile_v7",
    )
    v6_contract = v7_profile["base_profile_contract"]
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
    v7_additions = v7_profile["reference_contract"]["allowed_path_additions"]
    v8_additions = base_profile["reference_contract"]["allowed_path_additions"]
    base_paths = sorted([*v6_paths, *v7_additions, *v8_additions])
    require(
        len(v6_paths) == 365
        and len(v7_additions) == 8
        and len(v8_additions) == 11
        and len(base_paths) == len(set(base_paths)) == 384,
        "base_profile:allowed_count",
    )
    require(
        len(v7_profile["reference_contract"]["transition_pins"]) == 10
        and len(base_profile["reference_contract"]["transition_pins"]) == 12,
        "base_profile:pin_count",
    )
    base_delta = base_profile["delta_contract"]
    require(
        isinstance(base_delta.get("baseline_value"), dict)
        and len(base_delta.get("delta_whitelist", [])) == 14,
        "base_profile:transitive_delta_proof",
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
            "manifest_profile",
            "static_external_reference_manifest",
            "top_level_profile_binding",
            "state_source_sentinel",
            "work_item_authority_manifest",
        },
        "profile:reference_contract",
    )
    additions = refs["allowed_path_additions"]
    require(
        refs["digest"] == "SHA-256"
        and refs["reparse_points"] == "forbidden"
        and isinstance(additions, list)
        and len(additions) == 4
        and additions == sorted(additions)
        and len(additions) == len(set(additions))
        and not set(additions).intersection(base_paths),
        "profile:allowed_additions",
    )
    allowed = sorted([*base_paths, *additions])
    require(
        refs["base_allowed_path_count"] == 384
        and refs["effective_allowed_path_count"] == len(allowed) == 388,
        "profile:effective_allowed_count",
    )
    pins = refs["transition_pins"]
    require(
        isinstance(pins, list)
        and len(pins) == 9
        and [item["path"] for item in pins] == sorted(item["path"] for item in pins)
        and len({item["path"] for item in pins}) == 9,
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
    require(
        refs["manifest_profile"]
        == "path<TAB>lowercase_sha256<TAB>decimal_bytes<LF>",
        "profile:manifest_profile",
    )
    _validate_embedded_manifest(
        refs["static_external_reference_manifest"],
        repository_root,
        frozenset(allowed),
        expected_count=99,
        expected_content_bytes=3032891,
        expected_manifest_bytes=14016,
        expected_manifest_sha256="db29b63ab80a9ba3590eb1d4b68f44e2920116897d1e494da61326428790d202",
        label="static_reference_manifest",
    )
    _validate_embedded_manifest(
        refs["work_item_authority_manifest"],
        repository_root,
        frozenset(allowed),
        expected_count=13,
        expected_content_bytes=218132,
        expected_manifest_bytes=1763,
        expected_manifest_sha256="7a55a57a87efe82d760cc5d409fcbe711e84a2e6269c1da0b23ef69188ed0fb1",
        label="work_item_authority_manifest",
    )
    require(
        refs["top_level_profile_binding"]
        == {"path": PROFILE_PATH, "sha256": "computed_from_profile_bytes", "count": 1},
        "profile:top_level_profile_binding",
    )
    require(
        refs["state_source_sentinel"]
        == {"path": SOURCE_PATH, "sha256": "computed_from_source_bytes", "count": 1},
        "profile:state_source_sentinel",
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
    ]
    require(contract["delta_whitelist"] == expected_whitelist, "profile:delta_whitelist")
    state = profile["state_contract"]
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


def record_reference(
    path: Any,
    sha: Any,
    allowed_paths: frozenset[str],
    observed: dict[str, set[str]],
) -> None:
    require(
        isinstance(path, str)
        and isinstance(sha, str)
        and SHA.fullmatch(sha) is not None,
        "source:reference_shape",
    )
    require(path in allowed_paths, "source:reference_scope")
    require(path == ".gitattributes" or path.startswith("new pipeline/"), "source:root_reference")
    observed.setdefault(path, set()).add(sha)


def walk_references(
    value: Any,
    allowed_paths: frozenset[str],
    observed: dict[str, set[str]],
) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            record_reference(value["path"], value["sha256"], allowed_paths, observed)
        for item in value.values():
            walk_references(item, allowed_paths, observed)
    elif isinstance(value, list):
        for item in value:
            walk_references(item, allowed_paths, observed)
    elif isinstance(value, str):
        require(not DRIVE.match(value), "source:absolute_path")


def _manifest_map(contract: dict[str, Any]) -> dict[str, str]:
    return {item["path"]: item["sha256"] for item in contract["entries"]}


def validate_reference_contract(
    source: dict[str, Any],
    profile: dict[str, Any],
    profile_sha: str,
    repository_root: Path,
    allowed_paths: frozenset[str],
) -> dict[str, int]:
    observed: dict[str, set[str]] = {}
    walk_references(source, allowed_paths, observed)
    require(
        all(len(values) == 1 for values in observed.values()),
        "source:reference_conflict",
    )
    actual = {path: next(iter(values)) for path, values in observed.items()}
    require(
        actual.get(PROFILE_PATH) == profile_sha,
        "source:profile_reference_binding",
    )
    external = {path: sha for path, sha in actual.items() if path != PROFILE_PATH}
    expected = _manifest_map(
        profile["reference_contract"]["static_external_reference_manifest"]
    )
    missing = sorted(set(expected) - set(external))
    unexpected = sorted(set(external) - set(expected))
    require(not missing, "source:reference_manifest_missing")
    require(not unexpected, "source:reference_manifest_unexpected")
    require(external == expected, "source:reference_manifest_hash")
    for path, sha in sorted(actual.items()):
        reference(path, sha, repository_root, allowed_paths)
    static_count = len(external)
    profile_count = 1
    state_source_count = 1
    total = static_count + profile_count + state_source_count
    require(static_count == 99, "source:static_reference_path_count")
    require(total == 101, "source:reference_path_count")
    return {
        "static_external_reference_count": static_count,
        "computed_profile_binding_count": profile_count,
        "state_source_sentinel_count": state_source_count,
        "entry_state_reference_count": total,
    }


def validate_work_item_authorities(
    source: dict[str, Any],
    profile: dict[str, Any],
    repository_root: Path,
    allowed_paths: frozenset[str],
) -> int:
    observed: dict[str, set[str]] = {}
    for item in source["work_items"]:
        path = item.get("authority_path")
        sha = item.get("authority_sha256")
        record_reference(path, sha, allowed_paths, observed)
    require(
        all(len(values) == 1 for values in observed.values()),
        "source:work_item_authority_conflict",
    )
    actual = {path: next(iter(values)) for path, values in observed.items()}
    expected = _manifest_map(
        profile["reference_contract"]["work_item_authority_manifest"]
    )
    require(actual == expected, "source:work_item_authority_manifest")
    for path, sha in sorted(actual.items()):
        reference(path, sha, repository_root, allowed_paths)
    require(len(actual) == 13, "source:work_item_authority_count")
    return len(actual)


def render_bytes(
    *, source_path: Path, profile_path: Path, repository_root: Path
) -> tuple[bytes, dict[str, Any]]:
    reject_reparse(repository_root, "repository_root")
    source_raw, source = read_json(source_path, "source")
    profile, profile_sha, allowed_paths = load_profile(profile_path, repository_root)
    require(len(source_raw) <= profile["limits"]["maximum_source_bytes"], "source:size")
    validate_transition(source, profile, profile_sha)
    reference_summary = validate_reference_contract(
        source, profile, profile_sha, repository_root, allowed_paths
    )
    authority_count = validate_work_item_authorities(
        source, profile, repository_root, allowed_paths
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
    require(len(output) <= profile["limits"]["maximum_projection_bytes"], "projection:size")
    return output, {
        "source_sha256": digest(source_raw),
        "profile_sha256": profile_sha,
        "projection_sha256": digest(output),
        "open_gate_count": len(source["open_gates"]),
        "closed_gate_count": len(source["closed_gates"]),
        **reference_summary,
        "work_item_authority_count": authority_count,
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
    parser = argparse.ArgumentParser(prog="state-renderer-v8-1")
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
