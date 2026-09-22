from __future__ import annotations

from typing import Any

from .binary_budget import stress_checkpoint
from .canonical import json_bytes, load_json, require, sha256
from .contract import InputContext


FAMILIES = (
    "compiled_resource_forecast",
    "compiled_checkpoint_phase_partition_v1",
    "compiled_checkpoint_publication_budget_v2",
)
A_FAMILIES = (
    "compiled_artifact_event_profile",
    "compiled_event_reachability_graph",
    "compiled_subscription_terminal_snapshot",
    "compiled_s_route_table_v2",
    "compiled_fanout_barrier_profile",
    "compiled_projection_checkpoint_profile",
)


def _policy(context: InputContext) -> dict[str, Any]:
    p = context.json(
        "new pipeline/registry/resource-budget-policy/k0b02-policy-v3.json"
    )
    require(
        p["policy_id"] == "pipeline-v2.k0b02.resource-budget-policy"
        and p["version"] == "3.0.0",
        "policy:identity",
    )
    require(
        p["runtime_enabled"] is False
        and p["supersedes"]["sha256"]
        == "556c84527a865c5d04b0c0bfd1fa8e79c58c3388d9c63f83049157851feaa42a",
        "policy:predecessor",
    )
    require(
        p["phase_fences_locator"]
        == "new pipeline/registry/alpha0/alpha0-routing-contract-v2.json",
        "policy:fences",
    )
    require(
        all(type(v) is int and v == 0 for v in p["credit"].values()), "policy:credit"
    )
    require(
        p["F15"]["authoritative_worst_case_object_count"] is None
        and p["F15"]["size_stress_completion_claim"] is False,
        "policy:F15_claim",
    )
    return p


def compile_outputs(context: InputContext, receipt_a_raw: bytes) -> dict[str, bytes]:
    a = load_json(receipt_a_raw)
    require(
        a["family"] == "registry_and_routing" and a["result"] == "pass",
        "budget:A_receipt",
    )
    hashes = {x["family"]: x["sha256"] for x in a["outputs"]}
    require(set(hashes) == set(A_FAMILIES), "budget:A_six")
    p = _policy(context)
    inputs = context.json(
        "new pipeline/registry/resource-budget-policy/k0b01-reference-inputs-v2.json"
    )
    stress = stress_checkpoint(inputs["current_stress_inputs"], p["thresholds"])
    require(
        stress["rounded_size_stressed_checkpoint_bytes"] == 30408704,
        "budget:checkpoint",
    )
    require(stress["size_stressed_phase_pack_bytes"] == 1033895936, "budget:phase_pack")
    phase_order = context.registry["phase_fences"]["phase_order"]
    partition_core = {
        "phase_order": phase_order,
        "members": p["phase_members"],
        "F15_boundary_triggers": context.registry["phase_fences"][
            "F15_boundary_triggers"
        ],
        "exact_trigger_count": 4,
        "predecessor_seal_required": True,
        "post_F15_model_calls": 0,
        "runtime_enabled": False,
    }
    partition_core["partition_digest"] = sha256(json_bytes(partition_core))
    payloads = {
        FAMILIES[0]: {
            "family": FAMILIES[0],
            "policy_id": p["policy_id"],
            "reference_results_count": len(inputs["cases"]),
            "current_size_stress": stress,
            "F15_authoritative_worst_case_object_count": None,
            "phase_completion_claim": False,
            "runtime_enabled": False,
        },
        FAMILIES[1]: {"family": FAMILIES[1], **partition_core},
        FAMILIES[2]: {
            "family": FAMILIES[2],
            "thresholds": p["thresholds"],
            "credit": p["credit"],
            "approved_publications": p["runtime_publications"]["approved_exact"],
            "planning_pack_factor": p["planning_pack_factor"],
            "current_size_stress": stress,
            "runtime_enabled": False,
        },
    }
    for payload in payloads.values():
        payload["compiler_package_version"] = "4.0.0"
        payload["input_manifest_sha256"] = context.manifest_sha256
    return {name: json_bytes(payloads[name]) for name in FAMILIES}


def receipt_b(
    context: InputContext, receipt_a_raw: bytes, outputs: dict[str, bytes]
) -> dict[str, Any]:
    a = load_json(receipt_a_raw)
    require(tuple(outputs) == FAMILIES, "compiler:B_order")
    return {
        "receipt_id": "pipeline-v2.k0b02.resource-budget.v4",
        "schema_version": 2,
        "compiler_package_version": "4.0.0",
        "family": "resource_and_budget",
        "compiler": context.compiler_pin("budget_compiler.py"),
        "input_manifest_sha256": context.manifest_sha256,
        "policy": context.pin(
            "new pipeline/registry/resource-budget-policy/k0b02-policy-v3.json"
        ),
        "dependencies": {
            "receipt_A_sha256": sha256(receipt_a_raw),
            "receipt_A_output_hashes": {x["family"]: x["sha256"] for x in a["outputs"]},
        },
        "outputs": [
            {
                "family": name,
                "sha256": sha256(outputs[name]),
                "bytes": len(outputs[name]),
            }
            for name in FAMILIES
        ],
        "runtime_enabled": False,
        "result": "pass",
    }


def compile_b(
    context: InputContext, receipt_a_raw: bytes
) -> tuple[dict[str, bytes], bytes]:
    outputs = compile_outputs(context, receipt_a_raw)
    return outputs, json_bytes(receipt_b(context, receipt_a_raw, outputs))


def integrated_manifest(
    context: InputContext, a_raw: bytes, b_raw: bytes, all_outputs: dict[str, bytes]
) -> bytes:
    require(set(all_outputs) == set(A_FAMILIES + FAMILIES), "manifest:nine")
    b = load_json(b_raw)
    require(
        b["dependencies"]["receipt_A_sha256"] == sha256(a_raw), "manifest:A_binding"
    )
    return json_bytes(
        {
            "manifest_id": "pipeline-v2.k0b02.compiled-output-manifest.v4",
            "schema_version": 2,
            "compiler_package_version": "4.0.0",
            "input_manifest_sha256": context.manifest_sha256,
            "receipt_A_sha256": sha256(a_raw),
            "receipt_B_sha256": sha256(b_raw),
            "outputs": [
                {
                    "family": name,
                    "sha256": sha256(all_outputs[name]),
                    "bytes": len(all_outputs[name]),
                }
                for name in A_FAMILIES + FAMILIES
            ],
            "owners": context.registry["projection_checkpoint"]["owners"],
            "consumer_interfaces": [
                "transaction_writer",
                "projector",
                "publisher",
                "reconciliation",
                "phase_seal",
                "clone_only_replay",
            ],
            "runtime_enabled": False,
            "result": "pass",
        }
    )
