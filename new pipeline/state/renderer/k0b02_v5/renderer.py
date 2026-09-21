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
WORK_ITEM_FIELDS = {"status", "authority_path", "authority_sha256"}


class RendererError(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RendererError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RendererError(f"{label}:JSON") from exc
    require(isinstance(value, dict), f"{label}:object")
    return raw, value


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


def typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            typed_equal(left[k], right[k]) for k in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def load_profile(path: Path) -> tuple[dict[str, Any], str]:
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
            "reference_contract",
            "document_contract",
            "canonicalization",
            "delta_contract",
            "non_authorizations",
        },
        "profile:fields",
    )
    require(
        profile["profile_id"] == "pipeline-v2.state-projection-profile-v5", "profile:id"
    )
    require(
        profile["schema_version"] == 1 and profile["projection_version"] == "5.0.0",
        "profile:version",
    )
    require(profile["status"] == "active", "profile:status")
    require(
        profile["repository_paths"]
        == {
            "source": "new pipeline/state/state.yaml",
            "projection": "new pipeline/state/STATE.md",
            "profile": "new pipeline/state/renderer/k0b02_v5/projection-profile-v5.yaml",
        },
        "profile:paths",
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
    contract = profile["delta_contract"]
    require(
        set(contract)
        == {"baseline_source", "baseline_value", "delta_whitelist", "expected_patch"},
        "profile:delta_contract",
    )
    require(
        contract["baseline_source"]
        == {
            "path": "new pipeline/state/state.yaml",
            "sha256": "17624062836c03a45d0fb6c192cb78ae3d3c8cc441fdb02e8bcc73225e4f4550",
            "bytes": 38960,
        },
        "profile:baseline",
    )
    require(
        contract["delta_whitelist"]
        == [
            "generated_at",
            "projection_version",
            "status",
            "projection_profile.path",
            "projection_profile.sha256",
            "active_authority.K0b_02_artifact_event_implementation",
            "supporting_review_evidence.K0b_02_artifact_event_completion",
            "supporting_review_evidence.K0b_02_implementation_materialization",
            "work_items[work_item_id=K0b-02].status",
            "work_items[work_item_id=K0b-02].authority_path",
            "work_items[work_item_id=K0b-02].authority_sha256",
            "scope.K0b_02_implementation_authority",
        ],
        "profile:delta_whitelist",
    )
    return profile, digest(raw)


def _apply_patch(expected: dict[str, Any], patch: dict[str, Any]) -> None:
    for dotted, value in patch.items():
        if dotted.startswith("work_items[work_item_id=K0b-02]."):
            field = dotted.rsplit(".", 1)[1]
            require(field in WORK_ITEM_FIELDS, "profile:patch_path")
            item = next(
                x for x in expected["work_items"] if x["work_item_id"] == "K0b-02"
            )
            item[field] = copy.deepcopy(value)
            continue
        parts = dotted.split(".")
        cursor: dict[str, Any] = expected
        for part in parts[:-1]:
            require(isinstance(cursor, dict), "profile:patch_path")
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = copy.deepcopy(value)


def validate_transition(
    source: dict[str, Any], profile: dict[str, Any], profile_sha: str
) -> None:
    contract = profile["delta_contract"]
    expected = copy.deepcopy(contract["baseline_value"])
    _apply_patch(expected, contract["expected_patch"])
    expected["generated_at"] = source.get("generated_at")
    expected["projection_profile"] = {
        "path": profile["repository_paths"]["profile"],
        "sha256": profile_sha,
    }
    require(typed_equal(source, expected), "source:outside_delta_whitelist")
    try:
        recorded = datetime.fromisoformat(source["generated_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise RendererError("source:transition_time") from exc
    require(
        recorded.tzinfo is not None
        and recorded.utcoffset() == timezone.utc.utcoffset(recorded),
        "source:transition_time",
    )
    require(
        source["status"] == "K0b_02_implemented_validated_runtime_not_authorized",
        "source:status",
    )
    require(
        len(source["open_gates"]) == 7 and len(source["closed_gates"]) == 10,
        "source:gate_inventory",
    )
    require(
        source["scope"]["runtime_authority"] == "none"
        and source["scope"]["K0b_02_runtime_authority"] == "none",
        "source:runtime_authority",
    )


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
    require(
        path == ".gitattributes" or path.startswith("new pipeline/"),
        "source:root_reference",
    )
    require("\\" not in path and not DRIVE.match(path), "source:path_style")
    posix = PurePosixPath(path)
    require(
        not posix.is_absolute() and ".." not in posix.parts and str(posix) == path,
        "source:path_escape",
    )
    candidate = root.resolve()
    for part in posix.parts:
        candidate /= part
        reject_reparse(candidate, "source:reference")
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


def render_bytes(
    *, source_path: Path, profile_path: Path, repository_root: Path
) -> tuple[bytes, dict[str, str]]:
    source_raw, source = read_json(source_path, "source")
    profile, profile_sha = load_profile(profile_path)
    require(len(source_raw) <= profile["limits"]["maximum_source_bytes"], "source:size")
    validate_transition(source, profile, profile_sha)
    walk_references(source, repository_root, profile)
    for item in source["work_items"]:
        reference(
            item["authority_path"], item["authority_sha256"], repository_root, profile
        )
    paths, doc = profile["repository_paths"], profile["document_contract"]
    output = (
        f"{doc['heading']}\n\nSource: `{paths['source']}`\n\n"
        f"Source SHA-256: `{digest(source_raw)}`\n\nProjection profile: `{paths['profile']}`\n\n"
        f"Projection profile SHA-256: `{profile_sha}`\n\nProjection version: `5.0.0`\n\n"
        f"{doc['notice']}\n\n```yaml\n".encode("utf-8")
        + source_raw
        + b"```\n"
    )
    return output, {
        "source_sha256": digest(source_raw),
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
    actual = projection_path.read_bytes()
    require(actual == expected, "projection:byte_mismatch")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="state-renderer-v5")
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
    try:
        kwargs = {
            "source_path": args.source,
            "profile_path": args.profile,
            "repository_root": args.repository_root,
        }
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
