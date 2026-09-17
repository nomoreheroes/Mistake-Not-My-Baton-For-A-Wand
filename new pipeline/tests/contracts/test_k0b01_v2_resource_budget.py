from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


if "test_k0b01_v2_contracts" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "test_k0b01_v2_contracts",
        Path(__file__).with_name("test_k0b01_v2_contracts.py"),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

support = sys.modules["test_k0b01_v2_contracts"]
REPOSITORY = support.REPOSITORY
ctx = support.ctx
oracle = support.oracle
target = support.target
binary = importlib.import_module("k0b01_v2.binary_budget")
production = importlib.import_module("k0b01_v2.budget_compiler")
canonical = importlib.import_module("k0b01_v2.canonical")
registry_compiler = importlib.import_module("k0b01_v2.registry_compiler")


CASE_IDS = (
    "D0_K0a_packages",
    "D0_K0b_packages",
    "K0a_worksheet_packages",
    "K0b-runtime-operational.nominal",
    "K0b-runtime-operational.worst_case",
    "K0b-F15-exact-measurement.nominal",
    "K0b-F15-exact-measurement.worst_case",
    "K0a_checkpoint.nominal",
    "K0a_checkpoint.worst_case",
    "artifact_event_seed",
    "shared_control_binary_NA",
    "S_binary_NA",
)


@pytest.fixture(scope="session")
def inputs(ctx):
    return ctx.json(
        next(
            pin["path"]
            for pin in ctx.source_pins
            if pin["path"].endswith("/k0b01-reference-inputs-v2.json")
        )
    )


@pytest.fixture(scope="session")
def policy(ctx):
    return ctx.json(
        next(
            pin["path"]
            for pin in ctx.source_pins
            if pin["path"].endswith("/k0b01-policy-v2.json")
        )
    )


@pytest.fixture(scope="session")
def expected():
    return canonical.load_json(
        (
            REPOSITORY
            / "new pipeline/tests/k0b01_v2/fixtures/reference-expected-v1.json"
        ).read_bytes()
    )


@pytest.fixture(scope="session")
def budget_receipt(ctx):
    a = registry_compiler.compile_registry(ctx)
    return canonical.load_yaml(production.compile_budget(ctx, a, canonical.sha256(a)))


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_all_literal_reference_vectors(inputs, expected, budget_receipt, case_id):
    forecast = next(
        output["canonical_payload"]
        for output in budget_receipt["outputs"]
        if output["family"] == "compiled_resource_forecast"
    )
    actual = next(
        row["result"]
        for row in forecast["reference_results"]
        if row["case_id"] == case_id
    )
    literal = next(
        row["result"]
        for row in expected["authoritative_vectors"]
        if row["case_id"] == case_id
    )
    assert actual == literal
    assert {row["case_id"] for row in forecast["reference_results"]} == set(CASE_IDS)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_independent_oracle_matches_literals(inputs, expected, oracle, case_id):
    case = next(row for row in inputs["cases"] if row["case_id"] == case_id)
    literal = next(
        row["result"]
        for row in expected["authoritative_vectors"]
        if row["case_id"] == case_id
    )
    assert oracle.reference(case) == literal


def test_selected_stress_and_overlay(inputs, policy, expected, oracle, budget_receipt):
    literal = expected["literal_boundary_vectors"]["selected_stress"]
    assert (
        binary.stress_checkpoint(inputs["current_stress_inputs"], policy["thresholds"])
        == literal
    )
    assert oracle.stress(inputs["current_stress_inputs"]) == literal
    forecast = next(
        output["canonical_payload"]
        for output in budget_receipt["outputs"]
        if output["family"] == "compiled_resource_forecast"
    )
    assert forecast["review_overlay"] == expected["literal_review_overlay"]
    assert forecast["F15_size_stress"] == "blocked_missing_authoritative_object_count"
    assert forecast["phase_completion_claim"] is False
    assert all(
        row["canonical_payload"]["runtime_enabled"] is False
        for row in budget_receipt["outputs"]
    )


