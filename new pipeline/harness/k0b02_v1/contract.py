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

    MANIFEST = "new pipeline/evidence/k0b-02-implementation-input-manifest-v2.yaml"
    PACKAGE = "new pipeline/contracts/k0b02/alpha0-kernel-contract-package-v4.json"

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
            and self.manifest.get("schema_version") == 2
            and self.manifest.get("request_sha256")
            == "e7d4b50531986195a2a47715bb7bc9dcd5d0f5b1210ad3909c3ea4c3de85d29c",
            "manifest:identity",
        )
        effective = self.manifest["effective_inputs"]
        frozen = self.manifest["frozen_HASH_ONLY_inputs"]
        require(
            len(effective) == len({p["path"] for p in effective}), "manifest:duplicate"
        )
        require(
            len(frozen) == self.manifest["frozen_HASH_ONLY_file_count"]
            and len({p["path"] for p in frozen}) == len(frozen),
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
        require(
            self.package["package_version"] == "4.0.0"
            and self.package["input_manifest_locator"] == self.MANIFEST,
            "package:version",
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
        self._runtime_profile_cache: dict[str, Any] | None = None

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

    def _runtime_raw(self, path: str) -> bytes:
        require(
            path.startswith("new pipeline/compiled/k0b02_v1/")
            or path.startswith("new pipeline/evidence/k0b-02-"),
            "compiled:path_scope",
        )
        candidate = (self.root / path).resolve()
        require(candidate.is_relative_to(self.root), "compiled:path_escape")
        no_reparse(candidate)
        require(candidate.is_file(), "compiled:missing")
        return candidate.read_bytes()

    def runtime_profile(self) -> dict[str, Any]:
        if self._runtime_profile_cache is not None:
            return copy.deepcopy(self._runtime_profile_cache)
        manifest_path = self.package["compiled_output_manifest_locator"]
        receipt_a_path = self.package["compiler_receipt_A_locator"]
        receipt_b_path = self.package["compiler_receipt_B_locator"]
        manifest_raw = self._runtime_raw(manifest_path)
        receipt_a_raw = self._runtime_raw(receipt_a_path)
        receipt_b_raw = self._runtime_raw(receipt_b_path)
        compiled = load_json(manifest_raw)
        receipt_a = load_json(receipt_a_raw)
        receipt_b = load_json(receipt_b_raw)
        require(
            compiled["manifest_id"] == "pipeline-v2.k0b02.compiled-output-manifest.v4"
            and compiled["compiler_package_version"] == "4.0.0"
            and compiled["input_manifest_sha256"] == self.manifest_sha256
            and compiled["runtime_enabled"] is False
            and compiled["result"] == "pass",
            "compiled:manifest_identity",
        )
        require(
            compiled["receipt_A_sha256"] == sha256(receipt_a_raw)
            and compiled["receipt_B_sha256"] == sha256(receipt_b_raw)
            and receipt_a["input_manifest_sha256"] == self.manifest_sha256
            and receipt_b["input_manifest_sha256"] == self.manifest_sha256
            and receipt_b["dependencies"]["receipt_A_sha256"] == sha256(receipt_a_raw),
            "compiled:receipt_chain",
        )
        locators = {
            item["family"]: item["path"]
            for item in self.package["compiled_output_locators"]
        }
        pins = {item["family"]: item for item in compiled["outputs"]}
        require(
            len(locators) == 9 and set(locators) == set(pins), "compiled:nine_outputs"
        )
        outputs: dict[str, dict[str, Any]] = {}
        output_hashes: dict[str, str] = {}
        for family in locators:
            raw = self._runtime_raw(locators[family])
            require(
                sha256(raw) == pins[family]["sha256"]
                and len(raw) == pins[family]["bytes"],
                "compiled:output_pin:" + family,
            )
            value = load_json(raw)
            require(
                value["family"] == family
                and value["compiler_package_version"] == "4.0.0"
                and value["input_manifest_sha256"] == self.manifest_sha256
                and value["runtime_enabled"] is False,
                "compiled:output_identity:" + family,
            )
            outputs[family] = value
            output_hashes[family] = pins[family]["sha256"]
        projection = outputs["compiled_projection_checkpoint_profile"]
        partition = outputs["compiled_checkpoint_phase_partition_v1"]
        budget = outputs["compiled_checkpoint_publication_budget_v2"]
        events = outputs["compiled_artifact_event_profile"]["events"]
        event_schemas = {
            event["event_type"]: event["schema"]["sha256"]
            for event in events
            if event["event_type"]
            in {"projection.requested", "projection.written", "projection.failed"}
        }
        require(len(event_schemas) == 3, "compiled:projection_event_schemas")
        pair_targets = projection["pair_targets"]
        pair_stems = projection["pair_stems"]
        require(
            len(pair_stems) == 1
            and set(pair_targets) == {"yaml", "markdown"}
            and budget["credit"]["retry"] == 0,
            "compiled:runtime_profile",
        )
        self._runtime_profile_cache = {
            "binding_id": "compiler-binding-" + sha256(manifest_raw)[:32],
            "integrated_manifest_sha256": sha256(manifest_raw),
            "input_manifest_sha256": self.manifest_sha256,
            "output_hashes": output_hashes,
            "event_schema_sha256": event_schemas,
            "phases": list(partition["phase_order"]),
            "triggers": list(partition["F15_boundary_triggers"]),
            "partition_digest": partition["partition_digest"],
            "thresholds": copy.deepcopy(budget["thresholds"]),
            "projection_attempt_cap": 1 + budget["credit"]["retry"],
            "pair_stem": pair_stems[0],
            "pair_paths": [pair_targets["yaml"], pair_targets["markdown"]],
            "checkpoint_path": projection["checkpoint_target"],
            "replay_envelope_path": projection["replay_envelope"],
            "runtime_enabled": False,
        }
        return copy.deepcopy(self._runtime_profile_cache)

    def provenance(self) -> dict[str, Any]:
        return {
            "implementation_input_manifest_sha256": self.manifest_sha256,
            "request_sha256": self.manifest["request_sha256"],
            "owner_disposition_sha256": self.manifest["owner_disposition_sha256"],
            "effective_input_count": len(self.pins),
            "runtime_enabled": False,
        }
