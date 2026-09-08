"""Deterministic resource and binary-budget compiler for K0b-01."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contract import CHECKPOINT_PHASE_ORDER, F15_TRIGGER_IDS, canonical_json


class BudgetError(RuntimeError):
    """A resource-budget input or derived value is invalid."""


class IncompleteGraph(BudgetError):
    """A route, fan-out, retry, or dialogue graph fact is absent or unknown."""


class BudgetLimitExceeded(BudgetError):
    """A declared or derived hard limit is met or exceeded."""


class BinaryPayloadBudgetError(BudgetError):
    """A binary budget is incomplete, false-N/A, stale, or over limit."""


class ReferenceMismatch(BudgetError):
    """Compiled fields differ from a versioned independent reference result."""


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise BudgetError(
            f"{label} keys must be exactly {sorted(expected)!r}, got {actual!r}"
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BudgetError(f"{label} must be non-empty trimmed text")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BudgetError(f"{label} must be a non-negative integer")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise BudgetError(f"{label} must be boolean")
    return value


def _pair(value: Any, label: str) -> tuple[int, int]:
    pair = _exact_keys(value, {"nominal", "worst_case"}, label)
    nominal = _integer(pair["nominal"], f"{label}.nominal")
    worst = _integer(pair["worst_case"], f"{label}.worst_case")
    if worst < nominal:
        raise BudgetError(f"{label}.worst_case cannot be below nominal")
    return nominal, worst


def _ceil_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise BudgetError("division denominator must be positive")
    return (numerator + denominator - 1) // denominator


def _round_up(value: int, quantum: int) -> int:
    return _ceil_div(value, quantum) * quantum


def _status(value: int, warning: int, hard: int) -> str:
    if value >= hard:
        return "above_hard"
    if value >= warning:
        return "above_warning"
    return "below_warning"


@dataclass(frozen=True)
class CompiledReference:
    case_id: str
    result: Mapping[str, Any]


def validate_policy(policy: Mapping[str, Any]) -> None:
    top = _exact_keys(
        policy,
        {
            "policy_id",
            "version",
            "compiler_id",
            "compiler_version",
            "authority",
            "required_graph_sections",
            "call_classes",
            "invocation_tiers",
            "human_attention_required_fields",
            "human_attention_tiers",
            "binary_payload_required_fields",
            "binary_not_applicable_required_fields",
            "checkpoint",
            "k0b_checkpoint_phase_order",
            "k0b_work_item_membership",
            "k0b_call_allocation",
            "f15_boundary_trigger_ids",
            "f15_publication_limits",
            "forbidden",
        },
        "resource policy",
    )
    if (
        top["policy_id"] != "pipeline-v2.resource-budget-policy"
        or top["version"] != "1.0.0"
    ):
        raise BudgetError("resource policy identity differs")
    if (
        top["compiler_id"] != "pipeline-v2.k0b01.resource-budget-compiler"
        or top["compiler_version"] != "1.0.0"
    ):
        raise BudgetError("resource compiler identity differs")
    if top["authority"] != {
        "d0_gate_sha256": "1bf92c755912a95ecf46e691454512f22a48fe97b59a5f7a676ac07e054478c4",
        "d0_forecast_sha256": "7e8a8da36c982b21bc25e1bbd1b1dd495f36f92446e7afbef4c6ce8cc8683840",
        "base_checkpoint_policy_sha256": "8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3",
        "k0b_phase_policy_sha256": "ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8",
        "k0b_forecast_sha256": "ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a",
        "k0b_reconciliation_sha256": "d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb",
    }:
        raise BudgetError("resource policy authority hashes differ")
    if tuple(top["required_graph_sections"]) != (
        "route",
        "fanout",
        "retry",
        "dialogue",
    ):
        raise BudgetError("required graph sections differ")
    if top["call_classes"] != {
        "deterministic": {"counts_as_model_call": False},
        "model": {"counts_as_model_call": True},
    }:
        raise BudgetError("call-class policy differs")
    if top["invocation_tiers"] != {
        "light": {"nominal_max": 12, "worst_case_max": 20},
        "standard": {"nominal_max": 30, "worst_case_max": 50},
        "deep": {
            "nominal_max": None,
            "worst_case_max": None,
            "exact_counts_and_owner_authority_required": True,
        },
    }:
        raise BudgetError("invocation-tier policy differs")
    if tuple(top["human_attention_required_fields"]) != (
        "profile",
        "sessions_nominal",
        "sessions_worst_case",
        "blocking_decisions_nominal",
        "blocking_decisions_worst_case",
        "active_minutes_nominal",
        "active_minutes_worst_case",
        "max_single_session_minutes",
        "batchable_requests",
    ):
        raise BudgetError("human-attention field vocabulary differs")
    if top["human_attention_tiers"] != {
        "light": {
            "sessions_max": 1,
            "blocking_decisions_max": 2,
            "active_minutes_max": 30,
            "max_single_session_minutes": 30,
        },
        "standard": {
            "sessions_max": 3,
            "blocking_decisions_max": 6,
            "active_minutes_max": 120,
            "max_single_session_minutes": 60,
        },
        "high_attention": {
            "sessions_max": None,
            "blocking_decisions_max": None,
            "active_minutes_max": None,
            "max_single_session_minutes": 90,
            "owner_capacity_authority_required": True,
        },
    }:
        raise BudgetError("human-attention tier policy differs")
    if tuple(top["binary_payload_required_fields"]) != (
        "payload_classes_and_media_types",
        "nominal_object_count",
        "worst_case_object_count",
        "assumed_mean_object_bytes",
        "hard_per_object_bytes",
        "nominal_aggregate_new_bytes",
        "worst_case_aggregate_new_bytes",
        "policy_permitted_maximum_aggregate_bytes",
        "runtime_aggregate_limit_bytes",
        "checkpoint_publication_count",
        "pessimistic_pack_amplification",
        "exact_forecast_ref",
        "exact_forecast_sha256",
    ):
        raise BudgetError("binary payload field vocabulary differs")
    if tuple(top["binary_not_applicable_required_fields"]) != (
        "mode",
        "contract_prohibits_binary_persistence",
        "references_budgeted_payload_only",
        "proof_ref",
    ):
        raise BudgetError("binary N/A field vocabulary differs")
    if tuple(top["k0b_checkpoint_phase_order"]) != CHECKPOINT_PHASE_ORDER:
        raise BudgetError("K0b checkpoint phase order differs")
    if tuple(top["f15_boundary_trigger_ids"]) != F15_TRIGGER_IDS:
        raise BudgetError("F15 trigger allowlist differs")
    checkpoint = top["checkpoint"]
    expected_checkpoint = {
        "mib_bytes": 1048576,
        "max_checkpoint_bytes": 104857600,
        "phase_pack_warning_bytes": 536870912,
        "max_phase_pack_bytes": 1073741824,
        "publication_batch_cap": 12,
        "max_publication_p95_seconds": 10,
        "max_clean_clone_restore_seconds": 120,
        "window_replay_point_divisor": 10,
        "window_minutes_divisor": 5,
        "window_db_bytes_divisor": 33554432,
        "planning_delta_factor_numerator": 1,
        "planning_delta_factor_denominator": 1,
        "all_credit": 0,
    }
    if checkpoint != expected_checkpoint:
        raise BudgetError(
            "checkpoint policy changes thresholds, formulas, factor, or credit"
        )
    f15_limits = top["f15_publication_limits"]
    if f15_limits != {
        "forecast_worst_case": 26,
        "maximum_strictly_below_hard_at_approved_checkpoint": 29,
        "unconditional_block_at_or_above": 30,
    }:
        raise BudgetError("F15 publication limits differ")
    membership = top["k0b_work_item_membership"]
    if membership != {
        "K0b-01": "K0b-runtime-operational",
        "K0b-02": "K0b-runtime-operational",
        "K0b-03": "K0b-runtime-operational",
        "K0b-04-pre-F15": "K0b-runtime-operational",
        "K0b-04-F15": "K0b-F15-exact-measurement",
        "K0b-04-post-F15": "K0b-F15-exact-measurement",
        "K0b-05": "K0b-F15-exact-measurement",
    }:
        raise BudgetError("K0b work-item membership is incomplete or widened")
    if top["k0b_call_allocation"] != {
        "K0b-01": {"nominal": 0, "worst_case": 0},
        "K0b-02": {"nominal": 0, "worst_case": 0},
        "K0b-03": {"nominal": 0, "worst_case": 0},
        "K0b-04-pre-F15": {"nominal": 16, "worst_case": 30},
        "K0b-04-F15": {"nominal": 36, "worst_case": 36},
        "K0b-04-post-F15": {"nominal": 0, "worst_case": 0},
        "K0b-05": {"nominal": 0, "worst_case": 0},
    }:
        raise BudgetError("K0b call allocation differs")
    if tuple(top["forbidden"]) != (
        "unknown_graph_value",
        "phase_overlap",
        "phase_gap",
        "phase_reorder",
        "phase_reopen",
        "third_phase",
        "arbitrary_batch_as_phase",
        "post_operational_seal_non_F15_call",
        "post_F15_model_call",
        "fifth_F15_boundary_trigger",
        "threshold_raise",
        "storage_change",
        "credit",
    ):
        raise BudgetError("forbidden budget operation vocabulary differs")


def validate_binary_payload_budget(
    value: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise BinaryPayloadBudgetError("binary payload budget must be an object")
    mode = value.get("mode")
    owner = value.get("owner")
    _text(owner, "binary payload owner")
    if mode == "N/A":
        expected = set(policy["binary_not_applicable_required_fields"]) | {"owner"}
        try:
            entry = _exact_keys(value, expected, f"binary N/A budget for {owner}")
        except BudgetError as exc:
            raise BinaryPayloadBudgetError(str(exc)) from exc
        if (
            entry["contract_prohibits_binary_persistence"] is not True
            or entry["references_budgeted_payload_only"] is not True
        ):
            raise BinaryPayloadBudgetError(f"binary N/A proof is false for {owner}")
        _text(entry["proof_ref"], f"binary N/A proof ref for {owner}")
        return 0, 0
    if mode != "applicable":
        raise BinaryPayloadBudgetError(f"unknown binary payload mode for {owner}")
    expected = set(policy["binary_payload_required_fields"]) | {"owner", "mode"}
    try:
        entry = _exact_keys(value, expected, f"binary budget for {owner}")
    except BudgetError as exc:
        raise BinaryPayloadBudgetError(str(exc)) from exc
    classes = entry["payload_classes_and_media_types"]
    if (
        not isinstance(classes, list)
        or not classes
        or any(not isinstance(item, str) or not item for item in classes)
    ):
        raise BinaryPayloadBudgetError(f"binary classes must be non-empty for {owner}")
    numeric_names = set(policy["binary_payload_required_fields"]) - {
        "payload_classes_and_media_types",
        "exact_forecast_ref",
        "exact_forecast_sha256",
    }
    numbers: dict[str, int] = {}
    for name in numeric_names:
        try:
            numbers[name] = _integer(entry[name], f"binary budget {owner}.{name}")
        except BudgetError as exc:
            raise BinaryPayloadBudgetError(str(exc)) from exc
    _text(entry["exact_forecast_ref"], f"binary budget {owner}.exact_forecast_ref")
    forecast_hash = _text(
        entry["exact_forecast_sha256"], f"binary budget {owner}.exact_forecast_sha256"
    )
    if len(forecast_hash) != 64 or any(
        character not in "0123456789abcdef" for character in forecast_hash
    ):
        raise BinaryPayloadBudgetError(f"binary forecast hash is invalid for {owner}")
    nominal = numbers["nominal_object_count"] * numbers["assumed_mean_object_bytes"]
    worst = numbers["worst_case_object_count"] * numbers["assumed_mean_object_bytes"]
    if (
        numbers["nominal_object_count"] == 0
        or numbers["assumed_mean_object_bytes"] == 0
    ):
        raise BinaryPayloadBudgetError(f"applicable binary budget is empty for {owner}")
    if numbers["worst_case_object_count"] < numbers["nominal_object_count"]:
        raise BinaryPayloadBudgetError(
            f"binary worst-case object count is below nominal for {owner}"
        )
    if (
        nominal != numbers["nominal_aggregate_new_bytes"]
        or worst != numbers["worst_case_aggregate_new_bytes"]
    ):
        raise BinaryPayloadBudgetError(
            f"binary aggregate arithmetic differs for {owner}"
        )
    if numbers["assumed_mean_object_bytes"] > numbers["hard_per_object_bytes"]:
        raise BinaryPayloadBudgetError(
            f"binary mean exceeds per-object hard limit for {owner}"
        )
    if (
        numbers["worst_case_aggregate_new_bytes"]
        > numbers["policy_permitted_maximum_aggregate_bytes"]
    ):
        raise BinaryPayloadBudgetError(
            f"binary aggregate exceeds planning policy for {owner}"
        )
    if (
        numbers["worst_case_aggregate_new_bytes"]
        > numbers["runtime_aggregate_limit_bytes"]
    ):
        raise BinaryPayloadBudgetError(
            f"binary aggregate exceeds runtime limit for {owner}"
        )
    if numbers["pessimistic_pack_amplification"] != 1:
        raise BinaryPayloadBudgetError(f"binary pack amplification differs for {owner}")
    return numbers["nominal_aggregate_new_bytes"], numbers[
        "worst_case_aggregate_new_bytes"
    ]


def _compile_package(
    package: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[str, int, int, Mapping[str, Any]]:
    allowed = {"package_id", "invocation_profile", "call_nodes", "human_attention"}
    if package.get("invocation_profile") == "deep":
        allowed.add("deep_budget_authority")
    if "budget_escalation_authority" in package:
        allowed.add("budget_escalation_authority")
    entry = _exact_keys(package, allowed, "budget package")
    package_id = _text(entry["package_id"], "package_id")
    profile = entry["invocation_profile"]
    tiers = policy["invocation_tiers"]
    if profile not in tiers:
        raise BudgetError(f"unknown invocation profile for {package_id}")
    if profile == "deep":
        _text(entry.get("deep_budget_authority"), f"deep authority for {package_id}")
    escalation_authority = entry.get("budget_escalation_authority")
    if escalation_authority is not None:
        _text(escalation_authority, f"budget escalation authority for {package_id}")
    nodes = entry["call_nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise IncompleteGraph(f"call graph is empty for {package_id}")
    seen: set[str] = set()
    nominal = 0
    worst = 0
    for raw_node in nodes:
        node = _exact_keys(
            raw_node, {"node_id", "call_class", "nominal", "worst_case"}, "call node"
        )
        node_id = _text(node["node_id"], "call node id")
        if node_id in seen:
            raise IncompleteGraph(f"duplicate call node: {node_id}")
        seen.add(node_id)
        call_class = node["call_class"]
        if call_class not in policy["call_classes"]:
            raise IncompleteGraph(f"unknown call class: {call_class}")
        node_nominal = _integer(node["nominal"], f"{node_id}.nominal")
        node_worst = _integer(node["worst_case"], f"{node_id}.worst_case")
        if node_worst < node_nominal:
            raise BudgetError(f"{node_id} worst-case calls are below nominal")
        counts = policy["call_classes"][call_class]["counts_as_model_call"]
        if not counts and (node_nominal != 0 or node_worst != 0):
            raise BudgetError(f"deterministic node {node_id} cannot hide a model call")
        if counts:
            nominal += node_nominal
            worst += node_worst
    tier = tiers[profile]
    if (
        tier["nominal_max"] is not None
        and nominal > tier["nominal_max"]
        and escalation_authority is None
    ):
        raise BudgetLimitExceeded(f"{package_id} exceeds nominal {profile} call cap")
    if (
        tier["worst_case_max"] is not None
        and worst > tier["worst_case_max"]
        and escalation_authority is None
    ):
        raise BudgetLimitExceeded(f"{package_id} exceeds worst-case {profile} call cap")
    human = _exact_keys(
        entry["human_attention"],
        set(policy["human_attention_required_fields"]),
        f"human attention for {package_id}",
    )
    human_profile = human["profile"]
    if human_profile not in policy["human_attention_tiers"]:
        raise BudgetError(f"unknown human-attention profile for {package_id}")
    for name in set(policy["human_attention_required_fields"]) - {
        "profile",
        "batchable_requests",
    }:
        _integer(human[name], f"{package_id}.human_attention.{name}")
    _boolean(
        human["batchable_requests"], f"{package_id}.human_attention.batchable_requests"
    )
    for stem in ("sessions", "blocking_decisions", "active_minutes"):
        if human[f"{stem}_worst_case"] < human[f"{stem}_nominal"]:
            raise BudgetError(f"{package_id} human {stem} worst-case is below nominal")
    human_tier = policy["human_attention_tiers"][human_profile]
    for value_name, limit_name in (
        ("sessions_worst_case", "sessions_max"),
        ("blocking_decisions_worst_case", "blocking_decisions_max"),
        ("active_minutes_worst_case", "active_minutes_max"),
        ("max_single_session_minutes", "max_single_session_minutes"),
    ):
        limit = human_tier.get(limit_name)
        if limit is not None and human[value_name] > limit:
            raise BudgetLimitExceeded(
                f"{package_id} exceeds {human_profile} {value_name}"
            )
    return package_id, nominal, worst, human


def _compile_checkpoint_phase(
    phase: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[str, Mapping[str, Any]]:
    entry = _exact_keys(
        phase,
        {
            "phase_id",
            "publisher_available",
            "members",
            "replay_points",
            "publisher_eligible_minutes",
            "new_db_bytes",
            "fixed_trigger_counts",
            "checkpoint_components_bytes",
        },
        "checkpoint phase",
    )
    phase_id = _text(entry["phase_id"], "checkpoint phase id")
    publisher_available = _boolean(
        entry["publisher_available"], f"{phase_id}.publisher_available"
    )
    members = entry["members"]
    if (
        not isinstance(members, list)
        or not members
        or len(set(members)) != len(members)
    ):
        raise IncompleteGraph(f"{phase_id} members must be a non-empty unique list")
    replay_nominal, replay_worst = _pair(
        entry["replay_points"], f"{phase_id}.replay_points"
    )
    minutes_nominal, minutes_worst = _pair(
        entry["publisher_eligible_minutes"], f"{phase_id}.publisher_eligible_minutes"
    )
    db_nominal, db_worst = _pair(entry["new_db_bytes"], f"{phase_id}.new_db_bytes")
    trigger_nominal, trigger_worst = _pair(
        entry["fixed_trigger_counts"], f"{phase_id}.fixed_trigger_counts"
    )
    components = _exact_keys(
        entry["checkpoint_components_bytes"],
        {"nominal", "worst_case"},
        f"{phase_id}.components",
    )
    component_values: dict[str, int] = {}
    for bound in ("nominal", "worst_case"):
        values = components[bound]
        if not isinstance(values, list) or not values:
            raise IncompleteGraph(f"{phase_id}.{bound} checkpoint components are empty")
        component_values[bound] = sum(
            _integer(value, f"{phase_id}.{bound} component") for value in values
        )
    if component_values["worst_case"] < component_values["nominal"]:
        raise BudgetError(f"{phase_id} worst-case checkpoint bytes are below nominal")
    checkpoint_policy = policy["checkpoint"]
    window_nominal = max(
        _ceil_div(replay_nominal, checkpoint_policy["window_replay_point_divisor"]),
        _ceil_div(minutes_nominal, checkpoint_policy["window_minutes_divisor"]),
        _ceil_div(db_nominal, checkpoint_policy["window_db_bytes_divisor"]),
    )
    window_worst = max(
        _ceil_div(replay_worst, checkpoint_policy["window_replay_point_divisor"]),
        _ceil_div(minutes_worst, checkpoint_policy["window_minutes_divisor"]),
        _ceil_div(db_worst, checkpoint_policy["window_db_bytes_divisor"]),
    )
    publication_nominal = window_nominal + trigger_nominal if publisher_available else 0
    publication_worst = window_worst + trigger_worst if publisher_available else 0
    if not publisher_available and (trigger_nominal or trigger_worst):
        raise BudgetError(f"{phase_id} unavailable publisher has fixed triggers")
    if (
        phase_id == "K0b-F15-exact-measurement"
        and publication_worst
        >= policy["f15_publication_limits"]["unconditional_block_at_or_above"]
    ):
        raise BudgetLimitExceeded("F15 publication count blocks unconditionally")
    checkpoint_nominal = _round_up(
        component_values["nominal"], checkpoint_policy["mib_bytes"]
    )
    checkpoint_worst = _round_up(
        component_values["worst_case"], checkpoint_policy["mib_bytes"]
    )
    checkpoint_warning = checkpoint_policy["max_checkpoint_bytes"] // 2
    checkpoint_status = {
        "nominal": _status(
            checkpoint_nominal,
            checkpoint_warning,
            checkpoint_policy["max_checkpoint_bytes"],
        ),
        "worst_case": _status(
            checkpoint_worst,
            checkpoint_warning,
            checkpoint_policy["max_checkpoint_bytes"],
        ),
    }
    if "above_hard" in checkpoint_status.values():
        raise BudgetLimitExceeded(f"{phase_id} checkpoint meets or exceeds hard limit")
    factor_numerator = checkpoint_policy["planning_delta_factor_numerator"]
    factor_denominator = checkpoint_policy["planning_delta_factor_denominator"]
    pack_nominal = (
        checkpoint_nominal
        * publication_nominal
        * factor_numerator
        // factor_denominator
    )
    pack_worst = (
        checkpoint_worst * publication_worst * factor_numerator // factor_denominator
    )
    if not publisher_available:
        pack_status = {
            "nominal": "publisher_unavailable",
            "worst_case": "publisher_unavailable",
        }
    else:
        pack_status = {
            "nominal": _status(
                pack_nominal,
                checkpoint_policy["phase_pack_warning_bytes"],
                checkpoint_policy["max_phase_pack_bytes"],
            ),
            "worst_case": _status(
                pack_worst,
                checkpoint_policy["phase_pack_warning_bytes"],
                checkpoint_policy["max_phase_pack_bytes"],
            ),
        }
        if "above_hard" in pack_status.values():
            raise BudgetLimitExceeded(
                f"{phase_id} phase pack meets or exceeds hard limit"
            )
    cap = checkpoint_policy["publication_batch_cap"]
    batches_nominal = _ceil_div(publication_nominal, cap) if publication_nominal else 0
    batches_worst = _ceil_div(publication_worst, cap) if publication_worst else 0
    return phase_id, {
        "window_publications": {"nominal": window_nominal, "worst_case": window_worst},
        "publications": {
            "nominal": publication_nominal,
            "worst_case": publication_worst,
        },
        "checkpoint_bytes": {
            "nominal": checkpoint_nominal,
            "worst_case": checkpoint_worst,
        },
        "phase_pack_bytes": {"nominal": pack_nominal, "worst_case": pack_worst},
        "checkpoint_status": checkpoint_status,
        "phase_pack_status": pack_status,
        "batches": {"nominal": batches_nominal, "worst_case": batches_worst},
        "largest_batch_bytes": {
            "nominal": min(publication_nominal, cap) * checkpoint_nominal,
            "worst_case": min(publication_worst, cap) * checkpoint_worst,
        },
    }


def compile_resource_budget(
    case: Mapping[str, Any], policy: Mapping[str, Any]
) -> Mapping[str, Any]:
    validate_policy(policy)
    entry = _exact_keys(
        case,
        {
            "case_id",
            "profile",
            "graph_completeness",
            "packages",
            "checkpoint_phases",
            "binary_payload_budgets",
            "expected_reference_result",
        },
        "resource budget case",
    )
    case_id = _text(entry["case_id"], "case_id")
    if entry["profile"] not in {"K0a", "K0b"}:
        raise BudgetError(f"unknown resource budget profile for {case_id}")
    completeness = _exact_keys(
        entry["graph_completeness"],
        set(policy["required_graph_sections"]),
        "graph completeness",
    )
    if any(value is not True for value in completeness.values()):
        raise IncompleteGraph(
            f"{case_id} route/fan-out/retry/dialogue graph is incomplete"
        )
    packages = entry["packages"]
    if not isinstance(packages, list) or not packages:
        raise IncompleteGraph(f"{case_id} has no budget packages")
    package_calls: dict[str, dict[str, int]] = {}
    total_nominal = 0
    total_worst = 0
    human_totals = {
        "sessions_nominal": 0,
        "sessions_worst_case": 0,
        "blocking_decisions_nominal": 0,
        "blocking_decisions_worst_case": 0,
        "active_minutes_nominal": 0,
        "active_minutes_worst_case": 0,
    }
    call_node_totals: dict[str, tuple[int, int]] = {}
    for package in packages:
        package_id, nominal, worst, human = _compile_package(package, policy)
        if package_id in package_calls:
            raise IncompleteGraph(f"duplicate package_id: {package_id}")
        package_calls[package_id] = {"nominal": nominal, "worst_case": worst}
        total_nominal += nominal
        total_worst += worst
        for name in human_totals:
            human_totals[name] += human[name]
        for node in package["call_nodes"]:
            node_id = node["node_id"]
            if node_id in call_node_totals:
                raise IncompleteGraph(f"duplicate call node across packages: {node_id}")
            call_node_totals[node_id] = (node["nominal"], node["worst_case"])
    binary_nominal = 0
    binary_worst = 0
    binary_budgets = entry["binary_payload_budgets"]
    if not isinstance(binary_budgets, list) or not binary_budgets:
        raise BinaryPayloadBudgetError(f"{case_id} has no binary payload declarations")
    owners: set[str] = set()
    for binary in binary_budgets:
        owner = binary.get("owner") if isinstance(binary, dict) else None
        if owner in owners:
            raise BinaryPayloadBudgetError(f"duplicate binary payload owner: {owner}")
        owners.add(owner)
        nominal, worst = validate_binary_payload_budget(binary, policy)
        binary_nominal += nominal
        binary_worst += worst
    if owners != {"shared_control_plane", "shared_artifact_event_plane", "S"}:
        raise BinaryPayloadBudgetError(f"{case_id} binary owner coverage differs")
    phase_values = entry["checkpoint_phases"]
    if not isinstance(phase_values, list) or not phase_values:
        raise IncompleteGraph(f"{case_id} has no checkpoint phases")
    phase_order: list[str] = []
    phase_results: dict[str, Mapping[str, Any]] = {}
    all_members: list[str] = []
    for phase in phase_values:
        phase_id, result = _compile_checkpoint_phase(phase, policy)
        if phase_id in phase_results:
            raise IncompleteGraph(f"duplicate checkpoint phase: {phase_id}")
        phase_order.append(phase_id)
        phase_results[phase_id] = result
        all_members.extend(phase["members"])
    if len(all_members) != len(set(all_members)):
        raise IncompleteGraph("checkpoint phase membership overlaps")
    if entry["profile"] == "K0b":
        if tuple(phase_order) != CHECKPOINT_PHASE_ORDER:
            raise IncompleteGraph("K0b phases are missing, reordered, or widened")
        expected_membership = policy["k0b_work_item_membership"]
        actual_membership = {
            member: phase["phase_id"]
            for phase in phase_values
            for member in phase["members"]
        }
        if actual_membership != expected_membership:
            raise IncompleteGraph(
                "K0b phase membership is incomplete, overlapping, or reclassified"
            )
        for member, expected_calls in policy["k0b_call_allocation"].items():
            actual_calls = call_node_totals.get(member)
            if actual_calls != (
                expected_calls["nominal"],
                expected_calls["worst_case"],
            ):
                raise BudgetError(f"K0b call allocation differs for {member}")
        phase_by_id = {phase["phase_id"]: phase for phase in phase_values}
        if phase_by_id["K0b-runtime-operational"]["fixed_trigger_counts"] != {
            "nominal": 8,
            "worst_case": 16,
        }:
            raise BudgetError("operational fixed-trigger forecast differs")
        if phase_by_id["K0b-F15-exact-measurement"]["fixed_trigger_counts"] != {
            "nominal": 4,
            "worst_case": 4,
        }:
            raise BudgetError("F15 boundary trigger count differs")
        f15_publications = phase_results["K0b-F15-exact-measurement"]["publications"][
            "worst_case"
        ]
        limits = policy["f15_publication_limits"]
        if f15_publications != limits["forecast_worst_case"]:
            raise BudgetError("F15 forecast publication count differs")
        if f15_publications >= limits["unconditional_block_at_or_above"]:
            raise BudgetLimitExceeded("F15 publication count blocks unconditionally")
        total_publications_worst = sum(
            phase["publications"]["worst_case"] for phase in phase_results.values()
        )
        for binary in binary_budgets:
            if binary["mode"] == "applicable":
                if binary["checkpoint_publication_count"] != total_publications_worst:
                    raise BinaryPayloadBudgetError(
                        f"binary checkpoint publication count differs for {binary['owner']}"
                    )
                if (
                    binary["exact_forecast_sha256"]
                    != policy["authority"]["k0b_forecast_sha256"]
                ):
                    raise BinaryPayloadBudgetError(
                        f"binary forecast authority differs for {binary['owner']}"
                    )
    cumulative_pack = {
        "nominal": sum(
            phase["phase_pack_bytes"]["nominal"] for phase in phase_results.values()
        ),
        "worst_case": sum(
            phase["phase_pack_bytes"]["worst_case"] for phase in phase_results.values()
        ),
    }
    result = {
        "case_id": case_id,
        "package_calls": package_calls,
        "total_calls": {"nominal": total_nominal, "worst_case": total_worst},
        "human_attention": human_totals,
        "binary_payload": {
            "nominal_new_bytes": binary_nominal,
            "worst_case_new_bytes": binary_worst,
        },
        "checkpoint_phases": phase_results,
        "checkpoint_phase_order": phase_order,
        "cumulative_observable_phase_pack_bytes": cumulative_pack,
    }
    return result


def prove_reference_equivalence(
    reference_set: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[CompiledReference, ...]:
    root = _exact_keys(
        reference_set,
        {"reference_set_id", "version", "authority", "cases"},
        "reference set",
    )
    if (
        root["reference_set_id"] != "pipeline-v2.resource-budget-reference-cases"
        or root["version"] != "1.0.0"
    ):
        raise ReferenceMismatch("reference set identity differs")
    cases = root["cases"]
    if not isinstance(cases, list) or not cases:
        raise ReferenceMismatch("reference set is empty")
    compiled: list[CompiledReference] = []
    seen: set[str] = set()
    for case in cases:
        result = compile_resource_budget(case, policy)
        case_id = result["case_id"]
        if case_id in seen:
            raise ReferenceMismatch(f"duplicate reference case: {case_id}")
        seen.add(case_id)
        expected = case["expected_reference_result"]
        if canonical_json(result) != canonical_json(expected):
            raise ReferenceMismatch(
                f"compiled result differs from reference case {case_id}"
            )
        compiled.append(CompiledReference(case_id=case_id, result=result))
    return tuple(compiled)