@pytest.mark.parametrize("plus_one", (False, True))
def test_rounding_30MiB_boundary(inputs, policy, expected, plus_one):
    value = copy.deepcopy(inputs["current_stress_inputs"])
    value["non_binary_worst_bytes"] = 30 * 1048576 + int(plus_one) - 7864320
    actual = binary.stress_checkpoint(value, policy["thresholds"])
    literal = expected["literal_boundary_vectors"][
        "rounding_30MiB_plus_one" if plus_one else "rounding_30MiB"
    ]
    assert (
        actual["unrounded_size_stressed_checkpoint_bytes"] == literal["unrounded_bytes"]
    )
    assert actual["rounded_size_stressed_checkpoint_bytes"] == literal["rounded_bytes"]
    assert actual["size_stressed_phase_pack_bytes"] == literal["pack_bytes"]
    assert actual["phase_result"] == literal["phase_result"]


def test_superseded_1MiB_is_above_hard(inputs, policy, expected):
    value = copy.deepcopy(inputs["current_stress_inputs"])
    value["hard_per_object_bytes"] = 1048576
    actual = binary.stress_checkpoint(value, policy["thresholds"])
    literal = expected["literal_boundary_vectors"]["superseded_1MiB_stress"]
    assert actual["size_stressed_bytes"] == literal["size_stressed_bytes"]
    assert (
        actual["rounded_size_stressed_checkpoint_bytes"]
        == literal["rounded_checkpoint_bytes"]
    )
    assert actual["size_stressed_phase_pack_bytes"] == literal["phase_pack_bytes"]
    assert actual["phase_result"] == literal["phase_result"]


@pytest.mark.parametrize("publications", range(26, 31))
def test_F15_literal_26_to_30(expected, policy, publications):
    assert (
        36700160 * publications
        == expected["literal_boundary_vectors"]["F15_publications"][str(publications)]
    )
    assert (
        36700160 * publications < policy["thresholds"]["phase_pack_hard_bytes"]
    ) == (publications <= 29)
    assert policy["F15"]["authoritative_worst_case_object_count"] is None


@pytest.mark.parametrize(
    "boundary",
    (
        "object_exact",
        "object_plus_one",
        "aggregate_exact",
        "aggregate_plus_one",
        "count_plus_one",
    ),
)
def test_actual_binary_limits(policy, boundary):
    definition = policy["current_binary_definition"]
    hard = definition["hard_per_object_bytes"]
    if boundary.startswith("object"):
        objects = [b"x" * (hard + (boundary == "object_plus_one"))]
    elif boundary.startswith("aggregate"):
        objects = [b"x" * hard for _ in range(12)]
        if boundary == "aggregate_plus_one":
            objects += [b"x"]
    else:
        objects = [b""] * 13
    if boundary.endswith("plus_one"):
        with pytest.raises(canonical.ContractError):
            binary.validate_actual(objects, definition)
    else:
        result = binary.validate_actual(objects, definition)
        assert result["actual_aggregate_bytes"] == sum(map(len, objects))


@pytest.mark.parametrize(
    "fault",
    (
        "missing",
        "bool_count",
        "negative",
        "unknown_F15",
        "mean_above_hard",
        "aggregate_below_stress",
        "runtime_below_stress",
        "credit",
        "factor",
        "provenance",
        "payload",
        "proof",
    ),
)
def test_binary_definition_rejects(policy, fault):
    value = copy.deepcopy(policy["current_binary_definition"])
    if fault == "missing":
        del value["assumed_mean_object_bytes"]
    elif fault == "bool_count":
        value["nominal_object_count"] = True
    elif fault == "negative":
        value["worst_case_object_count"] = -1
    elif fault == "unknown_F15":
        value["worst_case_object_count"] = None
    elif fault == "mean_above_hard":
        value["assumed_mean_object_bytes"] = value["hard_per_object_bytes"] + 1
    elif fault == "aggregate_below_stress":
        value["maximum_aggregate_new_bytes"] -= 1
    elif fault == "runtime_below_stress":
        value["runtime_aggregate_limit_bytes"] -= 1
    elif fault == "credit":
        value["credit"]["compression"] = 1
    elif fault == "factor":
        value["planning_pack_factor"] = 0.5
    elif fault == "provenance":
        value["forecast_provenance"] = []
    elif fault == "payload":
        value["payload_classes"] = []
    else:
        value["contract_proof"]["binary_persistence"] = False
    with pytest.raises(canonical.ContractError):
        binary.validate_definition(value)


