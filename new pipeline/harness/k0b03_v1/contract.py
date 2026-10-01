from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from canonical import CanonicalError, load_strict


HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")


class ContractError(ValueError):
    pass


def closed_object(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("object required")
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise ContractError(f"missing fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"unknown fields: {sorted(unknown)}")
    return value


def validate_scan_request(value: Any) -> dict[str, Any]:
    request = closed_object(
        value,
        {"schema_version", "authenticated", "profile_sha256", "caller_byte_cap", "fields"},
    )
    if request["schema_version"] != "1.0.0" or request["authenticated"] is not True:
        raise ContractError("closed authenticated v1 request required")
    if not isinstance(request["profile_sha256"], str) or not HEX64.fullmatch(request["profile_sha256"]):
        raise ContractError("invalid profile SHA-256")
    cap = request["caller_byte_cap"]
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1 or cap > 1048576:
        raise ContractError("invalid caller byte cap")
    fields = request["fields"]
    if not isinstance(fields, list) or not fields:
        raise ContractError("at least one field required")
    for field in fields:
        item = closed_object(field, {"field_type", "source_id", "safe_source_binding", "text_utf8"})
        if item["field_type"] != "untrusted_text":
            raise ContractError("only untrusted_text fields are admitted")
        if not isinstance(item["source_id"], str) or not SAFE_ID.fullmatch(item["source_id"]):
            raise ContractError("unsafe source ID")
        if not isinstance(item["safe_source_binding"], str) or not SAFE_ID.fullmatch(item["safe_source_binding"]):
            raise ContractError("unsafe source binding")
        if not isinstance(item["text_utf8"], str):
            raise ContractError("text_utf8 must be a string")
    return request


def validate_invocation_envelope(value: Any) -> dict[str, Any]:
    envelope = closed_object(
        value,
        {
            "schema_version",
            "effect_id",
            "executable",
            "executable_sha256",
            "executable_version",
            "arguments",
            "working_directory",
            "environment",
            "timeout_seconds",
            "cpu_seconds_maximum",
            "memory_bytes_maximum",
            "process_count_maximum",
            "output_bytes_maximum",
            "owned_process_tree",
            "cancellable",
            "expected_result",
        },
    )
    if envelope["schema_version"] != "1.0.0":
        raise ContractError("unsupported envelope version")
    if not isinstance(envelope["effect_id"], str) or not SAFE_ID.fullmatch(envelope["effect_id"]):
        raise ContractError("unsafe effect ID")
    if not isinstance(envelope["executable_sha256"], str) or not HEX64.fullmatch(envelope["executable_sha256"]):
        raise ContractError("invalid executable SHA-256")
    if not isinstance(envelope["executable"], str) or not envelope["executable"]:
        raise ContractError("invalid executable path")
    if not isinstance(envelope["executable_version"], str) or not envelope["executable_version"]:
        raise ContractError("invalid executable version")
    if not isinstance(envelope["working_directory"], str) or not envelope["working_directory"]:
        raise ContractError("invalid working directory")
    if not isinstance(envelope["arguments"], list) or not all(isinstance(x, str) for x in envelope["arguments"]):
        raise ContractError("arguments must be a string array")
    if not isinstance(envelope["environment"], dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in envelope["environment"].items()):
        raise ContractError("environment must contain string pairs")
    for key in ("timeout_seconds", "cpu_seconds_maximum", "memory_bytes_maximum", "process_count_maximum", "output_bytes_maximum"):
        if not isinstance(envelope[key], int) or isinstance(envelope[key], bool) or envelope[key] < 1:
            raise ContractError(f"invalid {key}")
    if envelope["owned_process_tree"] is not True:
        raise ContractError("owned process tree required")
    if not isinstance(envelope["cancellable"], bool):
        raise ContractError("cancellable must be boolean")
    if not isinstance(envelope["expected_result"], str) or not envelope["expected_result"]:
        raise ContractError("expected result enum required")
    return envelope


def validate_detector_profile(profile: Any) -> dict[str, Any]:
    required = {
        "profile_id", "profile_version", "classification", "input", "precedence",
        "labelled_secret", "jwt", "bearer", "provider_tokens", "high_entropy",
        "base64", "split_line", "finding", "mandatory_hygiene_statement",
    }
    result = closed_object(profile, required)
    if result["profile_id"] != "pipeline-v2.k0b03-detector-profile-v1":
        raise ContractError("unexpected detector profile")
    if result["profile_version"] != "1.0.0" or result["classification"] != "heuristic_hygiene_only":
        raise ContractError("unexpected detector version or classification")
    if len(result["precedence"]) != 9 or len(result["provider_tokens"]) != 18:
        raise ContractError("incomplete detector profile")
    return result


def load_contract(path: Path) -> Any:
    try:
        return load_strict(path)
    except CanonicalError as exc:
        raise ContractError(str(exc)) from exc
