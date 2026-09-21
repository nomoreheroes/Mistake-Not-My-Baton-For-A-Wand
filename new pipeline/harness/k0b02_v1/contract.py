from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from .canonical import (
    ContractError,
    load_json,
    load_yaml,
    no_reparse,
    repository_file,
    require,
    sha256,
    verify_pin,
)


def typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            typed_equal(left[k], right[k]) for k in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def validate_schema(schema: Any, keywords: set[str], depth: int = 0) -> None:
    require(depth <= 64 and isinstance(schema, dict) and bool(schema), "schema:shape")
    require(
        set(schema) <= keywords and "$ref" not in schema, "schema:unsupported_keyword"
    )
    if "$schema" in schema:
        require(
            schema["$schema"] == "https://json-schema.org/draft/2020-12/schema",
            "schema:dialect",
        )
    if "$id" in schema:
        require(
            isinstance(schema["$id"], str) and schema["$id"].startswith("pipeline-v2."),
            "schema:ID",
        )
    for group in ("oneOf", "anyOf"):
        if group in schema:
            require(
                isinstance(schema[group], list) and bool(schema[group]),
                "schema:variants",
            )
            for child in schema[group]:
                validate_schema(child, keywords, depth + 1)
    kind = schema.get("type")
    if kind is not None:
        require(
            kind
            in ("object", "array", "string", "integer", "number", "boolean", "null"),
            "schema:type",
        )
    if kind == "object":
        require(
            schema.get("additionalProperties") is False
            and isinstance(schema.get("properties"), dict),
            "schema:closed_object",
        )
        required = schema.get("required")
        require(
            isinstance(required, list)
            and len(required) == len(set(required))
            and set(required) <= set(schema["properties"]),
            "schema:required",
        )
        for child in schema["properties"].values():
            validate_schema(child, keywords, depth + 1)
    if kind == "array":
        require("items" in schema, "schema:items")
        validate_schema(schema["items"], keywords, depth + 1)
    for key in ("minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"):
        if key in schema:
            require(type(schema[key]) is int and schema[key] >= 0, "schema:limit")
    if "enum" in schema:
        require(
            isinstance(schema["enum"], list) and bool(schema["enum"]), "schema:enum"
        )
    if "pattern" in schema:
        require(
            schema["pattern"] in ("^[0-9a-f]{64}$", "^[a-z][a-z0-9._-]*$"),
            "schema:bounded_pattern",
        )


def validate(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    for group in ("oneOf", "anyOf"):
        if group in schema:
            passed = 0
            for child in schema[group]:
                try:
                    validate(value, child, path)
                    passed += 1
                except ContractError:
                    pass
            require(
                passed == 1 if group == "oneOf" else passed >= 1,
                "value:variant:" + path,
            )
    kind = schema.get("type")
    kinds = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "number": type(value) in (int, float),
        "boolean": type(value) is bool,
        "null": value is None,
    }
    if kind:
        require(kinds[kind], "value:type:" + path)
    if "const" in schema:
        require(typed_equal(value, schema["const"]), "value:const:" + path)
    if "enum" in schema:
        require(
            any(typed_equal(value, item) for item in schema["enum"]),
            "value:enum:" + path,
        )
    if kind == "object":
        require(
            set(schema["required"]) <= set(value) <= set(schema["properties"]),
            "value:fields:" + path,
        )
        for key, item in value.items():
            validate(item, schema["properties"][key], path + "." + key)
    elif kind == "array":
        require(
            schema.get("minItems", 0)
            <= len(value)
            <= schema.get("maxItems", len(value)),
            "value:count:" + path,
        )
        for index, item in enumerate(value):
            validate(item, schema["items"], path + "[" + str(index) + "]")
    elif kind == "string":
        require(
            schema.get("minLength", 0)
            <= len(value)
            <= schema.get("maxLength", len(value)),
            "value:length:" + path,
        )
        if "pattern" in schema:
            require(
                re.fullmatch(schema["pattern"], value) is not None,
                "value:pattern:" + path,
            )
    elif kind in ("integer", "number"):
        if "minimum" in schema:
            require(value >= schema["minimum"], "value:minimum:" + path)
        if "maximum" in schema:
            require(value <= schema["maximum"], "value:maximum:" + path)