@pytest.mark.parametrize("index", (0, 1))
@pytest.mark.parametrize(
    "fault",
    ("persistence", "reference", "producer_budget", "media", "count", "bool_zero"),
)
def test_binary_false_NA_rejects(policy, index, fault):
    value = copy.deepcopy(policy["binary_NA_definitions"][index])
    if fault == "persistence":
        value["contract_proof"]["binary_persistence"] = True
    elif fault == "reference":
        value["contract_proof"]["uses_only_version_refs"] = False
    elif fault == "producer_budget":
        value["contract_proof"]["payload_budgeted_by_producer"] = False
    elif fault == "media":
        value["media_types"] = ["application/octet-stream"]
    elif fault == "count":
        value["worst_case_object_count"] = 1
    else:
        value["nominal_new_bytes"] = False
    with pytest.raises(canonical.ContractError):
        binary.validate_definition(value)


@pytest.mark.parametrize(
    "fault",
    (
        "incomplete",
        "missing_node",
        "cycle",
        "dangling",
        "duplicate_node",
        "unknown_class",
        "missing_retry",
        "hidden_fast_path",
        "fallback",
        "dialogue_unbounded",
        "dialogue_double",
        "missing_as_zero",
        "light_exceeded",
        "deep_missing",
        "deep_unbounded",
        "human_missing",
        "human_unknown",
        "capacity_runtime",
    ),
)
def test_complete_package_graph_rejects(inputs, policy, fault):
    value = copy.deepcopy(inputs["cases"][0]["packages"][0])
    node = value["nodes"][0]
    if fault == "incomplete":
        value["graph_kind"] = "partial"
    elif fault == "missing_node":
        value["nodes"] = []
    elif fault == "cycle":
        other = copy.deepcopy(node)
        other["node_id"] = "other"
        value["nodes"] += [other]
        value["edges"] = [[node["node_id"], "other"], ["other", node["node_id"]]]
    elif fault == "dangling":
        value["edges"] = [[node["node_id"], "absent"]]
    elif fault == "duplicate_node":
        value["nodes"] += [copy.deepcopy(node)]
    elif fault == "unknown_class":
        node["call_class"] = "unknown"
    elif fault == "missing_retry":
        value["retry_bounds_complete"] = False
    elif fault == "hidden_fast_path":
        node["call_class"] = "compiled_fast_path"
    elif fault == "fallback":
        value["fallback"]["additional_calls"] = 1
    elif fault == "dialogue_unbounded":
        value["dialogue"].update(
            applicable=True, topics=7, sessions=1, rounds_per_topic=1, role_instances=1
        )
    elif fault == "dialogue_double":
        value["dialogue"].update(
            applicable=True, topics=1, sessions=1, rounds_per_topic=1, role_instances=1
        )
        node["call_class"] = "dialogue_role"
    elif fault == "missing_as_zero":
        node["nominal_calls_per_instance"] = 0
        node["bounded_zero_proof"] = None
    elif fault == "light_exceeded":
        node["worst_instances"] = 21
    elif fault == "deep_missing":
        value["invocation_profile"] = "deep"
    elif fault == "deep_unbounded":
        value["invocation_profile"] = "deep"
        value["deep_authority"] = dict(
            value["forecast_authority"],
            purpose="exact_static_forecast_not_run_authority",
        )
    elif fault == "human_missing":
        del value["human_attention"]["active_minutes"]
    elif fault == "human_unknown":
        value["human_attention"]["profile"] = "K0b"
    else:
        value["capacity"]["runtime_authorized"] = True
    with pytest.raises(canonical.ContractError):
        production.package_calls(value, policy)


