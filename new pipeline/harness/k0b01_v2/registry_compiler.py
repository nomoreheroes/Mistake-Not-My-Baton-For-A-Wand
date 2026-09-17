from __future__ import annotations

import copy
import re
from typing import Any

from .canonical import json_bytes, load_yaml, require, sha256, yaml_bytes
from .contract import InputContext, typed_equal, validate


def closed(value: Any, fields: set[str], code: str) -> None:
    require(isinstance(value, dict) and set(value) == fields, code + ":fields")


def normative_events(context: InputContext) -> dict[str, dict[str, Any]]:
    paths = [p for p in context.pins if p.endswith("/k0b-01-planning-package-v1.2.md")]
    require(len(paths) == 1, "matrix:authority_identity")
    rows = {}
    for line in context.raw(paths[0]).decode("utf-8").splitlines():
        if not line.startswith("| `") or len(line.split("|")) != 8:
            continue
        event, producer, delivery, fields, activation, replay = [
            cell.strip().replace("`", "") for cell in line.strip("|").split("|")
        ]
        if "." not in event:
            continue
        require(event not in rows, "matrix:duplicate_event")
        alpha = delivery.split("; Alpha ")[-1]
        if alpha.startswith("F00 and Alpha: "):
            alpha = alpha.removeprefix("F00 and Alpha: ")
        subscriber, terminal_policy, state = alpha.split("/")
        key = re.search(r"key \(([^)]+)\)", replay)
        require(key is not None, "matrix:idempotency")
        rows[event] = {
            "producer": producer,
            "branch": {
                "subscriber": subscriber,
                "terminal_policy": terminal_policy,
                "state": state,
                "fields_read": fields.split(","),
                "activation_work_item": activation.split("Alpha ")[-1],
            },
            "replay_rule": replay.split("; key ")[0],
            "idempotency_fields": key.group(1).split(","),
        }
    require(len(rows) == 21, "matrix:exact_rows")
    return rows


