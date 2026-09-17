from __future__ import annotations

import copy
import re
from typing import Any

from .binary_budget import ceiling, integer, stress_checkpoint, validate_definition
from .canonical import json_bytes, require, sha256
from .contract import InputContext, typed_equal
from .registry_compiler import closed, receipt, validate_receipt


def zero_credit(value: Any) -> None:
    require(
        isinstance(value, dict)
        and value
        and all(type(v) is int and v == 0 for v in value.values()),
        "budget:credit",
    )


def pair(value: Any, code: str) -> tuple[int, int]:
    require(
        isinstance(value, dict) and set(value) == {"nominal", "worst_case"},
        code + ":fields",
    )
    nominal = integer(value["nominal"], code + ":nominal")
    worst = integer(value["worst_case"], code + ":worst")
    require(nominal <= worst, code + ":order")
    return nominal, worst


def human_attention(value: Any, policy: dict[str, Any]) -> dict[str, Any]:
    closed(
        value,
        {
            "profile",
            "sessions",
            "blocking_decisions",
            "active_minutes",
            "max_single_session_minutes",
            "batchable_requests",
        },
        "human",
    )
    require(value["profile"] in policy["human_profiles"], "human:profile")
    for key in ("sessions", "blocking_decisions", "active_minutes"):
        pair(value[key], "human:" + key)
    require(
        integer(value["max_single_session_minutes"], "human:max_session") > 0
        and type(value["batchable_requests"]) is bool,
        "human:session_batch",
    )
    return copy.deepcopy(value)


def package_calls(package: dict[str, Any], policy: dict[str, Any]) -> tuple[int, int]:
    closed(
        package,
        {
            "package_id",
            "invocation_profile",
            "graph_kind",
            "nodes",
            "edges",
            "fanout_members",
            "retry_bounds_complete",
            "dialogue",
            "fallback",
            "human_attention",
            "forecast_authority",
            "deep_authority",
            "capacity",
            "purpose",
        },
        "package",
    )
    require(
        isinstance(package["package_id"], str)
        and package["package_id"]
        and package["purpose"] == "forecast_only",
        "package:identity_purpose",
    )
    require(
        package["graph_kind"] in policy["graph_kinds"]
        and package["retry_bounds_complete"] is True,
        "package:completeness",
    )
    nodes = package["nodes"]
    require(
        isinstance(nodes, list)
        and nodes
        and len({n["node_id"] for n in nodes}) == len(nodes),
        "graph:nodes",
    )
    totals = [0, 0]
    identifiers = {n["node_id"] for n in nodes}
    for node in nodes:
        closed(
            node,
            {
                "node_id",
                "call_class",
                "nominal_instances",
                "worst_instances",
                "nominal_calls_per_instance",
                "worst_calls_per_instance",
                "nominal_attempts",
                "worst_attempts",
                "bounded_zero_proof",
                "provenance",
            },
            "node",
        )
        require(
            node["call_class"] in policy["call_classes"]
            and isinstance(node["provenance"], dict)
            and node["provenance"],
            "node:class_provenance",
        )
        counts = []
        for mode in ("nominal", "worst"):
            values = [
                integer(node[mode + suffix], "node:" + mode + suffix)
                for suffix in ("_instances", "_calls_per_instance", "_attempts")
            ]
            if 0 in values:
                require(
                    isinstance(node["bounded_zero_proof"], str)
                    and node["bounded_zero_proof"],
                    "node:missing_zero_proof",
                )
            counts.append(values[0] * values[1] * values[2])
        require(counts[0] <= counts[1], "node:count_order")
        if node["call_class"] == "compiled_fast_path":
            require(counts == [0, 0], "node:hidden_fast_path_call")
        for index in (0, 1):
            totals[index] += counts[index]
    edges = package["edges"]
    require(
        isinstance(edges, list)
        and all(
            isinstance(e, list)
            and len(e) == 2
            and set(e) <= identifiers
            and e[0] != e[1]
            for e in edges
        )
        and len({tuple(e) for e in edges}) == len(edges),
        "graph:edges",
    )
    remaining = set(identifiers)
    while remaining:
        ready = {
            n
            for n in remaining
            if not any(target == n and source in remaining for source, target in edges)
        }
        require(bool(ready), "graph:cycle")
        remaining -= ready
    require(
        isinstance(package["fanout_members"], list)
        and len(package["fanout_members"]) == len(set(package["fanout_members"])),
        "graph:fanout",
    )
    dialogue = package["dialogue"]
    closed(
        dialogue,
        {
            "applicable",
            "topics",
            "sessions",
            "rounds_per_topic",
            "role_instances",
            "bounded_zero_proof",
        },
        "dialogue",
    )
    require(type(dialogue["applicable"]) is bool, "dialogue:applicability")
    factors = [
        integer(dialogue[k], "dialogue:" + k)
        for k in ("topics", "sessions", "rounds_per_topic", "role_instances")
    ]
    if dialogue["applicable"]:
        require(
            all(factors)
            and all(
                dialogue[k] <= policy["dialogue_limits"][k]
                for k in policy["dialogue_limits"]
            ),
            "dialogue:bounds",
        )
        require(
            not any(n["call_class"] == "dialogue_role" for n in nodes),
            "dialogue:double_count",
        )
        contribution = factors[0] * factors[1] * factors[2] * factors[3]
        totals = [v + contribution for v in totals]
    else:
        require(
            factors == [0, 0, 0, 0]
            and isinstance(dialogue["bounded_zero_proof"], str)
            and dialogue["bounded_zero_proof"],
            "dialogue:false_NA",
        )
    fallback = package["fallback"]
    closed(fallback, {"additional_calls", "bounded_zero_proof"}, "fallback")
    require(
        type(fallback["additional_calls"]) is int
        and fallback["additional_calls"] == 0
        and isinstance(fallback["bounded_zero_proof"], str)
        and fallback["bounded_zero_proof"],
        "fallback:unbounded_or_hidden",
    )
    profile = package["invocation_profile"]
    require(profile in policy["invocation_tiers"], "package:unknown_tier")
    tier = policy["invocation_tiers"][profile]
    if tier["nominal_max"] is None:
        authority = package["deep_authority"]
        require(
            isinstance(authority, dict)
            and authority.get("path")
            and authority.get("sha256")
            and authority.get("purpose") == "exact_static_forecast_not_run_authority",
            "package:deep_authority",
        )
        require(
            totals[0] <= integer(authority.get("nominal_bound"), "deep:nominal_bound")
            and totals[1] <= integer(authority.get("worst_bound"), "deep:worst_bound"),
            "package:deep_bound",
        )
    else:
        require(
            totals[0] <= tier["nominal_max"] and totals[1] <= tier["worst_max"],
            "package:tier_exceeded",
        )
    closed(package["capacity"], {"state", "runtime_authorized"}, "capacity")
    require(
        package["capacity"]["state"] == "future_separate_capacity_receipt_required"
        and package["capacity"]["runtime_authorized"] is False,
        "capacity:runtime_claim",
    )
    human_attention(package["human_attention"], policy)
    return totals[0], totals[1]


