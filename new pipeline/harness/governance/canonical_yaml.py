"""Fail-closed canonical-yaml-v1 verifier.

The module has no repository-write, network, database, subprocess, model, or
provider-API capability. Its CLI reads one file and writes one result to
stdout (or one validation error to stderr).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, NoReturn
import unicodedata

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import AliasEvent
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


_CORE_TAG_PREFIX = "tag:yaml.org,2002:"
_MAP_TAG = _CORE_TAG_PREFIX + "map"
_SEQ_TAG = _CORE_TAG_PREFIX + "seq"
_STR_TAG = _CORE_TAG_PREFIX + "str"
_NULL_TAG = _CORE_TAG_PREFIX + "null"
_BOOL_TAG = _CORE_TAG_PREFIX + "bool"
_INT_TAG = _CORE_TAG_PREFIX + "int"
_FLOAT_TAG = _CORE_TAG_PREFIX + "float"
_MERGE_TAG = _CORE_TAG_PREFIX + "merge"
_ALLOWED_TAGS = {
    _MAP_TAG,
    _SEQ_TAG,
    _STR_TAG,
    _NULL_TAG,
    _BOOL_TAG,
    _INT_TAG,
    _FLOAT_TAG,
}
_EXCLUDED_PATH_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SAFE_INTEGER_MIN = -9_007_199_254_740_991
_SAFE_INTEGER_MAX = 9_007_199_254_740_991


class CanonicalYamlError(ValueError):
    """Typed, fail-closed canonicalization error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class VerificationResult:
    """Result of comparing a declared semantic hash with a computed hash."""

    declared_sha256: str
    computed_sha256: str
    matches: bool


def _fail(code: str, message: str) -> NoReturn:
    raise CanonicalYamlError(code, message)


def _new_yaml() -> YAML:
    parser = YAML(typ="safe", pure=True)
    parser.version = (1, 2)
    parser.allow_duplicate_keys = False
    return parser


def _contains_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _scan_for_aliases_and_anchors(text: str) -> None:
    try:
        events = _new_yaml().parse(text)
        for event in events:
            if isinstance(event, AliasEvent):
                _fail("ALIAS_FORBIDDEN", "YAML aliases are forbidden")
            if getattr(event, "anchor", None) is not None:
                _fail("ANCHOR_FORBIDDEN", "YAML anchors are forbidden")
    except CanonicalYamlError:
        raise
    except YAMLError as error:
        _fail("YAML_SYNTAX", str(error))


def _parse_integer(value: str) -> int:
    token = value.replace("_", "")
    sign = 1
    if token.startswith(("+", "-")):
        if token[0] == "-":
            sign = -1
        token = token[1:]
    lowered = token.lower()
    try:
        if lowered.startswith("0b"):
            result = int(token[2:], 2)
        elif lowered.startswith("0o"):
            result = int(token[2:], 8)
        elif lowered.startswith("0x"):
            result = int(token[2:], 16)
        else:
            result = int(token, 10)
    except ValueError:
        _fail("NON_JSON_VALUE", f"invalid YAML integer scalar {value!r}")
    result *= sign
    if not _SAFE_INTEGER_MIN <= result <= _SAFE_INTEGER_MAX:
        _fail("INTEGER_RANGE", "integer is outside the exact binary64 safe range")
    return result


def _parse_float(value: str) -> float:
    token = value.replace("_", "")
    if token.lower().lstrip("+-") in {".inf", ".nan"}:
        _fail("NON_FINITE_NUMBER", "non-finite YAML floats are forbidden")
    try:
        result = float(token)
    except ValueError:
        _fail("NON_JSON_VALUE", f"invalid YAML float scalar {value!r}")
    if not math.isfinite(result):
        _fail("NON_FINITE_NUMBER", "non-finite numbers are forbidden")
    return result


def _scalar_value(node: ScalarNode) -> Any:
    if node.tag == _STR_TAG:
        if _contains_surrogate(node.value):
            _fail("UNICODE_SURROGATE", "Unicode surrogate code points are forbidden")
        return node.value
    if node.tag == _NULL_TAG:
        return None
    if node.tag == _BOOL_TAG:
        lowered = node.value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        _fail("NON_JSON_VALUE", f"invalid YAML boolean scalar {node.value!r}")
    if node.tag == _INT_TAG:
        return _parse_integer(node.value)
    if node.tag == _FLOAT_TAG:
        return _parse_float(node.value)
    _fail("TAG_FORBIDDEN", f"tag {node.tag!r} is outside the allowed core set")


