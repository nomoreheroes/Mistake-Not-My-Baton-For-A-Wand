from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


REPOSITORY = Path(__file__).resolve().parents[3]
PRODUCT = REPOSITORY / "new pipeline/harness/k0b01_v2"
if "k0b01_v2" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "k0b01_v2", PRODUCT / "__init__.py", submodule_search_locations=[str(PRODUCT)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

canonical = importlib.import_module("k0b01_v2.canonical")
contract = importlib.import_module("k0b01_v2.contract")
registry_compiler = importlib.import_module("k0b01_v2.registry_compiler")


EVENT_TYPES = (
    "command.received",
    "run.started",
    "artifact.version_created",
    "handoff.ready",
    "run.completed",
    "run.blocked",
    "run.abort_requested",
    "run.aborted",
    "artifact.published",
    "projection.requested",
    "projection.written",
    "projection.failed",
    "revision.requested",
    "gate.passed",
    "approval.requested",
    "approval.granted",
    "approval.rejected",
    "error.schema_mismatch",
    "error.tool_failure",
    "error.security_policy",
    "meta.incident_detected",
)


@pytest.fixture(scope="session")
def target() -> Path:
    actual = Path(os.environ["PIPELINE_K0B_ENV_TARGET"])
    assert actual.is_absolute() and actual.name in (
        "pipeline-v2-k0b01-final-disposition-implementation-v1-a",
        "pipeline-v2-k0b01-final-disposition-implementation-v1-b",
    )
    return actual


@pytest.fixture(scope="session")
def ctx(target: Path) -> contract.InputContext:
    pins = canonical.load_json((target / ".tmp/source-pins-accepted.json").read_bytes())
    return contract.InputContext(
        REPOSITORY,
        REPOSITORY
        / "new pipeline/evidence/k0b-01-implementation-input-manifest-v2.yaml",
        pins,
    )


@pytest.fixture(scope="session")
def oracle():
    path = REPOSITORY / "new pipeline/tests/k0b01_v2/independent_oracle.py"
    spec = importlib.util.spec_from_file_location("independent_k0b01_oracle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample(schema):
    if "const" in schema:
        return copy.deepcopy(schema["const"])
    if "enum" in schema:
        return copy.deepcopy(schema["enum"][0])
    kind = schema["type"]
    if kind == "object":
        return {key: sample(schema["properties"][key]) for key in schema["required"]}
    if kind == "array":
        return [sample(schema["items"]) for _ in range(schema.get("minItems", 0))]
    if kind == "string":
        return "a" * 64 if schema.get("pattern") == "^[0-9a-f]{64}$" else "synthetic"
    if kind in ("integer", "number"):
        return schema.get("minimum", 0)
    if kind == "boolean":
        return False
    if kind == "null":
        return None
    raise AssertionError(kind)


def envelope(ctx, event_type, profile="Alpha0"):
    row = next(row for row in ctx.registry["events"] if row["event_type"] == event_type)
    schema = ctx.schemas[row["schema"]["id"]]
    value = sample(schema["oneOf"][-1 if profile == "Alpha0" else 0])
    if profile == "Alpha0":
        value["schema_sha256"] = row["schema"]["sha256"]
        parts = [
            "v1"
            if field == "v1"
            else value["run_id"]
            if field == "run_id"
            else value["payload"][field]
            for field in row["idempotency_fields"]
        ]
        value["idempotency_key"] = hashlib.sha256(
            (
                json.dumps(
                    parts, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            ).encode("utf-8")
        ).hexdigest()
        if "artifact_version_id" not in value["payload"]:
            value["artifact_version_id"] = ""
    return value


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_alpha_event_positive(ctx, event_type):
    registry_compiler.validate_event(ctx, event_type, envelope(ctx, event_type))


@pytest.mark.parametrize("event_type", EVENT_TYPES[:5])
def test_f00_event_positive(ctx, event_type):
    registry_compiler.validate_event(ctx, event_type, envelope(ctx, event_type, "F00"))


@pytest.mark.parametrize("event_type", EVENT_TYPES)
@pytest.mark.parametrize(
    "fault",
    (
        "extra",
        "missing",
        "producer",
        "payload",
        "schema_id",
        "schema_hash",
        "idempotency",
        "artifact_identity",
    ),
)
def test_alpha_event_closed_negative(ctx, event_type, fault):
    value = envelope(ctx, event_type)
    if fault == "extra":
        value["unapproved"] = 1
    elif fault == "missing":
        del value["checkpoint_phase_id"]
    elif fault == "producer":
        value["producer_id"] = "unknown"
    elif fault == "payload":
        value["payload"]["undeclared"] = 1
    elif fault == "schema_id":
        value["schema_id"] = "unknown"
    elif fault == "schema_hash":
        value["schema_sha256"] = "0" * 64
    elif fault == "idempotency":
        value["idempotency_key"] = "0" * 64
    else:
        value["artifact_version_id"] = "different-artifact"
    with pytest.raises(canonical.ContractError):
        registry_compiler.validate_event(ctx, event_type, value)


@pytest.mark.parametrize(
    "fault",
    (
        "keyword",
        "ref",
        "duplicate_required",
        "open",
        "bool_limit",
        "unknown_type",
        "unknown_pattern",
        "duplicate_enum",
    ),
)
def test_bounded_schema_rejects(ctx, fault):
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
    if fault == "keyword":
        schema["unrecognized"] = True
    elif fault == "ref":
        schema["$ref"] = "outside"
    elif fault == "duplicate_required":
        schema["required"] *= 2
    elif fault == "open":
        schema["additionalProperties"] = True
    elif fault == "bool_limit":
        schema["properties"]["name"]["minLength"] = True
    elif fault == "unknown_type":
        schema["properties"]["name"]["type"] = "bytes"
    elif fault == "unknown_pattern":
        schema["properties"]["name"]["pattern"] = ".*"
    else:
        schema["properties"]["name"]["enum"] = ["x", "x"]
    with pytest.raises(canonical.ContractError):
        contract.validate_schema(
            schema, set(ctx.package["supported_JSON_Schema_keywords"])
        )


@pytest.mark.parametrize(
    "value,schema",
    [
        (True, {"type": "integer"}),
        (1, {"type": "boolean"}),
        (True, {"enum": [1]}),
        (1, {"const": True}),
        ("x", {"type": "string", "minLength": 2}),
        ([], {"type": "array", "items": {"type": "string"}, "minItems": 1}),
        (
            ["x", "x"],
            {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        ),
        (-1, {"type": "integer", "minimum": 0}),
    ],
)
def test_typed_schema_values(value, schema):
    with pytest.raises(canonical.ContractError):
        contract.validate(value, schema)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}\n',
        b"{}\r\n",
        b"{}\n\n",
        b"\xef\xbb\xbf{}\n",
        b'{"a":NaN}\n',
        b'{"a":"\xff"}\n',
        b"{}",
    ],
)
def test_canonical_json_rejects(raw):
    with pytest.raises(canonical.ContractError):
        canonical.load_json(raw)


@pytest.mark.parametrize(
    "raw", [b"a: 1\na: 2\n", b"a: &same value\nb: *same\n", b"a: 1\n\n"]
)
def test_canonical_yaml_rejects(raw):
    with pytest.raises(canonical.ContractError):
        canonical.load_yaml(raw)


def test_yaml_json_roundtrip_and_determinism():
    value = {
        "unicode": "\u03bb\u96ea",
        "sha": "0" * 64,
        "integer": 7,
        "bool": False,
        "none": None,
        "nested": [{"b": 2, "a": 1}],
    }
    assert canonical.load_yaml(canonical.yaml_bytes(value)) == value
    assert canonical.yaml_bytes(value) == canonical.yaml_bytes(
        dict(reversed(list(value.items())))
    )
    assert canonical.json_bytes(value) == canonical.json_bytes(
        dict(reversed(list(value.items())))
    )


def test_manifest_stale_source_pin(ctx):
    pins = copy.deepcopy(ctx.source_pins)
    pins[0]["sha256"] = "0" * 64
    with pytest.raises(canonical.ContractError, match="pin:SHA256"):
        contract.InputContext(REPOSITORY, ctx.manifest_path, pins)


def test_manifest_duplicate_or_missing_source(ctx):
    for pins in (ctx.source_pins[:-1], ctx.source_pins + [ctx.source_pins[0]]):
        with pytest.raises(canonical.ContractError):
            contract.InputContext(REPOSITORY, ctx.manifest_path, pins)


@pytest.mark.parametrize("ordinal", range(18))
def test_frozen_manifest_is_hash_only(ctx, ordinal):
    path = sorted(ctx.hash_only)[ordinal]
    with pytest.raises(canonical.ContractError, match="semantic_scope"):
        ctx.raw(path)


@pytest.mark.parametrize(
    "relative",
    (
        "../outside",
        "new pipeline/../outside",
        "C:/outside",
        "new pipeline\\outside",
        "new pipeline/unlisted.json",
    ),
)
def test_finite_repository_path_rejection(relative):
    with pytest.raises(canonical.ContractError):
        canonical.repository_file(REPOSITORY, relative, set())


def test_contract_package_fences_and_exact_inventory(ctx):
    assert len(ctx.schemas) == 21 and set(
        row["event_type"] for row in ctx.registry["events"]
    ) == set(EVENT_TYPES)
    assert ctx.package["runtime_enabled"] is False and ctx.package["capabilities"] == []
    assert ctx.registry["content_artifact_types"] == [
        "bootstrap.synthetic_result",
        "alpha0.key_decision",
    ]
    assert len(ctx.source_pins) == 35 and len(ctx.hash_only) == 18
    assert ctx.manifest["authority"]["phase_A_commit"]["five_gates_closed"] is True