def calculate_packages(
    packages: list[dict[str, Any]], policy: dict[str, Any], envelope: str
) -> dict[str, Any]:
    require(
        isinstance(packages, list)
        and packages
        and len({p["package_id"] for p in packages}) == len(packages),
        "packages:duplicate_or_missing",
    )
    require(envelope in policy["human_profiles"], "human:missing_envelope")
    totals = {
        "nominal": 0,
        "worst_case": 0,
        "checkpointed_nominal": 0,
        "checkpointed_worst_case": 0,
    }
    human = {
        metric + "_" + mode: 0
        for metric in ("sessions", "blocking_decisions", "active_minutes")
        for mode in ("nominal", "worst_case")
    }
    for package in packages:
        nominal, worst = package_calls(package, policy)
        totals["nominal"] += nominal
        totals["worst_case"] += worst
        if not all(
            n["call_class"] == "plan_author_review_allocation" for n in package["nodes"]
        ):
            totals["checkpointed_nominal"] += nominal
            totals["checkpointed_worst_case"] += worst
        attention = human_attention(package["human_attention"], policy)
        require(
            policy["human_profiles"].index(envelope)
            >= policy["human_profiles"].index(attention["profile"]),
            "human:underclassified_envelope",
        )
        for metric in ("sessions", "blocking_decisions", "active_minutes"):
            for mode in ("nominal", "worst_case"):
                human[metric + "_" + mode] += attention[metric][mode]
    return {"invocations": totals, "human_attention": human, "human_profile": envelope}