def admission(partition, policy, member="K0b04_F15"):
    seal = {
        "partition_digest": partition["partition_digest"],
        "phase_id": partition["phase_order"][0],
        "result": "pass",
        "all_non_F15_terminal": True,
        "outbox_reconciled": True,
        "terminal_checkpoint_verified": True,
        "seal_committed": True,
        "checkpoint_bytes": 27262976,
        "projected_phase_pack_bytes": 926941184,
    }
    f15 = member in policy["phase_members"][partition["phase_order"][1]]
    return {
        "phase_id": partition["phase_order"][int(f15)],
        "partition_digest": partition["partition_digest"],
        "member_id": member,
        "predecessor_seal_digest": canonical.sha256(canonical.json_bytes(seal))
        if f15
        else None,
        "predecessor_seal": seal if f15 else None,
        "operational_sealed": f15,
        "F15_terminal": member in ("K0b04_post_F15", "K0b05"),
        "non_F15_call": False,
        "model_calls": policy["phase_call_allocations"][member][1],
        "boundary_triggers": partition["F15_boundary_triggers"] if f15 else [],
        "publications": 26 if f15 else 34,
        "batch_publications": 12,
        "separate_K0b05_run": False,
        "reopen": False,
        "publication_p95_seconds": 9,
        "restore_seconds": 119,
        "checkpoint_bytes": 36700160 if f15 else 27262976,
        "projected_phase_pack_bytes": 954204160 if f15 else 926941184,
    }


@pytest.mark.parametrize(
    "member",
    (
        "K0b01",
        "K0b02",
        "K0b03",
        "K0b04_pre_F15",
        "K0b04_F15",
        "K0b04_post_F15",
        "K0b05",
    ),
)
def test_two_phases_exact_membership_positive(ctx, policy, member):
    partition = production.phase_partition(policy, ctx.registry["phase_fences"])
    production.phase_guard(partition, admission(partition, policy, member), policy)


@pytest.mark.parametrize(
    "fault",
    (
        "third",
        "relabel",
        "unknown_member",
        "stale",
        "unsealed",
        "stale_seal",
        "nonterminal_seal",
        "over_limit_seal",
        "non_F15",
        "terminal_F15_model",
        "call_35",
        "call_37",
        "fifth_trigger",
        "duplicate_trigger",
        "pub_27",
        "pub_30",
        "batch_13",
        "separate_run",
        "reopen",
        "p95_10",
        "restore_120",
        "checkpoint_exact",
        "phase_exact",
        "credit",
        "post_F15_model",
        "post_F15_before_terminal",
    ),
)
def test_phase_guards_fail_before_effect(ctx, policy, fault):
    partition = production.phase_partition(policy, ctx.registry["phase_fences"])
    value = admission(
        partition, policy, "K0b05" if fault.startswith("post_F15") else "K0b04_F15"
    )
    if fault in ("third", "relabel"):
        value["phase_id"] = "third" if fault == "third" else "renamed"
    elif fault == "unknown_member":
        value["member_id"] = "unclassified"
    elif fault == "stale":
        value["partition_digest"] = "0" * 64
    elif fault == "unsealed":
        value["operational_sealed"] = False
    elif fault == "stale_seal":
        value["predecessor_seal_digest"] = "0" * 64
    elif fault in ("nonterminal_seal", "over_limit_seal"):
        value["predecessor_seal"][
            "seal_committed"
            if fault == "nonterminal_seal"
            else "projected_phase_pack_bytes"
        ] = False if fault == "nonterminal_seal" else 1073741824
        value["predecessor_seal_digest"] = canonical.sha256(
            canonical.json_bytes(value["predecessor_seal"])
        )
    elif fault == "non_F15":
        value["non_F15_call"] = True
    elif fault == "terminal_F15_model":
        value["F15_terminal"] = True
    elif fault.startswith("call_"):
        value["model_calls"] = int(fault.split("_")[1])
    elif fault == "fifth_trigger":
        value["boundary_triggers"] = value["boundary_triggers"] + ["fifth"]
    elif fault == "duplicate_trigger":
        value["boundary_triggers"] = value["boundary_triggers"] + [
            value["boundary_triggers"][0]
        ]
    elif fault.startswith("pub_"):
        value["publications"] = int(fault.split("_")[1])
        value["projected_phase_pack_bytes"] = 36700160 * value["publications"]
    elif fault == "batch_13":
        value["batch_publications"] = 13
    elif fault == "separate_run":
        value["separate_K0b05_run"] = True
    elif fault == "reopen":
        value["reopen"] = True
    elif fault == "p95_10":
        value["publication_p95_seconds"] = 10
    elif fault == "restore_120":
        value["restore_seconds"] = 120
    elif fault == "checkpoint_exact":
        value["checkpoint_bytes"] = 104857600
    elif fault == "phase_exact":
        value["projected_phase_pack_bytes"] = 1073741824
    elif fault == "credit":
        value["projected_phase_pack_bytes"] = 1
    elif fault == "post_F15_model":
        value["model_calls"] = 1
    else:
        value["F15_terminal"] = False
    with pytest.raises(canonical.ContractError):
        production.phase_guard(partition, value, policy)