def validate_registry(context: InputContext) -> dict[str, Any]:
    registry = context.json(context.package["registry_locator"])
    closed(
        registry,
        {
            "registry_id",
            "schema_version",
            "version",
            "profile",
            "claim_layer",
            "events",
            "routes",
            "run_states",
            "subscribers",
            "producers",
            "output_families",
            "phase_fences",
            "F00_contract",
            "content_artifact_types",
            "F05_rule",
            "F04_rule",
        },
        "registry",
    )
    require(
        type(registry["schema_version"]) is int
        and registry["schema_version"] == 1
        and registry["profile"] == "Alpha0",
        "registry:version",
    )
    require(
        registry["claim_layer"] == "registry_level_closed_21_event_Alpha0_definition",
        "registry:claim_layer",
    )
    events = registry["events"]
    normative = normative_events(context)
    require(
        {e["event_type"] for e in events} == set(normative),
        "registry:normative_event_set",
    )
    control_paths = [
        p
        for p in context.pins
        if p.endswith("/k0b-00-shared-control-plane-delta-v2.md")
    ]
    require(len(control_paths) == 1, "registry:control_authority")
    state_lines = [
        line
        for line in context.raw(control_paths[0]).decode("utf-8").splitlines()
        if line.startswith("The exhaustive run states remain ")
    ]
    require(
        len(state_lines) == 1
        and registry["run_states"]
        == re.findall(r"`([^`]+)`", state_lines[0].split(". Valid edges")[0]),
        "registry:run_states",
    )
    require(
        isinstance(events, list)
        and len(events) == context.package["event_schema_count"] == 21
        and len({e["event_type"] for e in events}) == 21,
        "registry:event_count",
    )
    subscribers: set[str] = set()
    producers: set[str] = set()
    f00 = context.json(registry["F00_contract"]["path"])
    require(
        context.pins[registry["F00_contract"]["path"]]["sha256"]
        == registry["F00_contract"]["sha256"],
        "registry:F00_pin",
    )
    retained: set[str] = set()
    for event in events:
        closed(
            event,
            {
                "event_type",
                "event_version",
                "schema",
                "producer",
                "profile_branches",
                "field_owners",
                "replay_rule",
                "idempotency_fields",
                "terminal_disposition",
                "persister",
                "runtime_enabled",
            },
            "event",
        )
        require(
            type(event["event_version"]) is int
            and event["event_version"] == 1
            and event["runtime_enabled"] is False
            and event["persister"] == "artifact_event",
            "event:version_fence",
        )
        producers.add(event["producer"])
        require(
            isinstance(event["replay_rule"], str)
            and event["replay_rule"]
            and isinstance(event["idempotency_fields"], list)
            and event["idempotency_fields"]
            and len(event["idempotency_fields"])
            == len(set(event["idempotency_fields"])),
            "event:replay",
        )
        branches = event["profile_branches"]
        expected = normative[event["event_type"]]
        require(
            typed_equal(branches.get("Alpha0"), expected["branch"])
            and event["producer"] == expected["producer"]
            and event["replay_rule"] == expected["replay_rule"]
            and event["idempotency_fields"] == expected["idempotency_fields"],
            "event:normative_matrix_difference",
        )
        require(set(branches) in ({"Alpha0"}, {"Alpha0", "F00"}), "event:profiles")
        schema = context.schemas[event["schema"]["id"]]
        require(len(schema["oneOf"]) == len(branches), "event:schema_branches")
        alpha_payload = schema["oneOf"][-1]["properties"]["payload"]
        require(
            schema["oneOf"][-1]["properties"]["event_type"]["const"]
            == event["event_type"],
            "event:schema_type",
        )
        for profile, branch in branches.items():
            closed(
                branch,
                {
                    "subscriber",
                    "terminal_policy",
                    "state",
                    "fields_read",
                    "activation_work_item",
                },
                "branch",
            )
            require(
                isinstance(branch["fields_read"], list)
                and branch["fields_read"]
                and len(branch["fields_read"]) == len(set(branch["fields_read"])),
                "branch:fields_read",
            )
            subscribers.add(branch["subscriber"])
            if profile == "F00":
                retained.add(event["event_type"])
                original = f00["event_profile"][event["event_type"]]
                require(
                    branch["subscriber"] == original["subscriber"]
                    and branch["terminal_policy"] == original["terminal_policy"]
                    and branch["activation_work_item"] == "historical_F00",
                    "branch:F00",
                )
                require(
                    typed_equal(
                        schema["oneOf"][0]["properties"]["payload"],
                        f00["schemas"][original["payload_schema_ref"]]["schema"],
                    ),
                    "branch:F00_payload",
                )
            else:
                require(
                    branch["subscriber"] not in ("bootstrap_sink", "bootstrap_readback")
                    and branch["activation_work_item"]
                    in registry["phase_fences"]["activation_work_items"],
                    "branch:Alpha_fence",
                )
                require(
                    set(branch["fields_read"]) <= set(alpha_payload["properties"]),
                    "branch:payload_fields",
                )
                require(
                    all(
                        event["field_owners"].get(k) == event["producer"]
                        for k in alpha_payload["properties"]
                    ),
                    "branch:field_owner",
                )
                require(
                    branch["state"]
                    in ("pending", "accepted_terminal", "observed_terminal"),
                    "branch:state",
                )
                if event["event_type"].startswith("error."):
                    require(
                        branch["terminal_policy"] == "block_run_and_enqueue_human"
                        and branch["subscriber"] == "human_blocker_queue"
                        and branch["state"] == "accepted_terminal",
                        "branch:error_terminal",
                    )
                if event["event_type"].startswith("meta."):
                    require(
                        branch["terminal_policy"] == "persist_incident_and_enqueue_W5"
                        and branch["subscriber"] == "w5_incident_queue"
                        and branch["state"] == "accepted_terminal",
                        "branch:incident_terminal",
                    )
        require(
            set(event["field_owners"]) == set(alpha_payload["properties"]),
            "branch:extra_field_owner",
        )
    require(retained == set(f00["event_profile"]), "registry:F00_event_set")
    require(
        sorted(subscribers) == registry["subscribers"]
        and sorted(producers) == registry["producers"],
        "registry:catalog",
    )
    fences = registry["phase_fences"]
    closed(
        fences,
        {
            "runtime_enabled",
            "capabilities",
            "activation_work_items",
            "phase_order",
            "predecessor_seal_required",
            "post_F15_model_calls",
            "F15_boundary_triggers",
        },
        "fences",
    )
    require(
        fences["runtime_enabled"] is False
        and fences["capabilities"] == []
        and fences["predecessor_seal_required"] is True
        and type(fences["post_F15_model_calls"]) is int
        and fences["post_F15_model_calls"] == 0,
        "fences:values",
    )
    phase_paths = [
        p
        for p in context.pins
        if p.endswith("/checkpoint-budget-policy/k0b-phase-partition-v1.yaml")
    ]
    require(len(phase_paths) == 1, "fences:policy_identity")
    phase_policy = context.yaml(phase_paths[0])
    require(
        fences["phase_order"]
        == [p["checkpoint_phase_id"] for p in phase_policy["phases"]]
        and fences["F15_boundary_triggers"]
        == [p["trigger_id"] for p in phase_policy["F15_boundary_trigger_allowlist"]],
        "fences:policy_match",
    )
    routes = registry["routes"]
    closed(
        registry["F04_rule"],
        {
            "barrier",
            "dynamic_membership",
            "members",
            "one_deduplicated_terminal_per_member",
            "peer_visibility_before_barrier",
        },
        "F04",
    )
    closed(
        registry["F05_rule"],
        {
            "revision_owner_zero_role_id",
            "producer_invocation_is_lineage_only",
            "owner_must_differ_from_producer_identity",
        },
        "F05",
    )
    require(
        registry["F04_rule"]["one_deduplicated_terminal_per_member"] is True
        and registry["F04_rule"]["dynamic_membership"] is False
        and registry["F04_rule"]["peer_visibility_before_barrier"] is False,
        "F04:closed_membership",
    )
    require(
        registry["F05_rule"]["producer_invocation_is_lineage_only"] is True
        and registry["F05_rule"]["owner_must_differ_from_producer_identity"] is True,
        "F05:owner_not_producer",
    )
    require(
        isinstance(routes, list)
        and len(routes) == context.package["route_count"] == 5
        and len({r["route_id"] for r in routes}) == 5,
        "routes:count",
    )
    require(len({r["class"] for r in routes}) == 5, "routes:class_count")
    for route in routes:
        closed(
            route,
            {
                "route_id",
                "class",
                "predicate",
                "targets",
                "dispatcher_calls",
                "barrier",
                "revision_owner",
                "phase_fences",
                "direct_actor_handoff",
            },
            "route",
        )
        require(
            route["direct_actor_handoff"] is False
            and typed_equal(route["phase_fences"], fences),
            "route:guards",
        )
        require(
            type(route["dispatcher_calls"]) is int
            and route["dispatcher_calls"] in (0, 1),
            "route:dispatcher_calls",
        )
        require(
            isinstance(route["predicate"], str)
            and route["predicate"]
            and isinstance(route["targets"], list)
            and len(route["targets"]) == len(set(route["targets"])),
            "route:structure",
        )
        if route["class"] == "parallel_review":
            require(
                route["targets"] == registry["F04_rule"]["members"]
                and route["barrier"]
                == registry["F04_rule"]["barrier"]
                == "all_required"
                and len(route["targets"]) == 2,
                "route:F04",
            )
        elif route["class"] == "revision":
            require(
                route["revision_owner"]
                == registry["F05_rule"]["revision_owner_zero_role_id"]
                and route["targets"] == [route["revision_owner"]],
                "route:F05",
            )
        else:
            require(
                route["barrier"] is None and route["revision_owner"] is None,
                "route:extra_semantics",
            )
        if route["class"] == "blocked":
            require(
                route["targets"] == [] and route["dispatcher_calls"] == 0,
                "route:blocked_effect",
            )
    families = registry["output_families"]
    request_paths = [
        p
        for p in context.pins
        if p.endswith(
            "/k0b-01-final-implementation-disposition-and-bounded-implementation-approval-request-v1.yaml"
        )
    ]
    require(len(request_paths) == 1, "families:authority_identity")
    partition_contract = context.yaml(request_paths[0])["phase_B_contract"][
        "compiler_partition"
    ]
    require(
        families["registry_and_routing"] == partition_contract["receipt_A_owns"]
        and families["resource_and_budget"] == partition_contract["receipt_B_owns"],
        "families:authority_match",
    )
    require(
        set(families) == {"registry_and_routing", "resource_and_budget"}
        and len(families["registry_and_routing"]) == 5
        and len(families["resource_and_budget"]) == 3,
        "families:partition",
    )
    require(
        len(set(families["registry_and_routing"] + families["resource_and_budget"]))
        == context.package["compiled_output_family_count"]
        == 8,
        "families:set",
    )
    return registry


