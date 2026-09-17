from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from .canonical import (
    ContractError,
    json_bytes,
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
    require(set(schema) <= keywords, "schema:unsupported_keyword")
    require("$ref" not in schema, "schema:reference")
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
            for variant in schema[group]:
                validate_schema(variant, keywords, depth + 1)
    if "type" in schema:
        require(
            schema["type"]
            in ("object", "array", "string", "integer", "number", "boolean", "null"),
            "schema:type",
        )
    if schema.get("type") == "object":
        require(
            schema.get("additionalProperties") is False
            and isinstance(schema.get("properties"), dict),
            "schema:closed_object",
        )
        required = schema.get("required")
        require(
            isinstance(required, list)
            and all(isinstance(k, str) for k in required)
            and len(required) == len(set(required))
            and set(required) <= set(schema["properties"]),
            "schema:required",
        )
        for child in schema["properties"].values():
            validate_schema(child, keywords, depth + 1)
    if schema.get("type") == "array":
        require("items" in schema, "schema:items")
        validate_schema(schema["items"], keywords, depth + 1)
    for limit in (
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
    ):
        if limit in schema:
            require(type(schema[limit]) is int and schema[limit] >= 0, "schema:limit")
    if "enum" in schema:
        require(
            isinstance(schema["enum"], list) and bool(schema["enum"]), "schema:enum"
        )
        require(
            len({json_bytes(v) for v in schema["enum"]}) == len(schema["enum"]),
            "schema:duplicate_enum",
        )
    if "pattern" in schema:
        require(
            schema["pattern"] in ("^[0-9a-f]{64}$", "^[a-z][a-z0-9._-]*$"),
            "schema:bounded_pattern",
        )
    if "uniqueItems" in schema:
        require(type(schema["uniqueItems"]) is bool, "schema:uniqueItems")


def validate(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    for group in ("oneOf", "anyOf"):
        if group in schema:
            passed = 0
            for variant in schema[group]:
                try:
                    validate(value, variant, path)
                    passed += 1
                except ContractError:
                    pass
            require(
                passed == 1 if group == "oneOf" else passed >= 1,
                "value:variant:" + path,
            )
    kind = schema.get("type")
    if kind is not None:
        matches = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "integer": type(value) is int,
            "number": type(value) in (int, float),
            "boolean": type(value) is bool,
            "null": value is None,
        }
        require(matches[kind], "value:type:" + path)
    if "const" in schema:
        require(typed_equal(value, schema["const"]), "value:const:" + path)
    if "enum" in schema:
        require(
            any(typed_equal(value, expected) for expected in schema["enum"]),
            "value:enum:" + path,
        )
    if kind == "object":
        properties = schema["properties"]
        require(
            set(schema["required"]) <= set(value) <= set(properties),
            "value:fields:" + path,
        )
        for key, item in value.items():
            validate(item, properties[key], path + "." + key)
    elif kind == "array":
        require(
            schema.get("minItems", 0)
            <= len(value)
            <= schema.get("maxItems", len(value)),
            "value:count:" + path,
        )
        if schema.get("uniqueItems"):
            require(
                len({json_bytes(item) for item in value}) == len(value),
                "value:duplicates:" + path,
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
    """Finite data-supplied pins. Hash-only provenance never becomes a module input."""

    def __init__(
        self,
        repository_root: Path,
        manifest_path: Path,
        source_pins: list[dict[str, Any]],
    ) -> None:
        self.root = repository_root.resolve()
        require(
            repository_root.is_absolute()
            and manifest_path
            == self.root
            / "new pipeline/evidence/k0b-01-implementation-input-manifest-v2.yaml",
            "manifest:exact_locator",
        )
        no_reparse(self.root)
        no_reparse(manifest_path)
        self.manifest_path = manifest_path
        raw = manifest_path.read_bytes()
        self.manifest = load_yaml(raw)
        require(
            self.manifest.get("status") == "immutable_implementation_entry_inputs",
            "manifest:status",
        )
        require(
            self.manifest.get("schema_version") == 1
            and type(self.manifest["schema_version"]) is int,
            "manifest:version",
        )
        require(
            self.manifest["authority"]["phase_A_commit"]["five_gates_closed"] is True,
            "manifest:entry_gate",
        )
        self.manifest_sha256 = sha256(raw)
        existing = self.manifest["exact_existing_inputs"]
        committed = self.manifest["phase_A_committed_artifacts"]
        require(
            len(existing) == 193 and len({p["path"] for p in existing}) == 193,
            "manifest:inventory",
        )
        self.hash_only = {
            p["path"]
            for p in existing
            if p["access"] == "hash_only_no_parse_import_copy_execute"
        }
        require(len(self.hash_only) == 18, "manifest:frozen_count")
        require(
            len(committed) == 18 and len({p["path"] for p in committed}) == 18,
            "manifest:phase_A_inventory",
        )
        require(
            len(source_pins) == len({p["path"] for p in source_pins}),
            "manifest:duplicate_source",
        )
        require(
            set(p["path"] for p in source_pins)
            == set(self.manifest["source_locators"]),
            "manifest:source_inventory",
        )
        self.source_pins = copy.deepcopy(source_pins)
        self.pins = {p["path"]: p for p in existing}
        for pin in committed:
            if pin["path"] in self.pins:
                require(
                    typed_equal(
                        {
                            k: self.pins[pin["path"]][k]
                            for k in ("path", "sha256", "bytes")
                        },
                        pin,
                    ),
                    "manifest:conflicting_pin",
                )
            self.pins[pin["path"]] = pin
        for pin in source_pins:
            require(
                pin["path"] not in self.pins and pin["path"] not in self.hash_only,
                "manifest:source_overlap",
            )
            self.pins[pin["path"]] = pin
        self.allowed = set(self.pins)
        for pin in self.pins.values():
            verify_pin(repository_file(self.root, pin["path"], self.allowed), pin)
        package_path = self.manifest["source_locators"][0]
        self.package = self.json(package_path)
        require(
            self.package["runtime_enabled"] is False
            and self.package["capabilities"] == [],
            "package:runtime_fence",
        )
        self.registry = self.json(self.package["registry_locator"])
        require(
            self.pins[self.package["registry_locator"]]["sha256"]
            == self.package["registry_complete_file_sha256"],
            "package:registry_pin",
        )
        self.schemas: dict[str, dict[str, Any]] = {}
        for event in self.registry["events"]:
            schema_pin = event["schema"]
            require(
                self.pins[schema_pin["path"]]["sha256"] == schema_pin["sha256"],
                "registry:schema_pin",
            )
            schema = self.json(schema_pin["path"])
            require(
                schema.get("$id") == schema_pin["id"]
                and schema_pin["id"] not in self.schemas,
                "registry:schema_ID",
            )
            validate_schema(schema, set(self.package["supported_JSON_Schema_keywords"]))
            self.schemas[schema_pin["id"]] = schema

    def raw(self, path: str) -> bytes:
        require(
            path not in self.hash_only and path in self.pins, "manifest:semantic_scope"
        )
        return verify_pin(
            repository_file(self.root, path, self.allowed), self.pins[path]
        )

    def json(self, path: str) -> dict[str, Any]:
        value = load_json(self.raw(path))
        require(isinstance(value, dict), "input:JSON_object")
        return value

    def yaml(self, path: str) -> dict[str, Any]:
        return load_yaml(
            self.raw(path),
            historical=path not in {pin["path"] for pin in self.source_pins},
        )

    def provenance(self) -> dict[str, Any]:
        return {
            "implementation_input_manifest_sha256": self.manifest_sha256,
            "authority": copy.deepcopy(self.manifest["authority"]),
            "source_pins": sorted(
                copy.deepcopy(self.source_pins), key=lambda p: p["path"]
            ),
            "canonicalization": self.package["canonicalization"],
        }

    def compiler_pin(self, filename: str) -> dict[str, Any]:
        matches = [p for p in self.source_pins if p["path"].endswith("/" + filename)]
        require(len(matches) == 1, "compiler:identity")
        self.raw(matches[0]["path"])
        return copy.deepcopy(matches[0])