def checkpoint(case: dict[str, Any], policy: dict[str, Any]) -> dict[str, int]:
    closed(
        case,
        {
            "case_id",
            "kind",
            "checkpoint_phase_id",
            "mode",
            "components_bytes",
            "window",
            "triggers",
            "publisher_available",
            "planning_pack_factor",
            "credit",
            "authority",
        },
        "checkpoint",
    )
    zero_credit(case["credit"])
    require(
        type(case["publisher_available"]) is bool
        and type(case["planning_pack_factor"]) is int
        and case["planning_pack_factor"] == policy["planning_pack_factor"],
        "checkpoint:publisher_factor",
    )
    components = case["components_bytes"]
    require(
        isinstance(components, dict) and components, "checkpoint:missing_components"
    )
    rounded = (
        ceiling(
            sum(integer(v, "checkpoint:component") for v in components.values()),
            1048576,
        )
        * 1048576
    )
    closed(
        case["window"], {"total_points", "publisher_minutes", "new_db_bytes"}, "window"
    )
    window = (
        max(
            ceiling(
                integer(case["window"][key], "window:" + key),
                policy["window_divisors"][divisor],
            )
            for key, divisor in (
                ("total_points", "points"),
                ("publisher_minutes", "minutes"),
                ("new_db_bytes", "db_bytes"),
            )
        )
        if case["publisher_available"]
        else 0
    )
    require(isinstance(case["triggers"], dict), "checkpoint:triggers")
    publications = (
        window
        + sum(integer(v, "checkpoint:trigger") for v in case["triggers"].values())
        if case["publisher_available"]
        else 0
    )
    require(
        case["publisher_available"] or case["triggers"] == {},
        "checkpoint:unavailable_publisher_trigger",
    )
    return {
        "checkpoint_bytes": rounded,
        "publications": publications,
        "phase_pack_bytes": rounded * publications,
        "window_publications": window,
        "batches": ceiling(publications, policy["thresholds"]["publication_batch_cap"]),
    }


def review_overlay(inputs: dict[str, Any]) -> dict[str, Any]:
    counts = [
        integer(inputs[k], "overlay:" + k)
        for k in (
            "design_nominal",
            "design_effective_worst",
            "operational_nominal",
            "operational_worst",
            "F15_exact",
            "review_nominal",
            "review_worst",
        )
    ]
    result: dict[str, Any] = {
        "invocations_nominal": counts[0] + counts[2] + counts[4] + counts[5],
        "invocations_worst": counts[1] + counts[3] + counts[4] + counts[6],
    }
    for key in ("sessions", "blocking_decisions", "active_minutes"):
        for index, mode in enumerate(("nominal", "worst")):
            result[key + "_" + mode] = integer(
                inputs["human_baseline"][key][index], "overlay:human_baseline"
            ) + integer(inputs["human_review"][key][index], "overlay:human_review")
    result["max_single_session_minutes"] = integer(
        inputs["human_review"]["max_single_session_minutes"], "overlay:max_session"
    )
    result["human_profile"] = "high_attention"
    return result


def resolve(document: Any, field_path: str) -> Any:
    require(isinstance(field_path, str) and field_path, "provenance:field_path")
    for part in field_path.split("."):
        if isinstance(document, list):
            require(part.isdigit() and int(part) < len(document), "provenance:index")
            document = document[int(part)]
        else:
            require(
                isinstance(document, dict) and part in document,
                "provenance:missing_field",
            )
            document = document[part]
    return document


def validate_provenance(
    context: InputContext, value: dict[str, Any], field_keys: tuple[str, ...]
) -> None:
    require(
        value.get("path") in context.pins
        and value.get("path") not in context.hash_only
        and value.get("sha256") == context.pins[value["path"]]["sha256"],
        "provenance:stale_or_forbidden",
    )
    document = (
        context.json(value["path"])
        if value["path"].endswith(".json")
        else context.yaml(value["path"])
    )
    for key in field_keys:
        field_paths = value[key] if isinstance(value[key], list) else [value[key]]
        for field_path in field_paths:
            resolve(document, field_path)