def receipt(
    context: InputContext,
    owner: str,
    payloads: list[dict[str, Any]],
    compiler_filename: str,
    dependencies: dict[str, Any],
) -> bytes:
    families = context.registry["output_families"][owner]
    require(len(payloads) == len(families), "receipt:output_count")
    outputs = []
    for family, payload in zip(families, payloads):
        raw = json_bytes(payload)
        outputs.append(
            {
                "family": family,
                "sha256": sha256(raw),
                "bytes": len(raw),
                "canonical_payload": payload,
            }
        )
    return yaml_bytes(
        {
            "receipt_id": "pipeline-v2.alpha0." + owner + ".v2",
            "schema_version": 1,
            "owner": owner,
            "compiler": context.compiler_pin(compiler_filename),
            "inputs": context.provenance(),
            "dependencies": dependencies,
            "outputs": outputs,
            "diagnostics": [],
            "result": "pass",
            "runtime_enabled": False,
        }
    )


def compile_registry(context: InputContext) -> bytes:
    registry = validate_registry(context)
    events = sorted(
        copy.deepcopy(registry["events"]), key=lambda event: event["event_type"]
    )
    routes = sorted(
        copy.deepcopy(registry["routes"]), key=lambda route: route["route_id"]
    )
    graph = []
    snapshots = []
    for event in events:
        for profile, branch in sorted(event["profile_branches"].items()):
            terminal = branch["state"] in ("accepted_terminal", "observed_terminal")
            graph.append(
                {
                    "event_type": event["event_type"],
                    "profile": profile,
                    "producer": event["producer"],
                    "subscriber": branch["subscriber"],
                    "terminal": terminal,
                    "downstream_semantic_routes": []
                    if terminal
                    else [branch["subscriber"]],
                }
            )
            snapshots.append(
                {"event_type": event["event_type"], "profile": profile, **branch}
            )
    common = {
        "registry_sha256": context.pins[context.package["registry_locator"]]["sha256"],
        "runtime_enabled": False,
        "claim_layer": registry["claim_layer"],
    }
    payloads = [
        {
            **common,
            "events": events,
            "content_artifact_types": registry["content_artifact_types"],
        },
        {**common, "edges": graph, "dynamic_subscriptions": False},
        {**common, "snapshots": snapshots},
        {**common, "routes": routes, "phase_fences": registry["phase_fences"]},
        {
            **common,
            "F04": registry["F04_rule"],
            "F05": registry["F05_rule"],
            "direct_actor_handoff": False,
        },
    ]
    return receipt(
        context, "registry_and_routing", payloads, "registry_compiler.py", {}
    )