class InputContext:
    """Finite K0b-02 input closure. HASH-ONLY inputs never become semantic inputs."""

    MANIFEST = "new pipeline/evidence/k0b-02-implementation-input-manifest-v1.yaml"
    PACKAGE = "new pipeline/contracts/k0b02/alpha0-kernel-contract-package-v3.json"

    def __init__(self, repository_root: Path, manifest_path: Path) -> None:
        require(repository_root.is_absolute(), "context:absolute_root")
        self.root = repository_root.resolve()
        require(
            manifest_path.resolve() == (self.root / self.MANIFEST).resolve(),
            "manifest:exact_locator",
        )
        no_reparse(self.root)
        no_reparse(manifest_path)
        raw = manifest_path.read_bytes()
        self.manifest = load_json(raw)
        self.manifest_sha256 = sha256(raw)
        require(
            self.manifest.get("status") == "frozen_implementation_inputs"
            and self.manifest.get("schema_version") == 1
            and self.manifest.get("request_sha256")
            == "b04ae991fbc6358eeb26b2feda00ff85abad7eadb378c4e188072431fa97c75d",
            "manifest:identity",
        )
        effective = self.manifest["effective_inputs"]
        frozen = self.manifest["frozen_HASH_ONLY_inputs"]
        require(
            len(effective) == len({p["path"] for p in effective}), "manifest:duplicate"
        )
        require(
            len(frozen) == 18 and len({p["path"] for p in frozen}) == 18,
            "manifest:frozen",
        )
        self.hash_only = {p["path"] for p in frozen}
        require(not self.hash_only & {p["path"] for p in effective}, "manifest:overlap")
        self.pins = {p["path"]: copy.deepcopy(p) for p in effective}
        self.allowed = set(self.pins) | self.hash_only
        for pin in effective + frozen:
            verify_pin(repository_file(self.root, pin["path"], self.allowed), pin)
        self.package = self.json(self.PACKAGE)
        require(
            self.package["runtime_enabled"] is False
            and self.package["capabilities"] == [],
            "package:runtime",
        )
        self.registry = self.json(self.package["registry_locator"])
        require(
            self.pins[self.package["registry_locator"]]["sha256"]
            == self.package["registry_complete_file_sha256"],
            "package:registry",
        )
        self.schemas: dict[str, dict[str, Any]] = {}
        keywords = set(self.package["supported_JSON_Schema_keywords"])
        for pin in self.package["contract_schemas"]:
            require(
                self.pins[pin["path"]]["sha256"] == pin["sha256"], "package:schema_pin"
            )
            schema = self.json(pin["path"])
            validate_schema(schema, keywords)
            require(schema["$id"] not in self.schemas, "package:duplicate_schema")
            self.schemas[schema["$id"]] = schema

    def raw(self, path: str) -> bytes:
        require(
            path in self.pins and path not in self.hash_only, "manifest:semantic_scope"
        )
        return verify_pin(
            repository_file(self.root, path, self.allowed), self.pins[path]
        )

    def json(self, path: str) -> dict[str, Any]:
        value = load_json(self.raw(path))
        require(isinstance(value, dict), "input:JSON_object")
        return value

    def yaml(self, path: str) -> dict[str, Any]:
        return load_yaml(self.raw(path), historical=True)

    def pin(self, path: str) -> dict[str, Any]:
        require(path in self.pins, "manifest:missing_pin")
        return copy.deepcopy(self.pins[path])

    def compiler_pin(self, name: str) -> dict[str, Any]:
        path = "new pipeline/harness/k0b02_v1/" + name
        self.raw(path)
        return self.pin(path)

    def provenance(self) -> dict[str, Any]:
        return {
            "implementation_input_manifest_sha256": self.manifest_sha256,
            "request_sha256": self.manifest["request_sha256"],
            "owner_disposition_sha256": self.manifest["owner_disposition_sha256"],
            "effective_input_count": len(self.pins),
            "runtime_enabled": False,
        }