def _node_to_value(node: Node) -> Any:
    if node.tag == _MERGE_TAG:
        _fail("MERGE_KEY_FORBIDDEN", "YAML merge keys are forbidden")
    if node.tag not in _ALLOWED_TAGS:
        _fail("TAG_FORBIDDEN", f"tag {node.tag!r} is outside the allowed core set")

    if isinstance(node, ScalarNode):
        return _scalar_value(node)

    if isinstance(node, SequenceNode):
        if node.tag != _SEQ_TAG:
            _fail("TAG_FORBIDDEN", f"sequence tag {node.tag!r} is forbidden")
        return [_node_to_value(child) for child in node.value]

    if isinstance(node, MappingNode):
        if node.tag != _MAP_TAG:
            _fail("TAG_FORBIDDEN", f"mapping tag {node.tag!r} is forbidden")
        result: dict[str, Any] = {}
        raw_keys: set[str] = set()
        normalized_keys: set[str] = set()
        for key_node, value_node in node.value:
            if key_node.tag == _MERGE_TAG:
                _fail("MERGE_KEY_FORBIDDEN", "YAML merge keys are forbidden")
            if not isinstance(key_node, ScalarNode) or key_node.tag != _STR_TAG:
                _fail("NON_STRING_KEY", "all YAML mapping keys must be strings")
            key = _scalar_value(key_node)
            if key in raw_keys:
                _fail("DUPLICATE_KEY", f"duplicate mapping key {key!r}")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized_keys:
                _fail(
                    "NORMALIZED_KEY_COLLISION",
                    f"mapping keys collide after NFC normalization at {key!r}",
                )
            raw_keys.add(key)
            normalized_keys.add(normalized_key)
            result[key] = _node_to_value(value_node)
        return result

    _fail("NON_JSON_VALUE", f"unsupported YAML node {type(node).__name__}")


def _parse_one_document(data: bytes) -> Any:
    if data.startswith(b"\xef\xbb\xbf"):
        _fail("BOM_FORBIDDEN", "UTF-8 byte order mark is forbidden")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        _fail("UTF8_DECODE", str(error))
    if _contains_surrogate(text):
        _fail("UNICODE_SURROGATE", "Unicode surrogate code points are forbidden")

    _scan_for_aliases_and_anchors(text)
    try:
        documents = list(_new_yaml().compose_all(text))
    except YAMLError as error:
        _fail("YAML_SYNTAX", str(error))
    if len(documents) != 1 or documents[0] is None:
        _fail("DOCUMENT_COUNT", "exactly one non-empty YAML document is required")
    return _node_to_value(documents[0])


def _parse_excluded_path(excluded_field_path: str) -> tuple[str, ...]:
    if not isinstance(excluded_field_path, str) or not _EXCLUDED_PATH_RE.fullmatch(
        excluded_field_path
    ):
        _fail("EXCLUDED_PATH_SYNTAX", "excluded field path has invalid syntax")
    return tuple(excluded_field_path.split("."))


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_copy_value(child) for child in value]
    return value


def _exclude_on_copy(value: Any, segments: tuple[str, ...]) -> Any:
    copied = _copy_value(value)
    cursor = copied
    for segment in segments[:-1]:
        if not isinstance(cursor, dict):
            _fail(
                "EXCLUDED_PATH_NON_MAPPING",
                f"excluded field parent for {segment!r} is not a mapping",
            )
        if segment not in cursor:
            _fail("EXCLUDED_PATH_MISSING", f"excluded path segment {segment!r} is missing")
        cursor = cursor[segment]
    if not isinstance(cursor, dict):
        _fail("EXCLUDED_PATH_NON_MAPPING", "excluded field parent is not a mapping")
    leaf = segments[-1]
    if leaf not in cursor:
        _fail("EXCLUDED_PATH_MISSING", f"excluded field {leaf!r} is missing")
    del cursor[leaf]
    return copied


def _normalize_value(value: Any) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not _SAFE_INTEGER_MIN <= value <= _SAFE_INTEGER_MAX:
            _fail("INTEGER_RANGE", "integer is outside the exact binary64 safe range")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            _fail("NON_FINITE_NUMBER", "non-finite numbers are forbidden")
        return value
    if type(value) is str:
        if _contains_surrogate(value):
            _fail("UNICODE_SURROGATE", "Unicode surrogate code points are forbidden")
        return unicodedata.normalize("NFC", value)
    if type(value) is list:
        return [_normalize_value(child) for child in value]
    if type(value) is dict:
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            if type(key) is not str:
                _fail("NON_STRING_KEY", "all mapping keys must be strings")
            if _contains_surrogate(key):
                _fail("UNICODE_SURROGATE", "Unicode surrogate keys are forbidden")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                _fail(
                    "NORMALIZED_KEY_COLLISION",
                    f"mapping keys collide after NFC normalization at {key!r}",
                )
            normalized[normalized_key] = _normalize_value(child)
        return normalized
    _fail("NON_JSON_VALUE", f"value type {type(value).__name__} is not JSON-compatible")


def parse_validate_and_normalize_yaml_bytes(
    data: bytes, excluded_field_path: str
) -> Any:
    """Parse, validate, exclude one field on a copy, and NFC-normalize."""

    if type(data) is not bytes:
        _fail("INPUT_TYPE", "input must be bytes")
    segments = _parse_excluded_path(excluded_field_path)
    parsed = _parse_one_document(data)
    without_self_hash = _exclude_on_copy(parsed, segments)
    return _normalize_value(without_self_hash)