def validate_receipt(
    raw: bytes, context: InputContext, owner: str, accepted_sha256: str
) -> dict[str, Any]:
    require(sha256(raw) == accepted_sha256, "receipt:accepted_SHA")
    value = load_yaml(raw)
    closed(
        value,
        {
            "receipt_id",
            "schema_version",
            "owner",
            "compiler",
            "inputs",
            "dependencies",
            "outputs",
            "diagnostics",
            "result",
            "runtime_enabled",
        },
        "receipt",
    )
    require(
        value["owner"] == owner
        and type(value["schema_version"]) is int
        and value["schema_version"] == 1
        and value["result"] == "pass"
        and value["diagnostics"] == []
        and value["runtime_enabled"] is False,
        "receipt:acceptance",
    )
    require(typed_equal(value["inputs"], context.provenance()), "receipt:stale_inputs")
    compiler_name = value["compiler"]["path"].rsplit("/", 1)[-1]
    require(
        compiler_name
        == (
            "registry_compiler.py"
            if owner == "registry_and_routing"
            else "budget_compiler.py"
        ),
        "receipt:owner_compiler",
    )
    require(
        typed_equal(value["compiler"], context.compiler_pin(compiler_name)),
        "receipt:compiler_pin",
    )
    expected = context.registry["output_families"][owner]
    outputs = value["outputs"]
    require(
        isinstance(outputs, list)
        and len(outputs) == len(expected)
        and {o["family"] for o in outputs} == set(expected),
        "receipt:family_set",
    )
    require(
        len({o["family"] for o in outputs}) == len(outputs), "receipt:duplicate_family"
    )
    for output in outputs:
        closed(output, {"family", "sha256", "bytes", "canonical_payload"}, "output")
        payload = json_bytes(output["canonical_payload"])
        require(
            type(output["bytes"]) is int
            and output["bytes"] == len(payload)
            and output["sha256"] == sha256(payload),
            "receipt:payload_hash",
        )
    return value