@pytest.mark.parametrize(
    "fault", ("overlap", "gap", "extra_phase", "duplicate", "unclassified")
)
def test_partition_closure_rejects(ctx, policy, fault):
    value = copy.deepcopy(policy)
    first, second = ctx.registry["phase_fences"]["phase_order"]
    if fault == "overlap":
        value["phase_members"][second] += [value["phase_members"][first][0]]
    elif fault == "gap":
        value["phase_members"][first].pop()
    elif fault == "extra_phase":
        value["phase_members"]["third"] = ["extra"]
    elif fault == "duplicate":
        value["phase_members"][first] += [value["phase_members"][first][0]]
    else:
        value["phase_call_allocations"]["unknown"] = [0, 0]
    with pytest.raises(canonical.ContractError):
        production.phase_partition(value, ctx.registry["phase_fences"])


@pytest.mark.parametrize(
    "fault",
    (
        "publication",
        "count",
        "mean",
        "hard",
        "nonbinary",
        "threshold",
        "warning",
        "timing",
        "window",
        "provenance",
        "F15_count",
        "oracle",
        "reclassify",
        "node_count",
    ),
)
def test_full_compiler_exact_input_rejects(ctx, inputs, policy, monkeypatch, fault):
    p, i = copy.deepcopy(policy), copy.deepcopy(inputs)
    if fault in ("publication", "count", "mean", "hard", "nonbinary"):
        key = {
            "publication": "publications",
            "count": "worst_case_object_count",
            "mean": "assumed_mean_object_bytes",
            "hard": "hard_per_object_bytes",
            "nonbinary": "non_binary_worst_bytes",
        }[fault]
        i["current_stress_inputs"][key] += 1
    elif fault == "threshold":
        p["thresholds"]["checkpoint_hard_bytes"] += 1
    elif fault == "warning":
        p["thresholds"]["warning_bytes"] += 1
    elif fault == "timing":
        p["thresholds"]["restore_seconds"] += 1
    elif fault == "window":
        p["window_divisors"]["points"] += 1
    elif fault == "provenance":
        i["normative_provenance"][0]["sha256"] = "0" * 64
    elif fault == "F15_count":
        i["F15_authoritative_worst_case_object_count"] = 12
    elif fault == "oracle":
        i["expected_outputs"] = {}
    elif fault == "reclassify":
        first, second = ctx.registry["phase_fences"]["phase_order"]
        p["phase_members"][second] += [p["phase_members"][first].pop(0)]
    else:
        i["cases"][0]["packages"][0]["nodes"][0]["nominal_instances"] += 1
    a = registry_compiler.compile_registry(ctx)
    original = ctx.json
    monkeypatch.setattr(
        ctx,
        "json",
        lambda path: (
            p
            if path.endswith("/k0b01-policy-v2.json")
            else i
            if path.endswith("/k0b01-reference-inputs-v2.json")
            else original(path)
        ),
    )
    with pytest.raises(canonical.ContractError):
        production.compile_budget(ctx, a, canonical.sha256(a))
