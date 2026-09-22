from __future__ import annotations

import copy
from typing import Any

from .canonical import json_bytes, require, sha256
from .contract import InputContext


FAMILIES = (
    "compiled_artifact_event_profile",
    "compiled_event_reachability_graph",
    "compiled_subscription_terminal_snapshot",
    "compiled_s_route_table_v2",
    "compiled_fanout_barrier_profile",
    "compiled_projection_checkpoint_profile",
)


def validate_registry(context: InputContext) -> dict[str, Any]:
    r = context.registry
    require(
        set(r)
        == {
            "F00_contract",
            "F04_rule",
            "F05_rule",
            "claim_layer",
            "content_artifact_types",
            "events",
            "output_families",
            "phase_fences",
            "producers",
            "profile",
            "registry_id",
            "routes",
            "run_states",
            "schema_version",
            "subscribers",
            "version",
            "supersedes",
            "projection_checkpoint",
        },
        "registry:fields",
    )
    require(
        r["schema_version"] == 2
        and r["version"] == "2.0.0"
        and r["profile"] == "Alpha0",
        "registry:version",
    )
    require(
        len(r["events"]) == 21 and len({e["event_type"] for e in r["events"]}) == 21,
        "registry:events",
    )
    require(
        len(r["routes"]) == 5 and len({x["route_id"] for x in r["routes"]}) == 5,
        "registry:routes",
    )
    require(
        r["output_families"]["registry_and_routing"] == list(FAMILIES),
        "registry:A_families",
    )
    require(
        r["output_families"]["resource_and_budget"]
        == [
            "compiled_resource_forecast",
            "compiled_checkpoint_phase_partition_v1",
            "compiled_checkpoint_publication_budget_v2",
        ],
        "registry:B_families",
    )
    p = r["projection_checkpoint"]
    require(
        p["pair_stems"] == ["fixture-decision"] and p["runtime_enabled"] is False,
        "registry:singleton",
    )
    require(
        r["supersedes"]["sha256"]
        == "38f0ad9652fde5b26268be476347e119be864110f3d4b2fbcc0d4682187f232f",
        "registry:predecessor",
    )
    projection = {
        e["event_type"]: e
        for e in r["events"]
        if e["event_type"].startswith("projection.")
    }
    require(
        set(projection)
        == {"projection.requested", "projection.written", "projection.failed"},
        "registry:projection_set",
    )
    require(
        projection["projection.requested"]["idempotency_fields"]
        == ["run_id", "v1", "decision_version_id", "projection_profile_sha256"],
        "registry:requested_key",
    )
    return r


def compile_outputs(context: InputContext) -> dict[str, bytes]:
    r = validate_registry(context)
    registry_sha = context.pin(context.package["registry_locator"])["sha256"]
    events = sorted(copy.deepcopy(r["events"]), key=lambda x: x["event_type"])
    routes = sorted(copy.deepcopy(r["routes"]), key=lambda x: x["route_id"])
    subscribers = sorted(copy.deepcopy(r["subscribers"]), key=lambda x: json_bytes(x))
    producers = sorted(copy.deepcopy(r["producers"]), key=lambda x: json_bytes(x))
    p = copy.deepcopy(r["projection_checkpoint"])
    payloads: dict[str, dict[str, Any]] = {
        FAMILIES[0]: {
            "family": FAMILIES[0],
            "registry_id": r["registry_id"],
            "registry_version": r["version"],
            "events": events,
            "producers": producers,
            "runtime_enabled": False,
        },
        FAMILIES[1]: {
            "family": FAMILIES[1],
            "event_types": [e["event_type"] for e in events],
            "routes": routes,
            "run_states": r["run_states"],
            "runtime_enabled": False,
        },
        FAMILIES[2]: {
            "family": FAMILIES[2],
            "subscribers": subscribers,
            "terminal_by_event": {
                e["event_type"]: e["terminal_disposition"] for e in events
            },
            "runtime_enabled": False,
        },
        FAMILIES[3]: {
            "family": FAMILIES[3],
            "routes": routes,
            "phase_fences": r["phase_fences"],
            "runtime_enabled": False,
        },
        FAMILIES[4]: {
            "family": FAMILIES[4],
            "F04_rule": r["F04_rule"],
            "F05_rule": r["F05_rule"],
            "barriers": [x for x in routes if x["barrier"] is not None],
            "runtime_enabled": False,
        },
        FAMILIES[5]: {
            "family": FAMILIES[5],
            "profile_id": p["profile_id"],
            "schema_version": p["schema_version"],
            "version": p["version"],
            "runtime_enabled": False,
            "owners": p["owners"],
            "pair_stems": p["pair_stems"],
            "pair_targets": p["pair_targets"],
            "checkpoint_target": p["checkpoint_target"],
            "replay_envelope": p["replay_envelope"],
            "source_registry_sha256": registry_sha,
        },
    }
    for payload in payloads.values():
        payload["compiler_package_version"] = "4.0.0"
        payload["input_manifest_sha256"] = context.manifest_sha256
    return {name: json_bytes(payloads[name]) for name in FAMILIES}


def receipt_a(context: InputContext, outputs: dict[str, bytes]) -> dict[str, Any]:
    require(tuple(outputs) == FAMILIES, "compiler:A_order")
    return {
        "receipt_id": "pipeline-v2.k0b02.registry-routing.v4",
        "schema_version": 2,
        "compiler_package_version": "4.0.0",
        "family": "registry_and_routing",
        "compiler": context.compiler_pin("registry_compiler.py"),
        "input_manifest_sha256": context.manifest_sha256,
        "registry": context.pin(context.package["registry_locator"]),
        "dependencies": {},
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


def compile_a(context: InputContext) -> tuple[dict[str, bytes], bytes]:
    outputs = compile_outputs(context)
    return outputs, json_bytes(receipt_a(context, outputs))
