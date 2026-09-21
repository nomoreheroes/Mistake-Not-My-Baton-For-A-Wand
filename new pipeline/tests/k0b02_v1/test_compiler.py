from __future__ import annotations

import copy

import pytest

from fixture_support import ContractError, context, record
from k0b02_v1.budget_compiler import compile_b, integrated_manifest
from k0b02_v1.canonical import json_bytes
from k0b02_v1.contract import validate
from k0b02_v1.registry_compiler import compile_a, compile_outputs


def test_compile_valid() -> None:
    ctx = context()
    a, receipt_a = compile_a(ctx)
    b, receipt_b = compile_b(ctx, receipt_a)
    manifest = integrated_manifest(ctx, receipt_a, receipt_b, {**a, **b})
    assert len(a) == 6 and len(b) == 3 and b"compiled-output-manifest.v3" in manifest
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
    ctx = context()
    drift = copy.deepcopy(ctx.registry)
    drift["routes"].pop()
    ctx.registry = drift
    with pytest.raises(ContractError, match="registry:routes"):
        compile_outputs(ctx)
    record("compile_registry_semantic_drift")

    ctx = context()
    duplicate = copy.deepcopy(ctx.registry)
    duplicate["output_families"]["registry_and_routing"].append(
        "compiled_projection_checkpoint_profile"
    )
    ctx.registry = duplicate
    with pytest.raises(ContractError, match="registry:A_families"):
        compile_outputs(ctx)
    record("compile_duplicate_family")


def test_multiple_pair_stems_rejected() -> None:
    ctx = context()
    changed = copy.deepcopy(ctx.registry)
    changed["projection_checkpoint"]["pair_stems"].append("shadow-decision")
    ctx.registry = changed
    with pytest.raises(ContractError, match="registry:singleton"):
        compile_outputs(ctx)
    assert json_bytes(changed) != json_bytes(context().registry)
    record("compile_multiple_pair_stems_rejected")