def _escape_string(value: str) -> str:
    if _contains_surrogate(value):
        _fail("UNICODE_SURROGATE", "Unicode surrogate code points are forbidden")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _float_to_jcs(value: float) -> str:
    if not math.isfinite(value):
        _fail("NON_FINITE_NUMBER", "non-finite numbers are forbidden")
    if value == 0.0:
        return "0"

    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    rendered = repr(magnitude).lower()
    if "e" in rendered:
        mantissa, exponent_text = rendered.split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa = rendered
        exponent = 0
    if "." in mantissa:
        integer_part, fractional_part = mantissa.split(".", 1)
    else:
        integer_part, fractional_part = mantissa, ""
    digits = integer_part + fractional_part
    decimal_position = len(integer_part) + exponent

    leading_zero_count = len(digits) - len(digits.lstrip("0"))
    digits = digits.lstrip("0")
    decimal_position -= leading_zero_count
    digits = digits.rstrip("0")
    if not digits:
        return "0"

    if 1e-6 <= magnitude < 1e21:
        if decimal_position <= 0:
            body = "0." + ("0" * -decimal_position) + digits
        elif decimal_position >= len(digits):
            body = digits + ("0" * (decimal_position - len(digits)))
        else:
            body = digits[:decimal_position] + "." + digits[decimal_position:]
        return sign + body

    scientific_exponent = decimal_position - 1
    coefficient = digits[0]
    if len(digits) > 1:
        coefficient += "." + digits[1:]
    exponent_sign = "+" if scientific_exponent >= 0 else "-"
    return sign + coefficient + "e" + exponent_sign + str(abs(scientific_exponent))


def _serialize_jcs(value: Any) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        if not _SAFE_INTEGER_MIN <= value <= _SAFE_INTEGER_MAX:
            _fail("INTEGER_RANGE", "integer is outside the exact binary64 safe range")
        return str(value)
    if type(value) is float:
        return _float_to_jcs(value)
    if type(value) is str:
        return _escape_string(value)
    if type(value) is list:
        return "[" + ",".join(_serialize_jcs(child) for child in value) + "]"
    if type(value) is dict:
        for key in value:
            if type(key) is not str:
                _fail("NON_STRING_KEY", "all mapping keys must be strings")
            if _contains_surrogate(key):
                _fail("UNICODE_SURROGATE", "Unicode surrogate keys are forbidden")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        members = (
            _escape_string(key) + ":" + _serialize_jcs(value[key]) for key in keys
        )
        return "{" + ",".join(members) + "}"
    _fail("NON_JSON_VALUE", f"value type {type(value).__name__} is not JSON-compatible")


def canonicalize_validated_value(value: Any) -> bytes:
    """Normalize a JSON-compatible value and encode it as RFC 8785 bytes."""

    normalized = _normalize_value(value)
    return _serialize_jcs(normalized).encode("utf-8")


def calculate_canonical_payload_sha256(
    data: bytes, excluded_field_path: str
) -> str:
    """Calculate canonical-yaml-v1 SHA-256 for one YAML byte string."""

    normalized = parse_validate_and_normalize_yaml_bytes(data, excluded_field_path)
    return sha256(canonicalize_validated_value(normalized)).hexdigest()


def verify_declared_canonical_payload_sha256(
    data: bytes, excluded_field_path: str, declared_sha256: str
) -> VerificationResult:
    """Compare a declared hash with the computed canonical-yaml-v1 hash."""

    if not isinstance(declared_sha256, str) or not _SHA256_RE.fullmatch(
        declared_sha256
    ):
        _fail("DECLARED_HASH_FORMAT", "declared SHA-256 must be 64 lowercase hex")
    computed = calculate_canonical_payload_sha256(data, excluded_field_path)
    return VerificationResult(
        declared_sha256=declared_sha256,
        computed_sha256=computed,
        matches=hmac.compare_digest(declared_sha256, computed),
    )


def _result_json(result: VerificationResult) -> str:
    return json.dumps(
        {
            "computed_sha256": result.computed_sha256,
            "declared_sha256": result.declared_sha256,
            "matches": result.matches,
            "profile": "canonical-yaml-v1",
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify canonical-yaml-v1 SHA-256")
    parser.add_argument("file", type=Path)
    parser.add_argument("--exclude", required=True, dest="excluded_field_path")
    parser.add_argument("--expected", required=True, dest="declared_sha256")
    arguments = parser.parse_args(argv)
    try:
        data = arguments.file.read_bytes()
        result = verify_declared_canonical_payload_sha256(
            data,
            arguments.excluded_field_path,
            arguments.declared_sha256,
        )
    except (CanonicalYamlError, OSError) as error:
        if isinstance(error, CanonicalYamlError):
            payload = {"error_code": error.code, "message": error.message}
        else:
            payload = {"error_code": "FILE_READ", "message": str(error)}
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(_result_json(result))
    return 0 if result.matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