def aggregate(
    context: InputContext,
    raw_a: bytes,
    accepted_a_sha: str,
    raw_b: bytes,
    accepted_b_sha: str,
) -> bytes:
    a = validate_receipt(raw_a, context, "registry_and_routing", accepted_a_sha)
    b = validate_receipt(raw_b, context, "resource_and_budget", accepted_b_sha)
    require(a["dependencies"] == {}, "aggregate:reverse_dependency")
    expected_dependencies = {
        "receipt_A_sha256": sha256(raw_a),
        "receipt_A_output_hashes": {
            output["family"]: output["sha256"] for output in a["outputs"]
        },
    }
    require(
        typed_equal(b["dependencies"], expected_dependencies),
        "aggregate:B_to_A_binding",
    )
    outputs = a["outputs"] + b["outputs"]
    require(
        len(outputs) == 8 and len({o["family"] for o in outputs}) == 8,
        "aggregate:overlap",
    )
    return yaml_bytes(
        {
            "manifest_id": "pipeline-v2.alpha0.compiled-output-manifest.v2",
            "schema_version": 1,
            "result": "pass",
            "runtime_enabled": False,
            "inputs": context.provenance(),
            "receipts": [
                {
                    "owner": a["owner"],
                    "sha256": sha256(raw_a),
                    "compiler": a["compiler"],
                },
                {
                    "owner": b["owner"],
                    "sha256": sha256(raw_b),
                    "compiler": b["compiler"],
                },
            ],
            "outputs": sorted(outputs, key=lambda output: output["family"]),
            "credit": 0,
        }
    )


