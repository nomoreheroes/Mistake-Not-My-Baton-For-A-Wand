from __future__ import annotations

import copy

import pytest

from fixture_support import ContractError, context, record
from k0b02_v1.budget_compiler import compile_b, integrated_manifest
from k0b02_v1.canonical import json_bytes, load_json
from k0b02_v1.contract import validate
from k0b02_v1.registry_compiler import compile_a, compile_outputs


def test_compile_valid() -> None:
    ctx = context()
    a, receipt_a = compile_a(ctx)
    b, receipt_b = compile_b(ctx, receipt_a)
    manifest = integrated_manifest(ctx, receipt_a, receipt_b, {**a, **b})
    assert len(a) == 6 and len(b) == 3 and b"compiled-output-manifest.v4" in manifest
    assert ctx.manifest_sha256.encode() in manifest
    for output in (*a.values(), *b.values()):
        value = load_json(output)
        assert value["compiler_package_version"] == "4.0.0"
        assert value["input_manifest_sha256"] == ctx.manifest_sha256
    record("compile_valid", outputs=9)


def test_compile_missing_ninth_and_B_binding() -> None:
    ctx = context()
    a, receipt_a = compile_a(ctx)
    b, receipt_b = compile_b(ctx, receipt_a)
    outputs = {**a, **b}
    outputs.pop("compiled_checkpoint_publication_budget_v2")
    with pytest.raises(ContractError, match="manifest:nine"):
        integrated_manifest(ctx, receipt_a, receipt_b, outputs)
    record("compile_missing_ninth")
    changed = bytearray(receipt_a)
    changed[-2] = ord(" ")
    with pytest.raises((ContractError, ValueError)):
        compile_b(ctx, bytes(changed))
    record("compile_missing_B_binding")


def test_A_has_no_reverse_B_binding() -> None:
    ctx = context()
    _, receipt_a = compile_a(ctx)
    parsed = ctx.json("new pipeline/registry/alpha0/alpha0-routing-contract-v2.json")
    assert b'"dependencies":{}' in receipt_a
    assert (
        "compiled_resource_forecast" in parsed["output_families"]["resource_and_budget"]
    )
    record("compile_A_reverse_B_binding")


def test_wrong_output_schema_rejected() -> None:
    ctx = context()
    schema = ctx.schemas[
        "pipeline-v2.k0b02.compiled-projection-checkpoint-profile-v1.schema"
    ]
    with pytest.raises(ContractError):
        validate({"profile_id": 7}, schema)
    record("compile_wrong_output_schema")


def test_registry_semantic_drift_and_duplicate_family_rejected() -> None:
    ctx = copy.deepcopy(context())
    drift = copy.deepcopy(ctx.registry)
    drift["routes"].pop()
    ctx.registry = drift
    with pytest.raises(ContractError, match="registry:routes"):
        compile_outputs(ctx)
    record("compile_registry_semantic_drift")

    ctx = copy.deepcopy(context())
    duplicate = copy.deepcopy(ctx.registry)
    duplicate["output_families"]["registry_and_routing"].append(
        "compiled_projection_checkpoint_profile"
    )
    ctx.registry = duplicate
    with pytest.raises(ContractError, match="registry:A_families"):
        compile_outputs(ctx)
    record("compile_duplicate_family")


def test_multiple_pair_stems_rejected() -> None:
    ctx = copy.deepcopy(context())
    changed = copy.deepcopy(ctx.registry)
    changed["projection_checkpoint"]["pair_stems"].append("shadow-decision")
    ctx.registry = changed
    with pytest.raises(ContractError, match="registry:singleton"):
        compile_outputs(ctx)
    assert json_bytes(changed) != json_bytes(context().registry)
    record("compile_multiple_pair_stems_rejected")


def test_runtime_profile_is_hash_bound_to_all_nine_outputs() -> None:
    ctx = context()
    profile = ctx.runtime_profile()
    assert len(profile["output_hashes"]) == 9
    assert profile["input_manifest_sha256"] == ctx.manifest_sha256
    assert profile["projection_attempt_cap"] == 1
    assert profile["runtime_enabled"] is False
    assert (
        profile["pair_stem"] == ctx.registry["projection_checkpoint"]["pair_stems"][0]
    )
    assert profile["pair_paths"] == [
        ctx.registry["projection_checkpoint"]["pair_targets"]["yaml"],
        ctx.registry["projection_checkpoint"]["pair_targets"]["markdown"],
    ]
    record("runtime_profile_nine_output_binding")


def test_runtime_profile_rejects_manifest_binding_and_output_tamper() -> None:
    ctx = copy.deepcopy(context())
    ctx._runtime_profile_cache = None
    original = ctx._runtime_raw
    manifest_path = ctx.package["compiled_output_manifest_locator"]

    def manifest_tamper(path: str) -> bytes:
        raw = original(path)
        if path == manifest_path:
            value = load_json(raw)
            value["input_manifest_sha256"] = "0" * 64
            return json_bytes(value)
        return raw

    ctx._runtime_raw = manifest_tamper
    with pytest.raises(ContractError, match="compiled:manifest_identity"):
        ctx.runtime_profile()
    record("compiled_manifest_binding_tamper")

    ctx = copy.deepcopy(context())
    ctx._runtime_profile_cache = None
    original = ctx._runtime_raw
    output_path = next(
        item["path"]
        for item in ctx.package["compiled_output_locators"]
        if item["family"] == "compiled_projection_checkpoint_profile"
    )

    def output_tamper(path: str) -> bytes:
        raw = original(path)
        return raw[:-1] + b" \n" if path == output_path else raw

    ctx._runtime_raw = output_tamper
    with pytest.raises(ContractError, match="compiled:output_pin"):
        ctx.runtime_profile()
    record("compiled_output_tamper")