def phase_partition(policy: dict[str, Any], fences: dict[str, Any]) -> dict[str, Any]:
    order = fences["phase_order"]
    require(
        len(order) == 2 and set(policy["phase_members"]) == set(order),
        "partition:phase_set",
    )
    members = []
    for phase in order:
        group = policy["phase_members"][phase]
        require(
            isinstance(group, list) and group and len(group) == len(set(group)),
            "partition:group",
        )
        members.extend(group)
    require(
        len(members) == len(set(members))
        and set(members) == set(policy["phase_call_allocations"]),
        "partition:gap_overlap",
    )
    calls = []
    for phase in order:
        counts = [0, 0]
        for member in policy["phase_members"][phase]:
            value = policy["phase_call_allocations"][member]
            require(
                isinstance(value, list)
                and len(value) == 2
                and all(type(v) is int and v >= 0 for v in value),
                "partition:call_types",
            )
            counts = [counts[i] + value[i] for i in (0, 1)]
        calls.append(counts)
    require(
        calls[1] == [policy["F15_exact_calls"], policy["F15_exact_calls"]]
        and policy["separate_K0b05_run"] is False
        and fences["post_F15_model_calls"] == 0,
        "partition:F15",
    )
    core = {
        "phase_order": order,
        "members": [
            {
                "checkpoint_phase_id": p,
                "member_ids": policy["phase_members"][p],
                "model_call_budget": calls[i],
                "starts_only_after_verified_predecessor_seal": i > 0,
                "runtime_enabled": False,
            }
            for i, p in enumerate(order)
        ],
        "F15_boundary_triggers": fences["F15_boundary_triggers"],
        "exact_trigger_count": 4,
        "phase_reopen_reorder_relabel_or_third_phase": "forbidden",
        "runtime_enabled": False,
    }
    require(
        len(core["F15_boundary_triggers"])
        == len(set(core["F15_boundary_triggers"]))
        == 4,
        "partition:trigger_set",
    )
    return {
        **core,
        "partition_digest": sha256(json_bytes(core)),
        "partition_digest_profile": "canonical_core_without_digest_or_digest_profile",
    }


def phase_guard(
    partition: dict[str, Any], request: dict[str, Any], policy: dict[str, Any]
) -> None:
    closed(
        request,
        {
            "phase_id",
            "partition_digest",
            "member_id",
            "predecessor_seal_digest",
            "predecessor_seal",
            "operational_sealed",
            "F15_terminal",
            "non_F15_call",
            "model_calls",
            "boundary_triggers",
            "publications",
            "batch_publications",
            "separate_K0b05_run",
            "reopen",
            "publication_p95_seconds",
            "restore_seconds",
            "checkpoint_bytes",
            "projected_phase_pack_bytes",
        },
        "phase_request",
    )
    require(
        request["partition_digest"] == partition["partition_digest"]
        and request["phase_id"] in partition["phase_order"]
        and request["reopen"] is False,
        "phase:identity",
    )
    group = next(
        p
        for p in partition["members"]
        if p["checkpoint_phase_id"] == request["phase_id"]
    )
    require(
        request["member_id"] in group["member_ids"]
        and request["separate_K0b05_run"] is False,
        "phase:membership",
    )
    for key in ("operational_sealed", "F15_terminal", "non_F15_call"):
        require(type(request[key]) is bool, "phase:boolean")
    calls = integer(request["model_calls"], "phase:model_calls")
    publications = integer(request["publications"], "phase:publications")
    require(
        integer(request["batch_publications"], "phase:batch_publications")
        <= policy["thresholds"]["publication_batch_cap"],
        "phase:batch_cap",
    )
    require(
        integer(request["publication_p95_seconds"], "phase:p95")
        < policy["thresholds"]["publication_p95_seconds"]
        and integer(request["restore_seconds"], "phase:restore")
        < policy["thresholds"]["restore_seconds"],
        "phase:timing",
    )
    require(
        integer(request["checkpoint_bytes"], "phase:checkpoint_bytes")
        < policy["thresholds"]["checkpoint_hard_bytes"]
        and integer(request["projected_phase_pack_bytes"], "phase:pack_bytes")
        < policy["thresholds"]["phase_pack_hard_bytes"],
        "phase:hard_stop_before_effect",
    )
    require(
        request["projected_phase_pack_bytes"]
        >= request["checkpoint_bytes"] * publications,
        "phase:invented_pack_credit",
    )
    allocation = policy["phase_call_allocations"][request["member_id"]]
    require(calls <= allocation[1], "phase:member_call_allocation")
    if group["starts_only_after_verified_predecessor_seal"]:
        seal = request["predecessor_seal"]
        closed(
            seal,
            {
                "partition_digest",
                "phase_id",
                "result",
                "all_non_F15_terminal",
                "outbox_reconciled",
                "terminal_checkpoint_verified",
                "seal_committed",
                "checkpoint_bytes",
                "projected_phase_pack_bytes",
            },
            "predecessor_seal",
        )
        require(
            request["operational_sealed"] is True
            and request["predecessor_seal_digest"] == sha256(json_bytes(seal))
            and seal["partition_digest"] == partition["partition_digest"]
            and seal["phase_id"] == partition["phase_order"][0]
            and seal["result"] == "pass"
            and all(
                seal[k] is True
                for k in (
                    "all_non_F15_terminal",
                    "outbox_reconciled",
                    "terminal_checkpoint_verified",
                    "seal_committed",
                )
            ),
            "phase:verified_predecessor_seal",
        )
        require(
            integer(seal["checkpoint_bytes"], "seal:checkpoint_bytes")
            < policy["thresholds"]["checkpoint_hard_bytes"]
            and integer(seal["projected_phase_pack_bytes"], "seal:pack_bytes")
            < policy["thresholds"]["phase_pack_hard_bytes"],
            "phase:over_limit_seal_never_admits_successor",
        )
        require(request["non_F15_call"] is False, "phase:non_F15_after_entry")
        if allocation[1] == policy["F15_exact_calls"]:
            require(
                not request["F15_terminal"] and calls == policy["F15_exact_calls"],
                "phase:F15_exact_matrix",
            )
        else:
            require(
                request["F15_terminal"] is True and calls == 0,
                "phase:post_F15_deterministic_only",
            )
        require(
            request["boundary_triggers"] == partition["F15_boundary_triggers"],
            "phase:fifth_or_duplicate_trigger",
        )
        require(
            publications < policy["F15"]["unconditional_block_from_publications"],
            "phase:F15_publication_hard",
        )
        require(
            publications <= policy["F15"]["requires_reforecast_above"],
            "phase:reforecast_required",
        )
    else:
        require(
            request["operational_sealed"] is False
            and calls <= group["model_call_budget"][1]
            and not request["F15_terminal"]
            and request["predecessor_seal"] is None
            and request["predecessor_seal_digest"] is None,
            "phase:post_seal_call",
        )