def validate_event(
    context: InputContext, event_type: str, envelope: dict[str, Any]
) -> None:
    matches = [e for e in context.registry["events"] if e["event_type"] == event_type]
    require(len(matches) == 1, "event:unknown_type")
    validate(envelope, context.schemas[matches[0]["schema"]["id"]])
    if envelope.get("profile") == "Alpha0":
        row = matches[0]
        require(
            envelope["schema_sha256"] == row["schema"]["sha256"],
            "event:stale_schema_hash",
        )
        payload = envelope["payload"]
        require(
            "run_id" not in payload or payload["run_id"] == envelope["run_id"],
            "event:run_identity",
        )
        require(
            envelope["artifact_version_id"] == payload.get("artifact_version_id", ""),
            "event:artifact_identity",
        )
        parts = [
            "v1"
            if field == "v1"
            else envelope["run_id"]
            if field == "run_id"
            else payload[field]
            for field in row["idempotency_fields"]
        ]
        require(
            envelope["idempotency_key"] == sha256(json_bytes(parts)),
            "event:exact_idempotency_key",
        )


def barrier(rule: dict[str, Any], results: list[dict[str, str]]) -> bool:
    require(
        rule["barrier"] == "all_required"
        and rule["dynamic_membership"] is False
        and rule["peer_visibility_before_barrier"] is False,
        "barrier:policy",
    )
    seen: dict[str, dict[str, str]] = {}
    for result in results:
        require(
            set(result) == {"member", "result_id", "sha256", "terminal"}
            and result["member"] in rule["members"]
            and result["terminal"] == "valid_terminal",
            "barrier:result",
        )
        require(
            isinstance(result["result_id"], str)
            and result["result_id"]
            and isinstance(result["sha256"], str)
            and re.fullmatch("[0-9a-f]{64}", result["sha256"]),
            "barrier:result_identity",
        )
        require(
            not any(
                other["result_id"] == result["result_id"] and member != result["member"]
                for member, other in seen.items()
            ),
            "barrier:cross_member_duplicate",
        )
        if result["member"] in seen:
            require(
                typed_equal(seen[result["member"]], result),
                "barrier:conflicting_duplicate",
            )
        seen[result["member"]] = result
    return set(seen) == set(rule["members"])


def revision_owner(rule: dict[str, Any], proposal: dict[str, str]) -> str:
    require(
        set(proposal)
        == {
            "revision_owner_zero_role_id",
            "producer_invocation_id",
            "producer_role_id",
        },
        "revision:fields",
    )
    owner = rule["revision_owner_zero_role_id"]
    require(
        proposal["revision_owner_zero_role_id"] == owner
        and proposal["producer_invocation_id"]
        and proposal["producer_role_id"]
        and proposal["producer_role_id"] != owner
        and proposal["producer_invocation_id"] != owner,
        "revision:owner_lineage",
    )
    require(
        rule["producer_invocation_is_lineage_only"] is True
        and rule["owner_must_differ_from_producer_identity"] is True,
        "revision:policy",
    )
    return owner


def static_route(registry: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Validate a compiled selection; never dispatch an actor or emit an event."""
    closed(
        proposal,
        {
            "route_id",
            "phase_id",
            "partition_digest",
            "accepted_partition_digest",
            "direct_actor_handoff",
            "revision_proposal",
        },
        "route_selection",
    )
    matches = [
        route
        for route in registry["routes"]
        if route["route_id"] == proposal["route_id"]
    ]
    require(
        len(matches) == 1
        and proposal["phase_id"] in registry["phase_fences"]["phase_order"],
        "route_selection:identity",
    )
    require(
        isinstance(proposal["partition_digest"], str)
        and re.fullmatch("[0-9a-f]{64}", proposal["partition_digest"])
        and proposal["partition_digest"] == proposal["accepted_partition_digest"]
        and proposal["direct_actor_handoff"] is False,
        "route_selection:guards",
    )
    route = matches[0]
    if route["class"] == "revision":
        revision_owner(registry["F05_rule"], proposal["revision_proposal"])
    else:
        require(proposal["revision_proposal"] is None, "route_selection:extra_revision")
    return copy.deepcopy(route)