def compile_budget(context: InputContext, raw_a: bytes, accepted_a_sha: str) -> bytes:
    a = validate_receipt(raw_a, context, "registry_and_routing", accepted_a_sha)
    require(a["dependencies"] == {}, "budget:reverse_dependency")
    policy_paths = [
        p["path"]
        for p in context.source_pins
        if p["path"].endswith("/k0b01-policy-v2.json")
    ]
    reference_paths = [
        p["path"]
        for p in context.source_pins
        if p["path"].endswith("/k0b01-reference-inputs-v2.json")
    ]
    require(len(policy_paths) == len(reference_paths) == 1, "budget:source_identity")
    policy = context.json(policy_paths[0])
    inputs = context.json(reference_paths[0])
    require(
        type(policy["schema_version"]) is int
        and policy["schema_version"] == 1
        and policy["runtime_enabled"] is False,
        "policy:version_fence",
    )
    closed(
        policy,
        {
            "policy_id",
            "schema_version",
            "version",
            "purpose",
            "runtime_enabled",
            "credit",
            "base_policy",
            "current_binary_definition",
            "binary_NA_definitions",
            "bounded_zero_proof_required",
            "dialogue_limits",
            "call_classes",
            "graph_kinds",
            "human_profiles",
            "invocation_tiers",
            "normative_provenance",
            "phase_call_allocations",
            "phase_fences_locator",
            "phase_members",
            "phase_overlay",
            "planning_pack_factor",
            "runtime_publications",
            "separate_K0b05_run",
            "thresholds",
            "window_divisors",
            "F15",
            "F15_exact_calls",
        },
        "policy",
    )
    require(
        policy["bounded_zero_proof_required"] is True,
        "policy:missing_as_zero_forbidden",
    )
    closed(
        inputs,
        {
            "reference_id",
            "schema_version",
            "version",
            "purpose",
            "cases",
            "current_stress_inputs",
            "normative_provenance",
            "review_overlay",
            "F15_authoritative_worst_case_object_count",
        },
        "reference",
    )
    require(
        type(inputs["schema_version"]) is int
        and inputs["schema_version"] == 1
        and inputs["purpose"]
        == "input_graphs_only_no_expected_output_or_oracle_dependency"
        and policy["purpose"] == "static_forecast_only_not_runtime_authority",
        "budget:purpose",
    )
    zero_credit(policy["credit"])
    base = context.yaml(policy["base_policy"]["path"])
    require(
        policy["base_policy"]["sha256"]
        == context.pins[policy["base_policy"]["path"]]["sha256"]
        and policy["thresholds"]["checkpoint_hard_bytes"]
        == base["thresholds"]["max_checkpoint_bytes"]
        and policy["thresholds"]["phase_pack_hard_bytes"]
        == base["thresholds"]["max_projected_pack_growth_per_phase"]
        and policy["thresholds"]["publication_batch_cap"]
        == base["thresholds"]["max_publications_per_run"],
        "policy:threshold_change",
    )
    require(
        policy["thresholds"]["publication_p95_seconds"]
        == base["thresholds"]["max_publication_p95_seconds"]
        and policy["thresholds"]["restore_seconds"]
        == base["thresholds"]["max_clean_clone_restore_seconds"]
        and policy["thresholds"]["warning_bytes"]
        == base["thresholds"]["max_projected_pack_growth_per_phase"] // 2,
        "policy:timing_warning_change",
    )
    require(
        policy["window_divisors"]
        == {
            "points": base["publication_window"]["max_unpublished_replay_points"],
            "minutes": base["publication_window"]["max_unpublished_minutes"],
            "db_bytes": base["publication_window"]["max_unpublished_db_bytes"],
        },
        "policy:window_change",
    )
    overlay = context.yaml(policy["phase_overlay"]["path"])
    require(
        policy["phase_overlay"]["sha256"]
        == context.pins[policy["phase_overlay"]["path"]]["sha256"]
        and context.registry["phase_fences"]["phase_order"]
        == overlay["threshold_unit_override"]["exact_order"],
        "policy:phase_overlay_binding",
    )
    operational, f15 = context.registry["phase_fences"]["phase_order"]
    operational_text = " ".join(overlay["phases"][0]["includes"])
    f15_text = " ".join(overlay["phases"][1]["includes"])
    prior_ids = {
        "K0b" + number
        for number in re.findall(
            r"K0b_([0-9]{2})", operational_text.split("all_pre_F15_")[0]
        )
    }
    milestone = re.search(r"pre_F15_K0b_([0-9]{2})", operational_text)
    closure = re.search(r"post_F15_K0b_([0-9]{2})", f15_text)
    disposition = re.search(r"deterministic_K0b_([0-9]{2})", f15_text)
    require(
        milestone is not None
        and closure is not None
        and disposition is not None
        and milestone.group(1) == closure.group(1),
        "policy:milestone_authority_parse",
    )
    expected_operational = prior_ids | {"K0b" + milestone.group(1) + "_pre_F15"}
    expected_f15 = {
        "K0b" + closure.group(1) + "_F15",
        "K0b" + closure.group(1) + "_post_F15",
        "K0b" + disposition.group(1),
    }
    require(
        set(policy["phase_members"][operational]) == expected_operational
        and set(policy["phase_members"][f15]) == expected_f15,
        "policy:immutable_milestone_membership",
    )
    for source in policy["normative_provenance"]:
        validate_provenance(context, source, ("field_paths",))
    require(
        typed_equal(inputs["normative_provenance"], policy["normative_provenance"]),
        "budget:provenance_binding",
    )
    request_paths = [
        p
        for p in context.pins
        if p.endswith(
            "/k0b-01-final-implementation-disposition-and-bounded-implementation-approval-request-v1.yaml"
        )
    ]
    require(len(request_paths) == 1, "budget:approval_identity")
    approved = context.yaml(request_paths[0])["phase_B_contract"]["budget_inputs"]
    for key in (
        "assumed_mean_object_bytes",
        "nominal_object_count",
        "worst_case_object_count",
        "hard_per_object_bytes",
        "non_binary_worst_bytes",
    ):
        require(
            type(inputs["current_stress_inputs"][key]) is int
            and inputs["current_stress_inputs"][key] == approved[key],
            "budget:changed_exact_input",
        )
    require(
        inputs["current_stress_inputs"]["publications"]
        == approved["runtime_phase_publications"],
        "budget:publication_recalculation_required",
    )
    results = []
    require(
        isinstance(inputs["cases"], list)
        and len({c["case_id"] for c in inputs["cases"]}) == len(inputs["cases"]),
        "reference:duplicate_case",
    )
    for case in sorted(inputs["cases"], key=lambda item: item["case_id"]):
        if case["kind"] == "packages":
            closed(
                case,
                {"case_id", "kind", "packages", "credit", "human_envelope_profile"},
                "reference:packages",
            )
            zero_credit(case["credit"])
            for package in case["packages"]:
                validate_provenance(context, package["forecast_authority"], ())
                for node in package["nodes"]:
                    validate_provenance(context, node["provenance"], ("field_path",))
                    if (
                        package["graph_kind"]
                        == "complete_authoritative_allocation_graph"
                    ):
                        source = (
                            context.json(node["provenance"]["path"])
                            if node["provenance"]["path"].endswith(".json")
                            else context.yaml(node["provenance"]["path"])
                        )
                        bounds = resolve(source, node["provenance"]["field_path"])
                        require(
                            isinstance(bounds, dict)
                            and node["nominal_instances"]
                            * node["nominal_calls_per_instance"]
                            * node["nominal_attempts"]
                            == bounds["nominal"]
                            and node["worst_instances"]
                            * node["worst_calls_per_instance"]
                            * node["worst_attempts"]
                            == bounds["worst_case"],
                            "node:authoritative_allocation_equivalence",
                        )
            result = calculate_packages(
                case["packages"], policy, case["human_envelope_profile"]
            )
        elif case["kind"] == "checkpoint":
            validate_provenance(context, case["authority"], ("field_path",))
            result = checkpoint(case, policy)
        elif case["kind"] == "binary":
            closed(case, {"case_id", "kind", "definition"}, "reference:binary")
            for source in case["definition"]["forecast_provenance"]:
                validate_provenance(context, source, ("field_paths",))
            result = validate_definition(case["definition"])
        else:
            require(False, "reference:unknown_kind")
        results.append({"case_id": case["case_id"], "result": result})
    stress = stress_checkpoint(inputs["current_stress_inputs"], policy["thresholds"])
    require(
        stress["checkpoint_result"] == "below_hard"
        and stress["phase_result"] != "above_hard",
        "budget:current_size_stress_hard",
    )
    require(
        policy["runtime_publications"]["reforecast_sensitive"] is True
        and stress["publications"] == policy["runtime_publications"]["approved_exact"],
        "budget:publication_reforecast",
    )
    require(
        inputs["F15_authoritative_worst_case_object_count"] is None
        and policy["F15"]["authoritative_worst_case_object_count"] is None
        and policy["F15"]["size_stress_completion_claim"] is False,
        "budget:invented_F15_count",
    )
    binary = validate_definition(policy["current_binary_definition"])
    require(
        binary["size_stressed_bytes"] == stress["size_stressed_bytes"],
        "budget:binary_stress_binding",
    )
    partition = phase_partition(policy, context.registry["phase_fences"])
    payloads = [
        {
            "reference_results": results,
            "review_overlay": review_overlay(inputs["review_overlay"]),
            "binary_budget": binary,
            "current_size_stress": stress,
            "human_package_profiles": [
                {
                    "case_id": case["case_id"],
                    "packages": [
                        {
                            "package_id": p["package_id"],
                            "human_attention": p["human_attention"],
                            "capacity": p["capacity"],
                        }
                        for p in case["packages"]
                    ],
                }
                for case in inputs["cases"]
                if case["kind"] == "packages"
            ],
            "F15_size_stress": "blocked_missing_authoritative_object_count",
            "phase_completion_claim": False,
            "runtime_enabled": False,
        },
        partition,
        {
            "thresholds": policy["thresholds"],
            "credit": policy["credit"],
            "historical_checkpoint_vectors": [
                r for r in results if "checkpoint_bytes" in r["result"]
            ],
            "current_size_stressed_checkpoint_and_phase": stress,
            "F15": policy["F15"],
            "runtime_publications_reforecast_sensitive": policy["runtime_publications"],
            "planning_pack_factor": policy["planning_pack_factor"],
            "runtime_enabled": False,
            "phase_completion_claim": False,
        },
    ]
    dependencies = {
        "receipt_A_sha256": sha256(raw_a),
        "receipt_A_output_hashes": {o["family"]: o["sha256"] for o in a["outputs"]},
    }
    return receipt(
        context, "resource_and_budget", payloads, "budget_compiler.py", dependencies
    )
