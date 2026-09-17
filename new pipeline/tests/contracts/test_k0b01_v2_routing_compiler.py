from __future__ import annotations

import copy
import importlib.util
import locale
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
EVENT_TYPES = support.EVENT_TYPES
ctx = support.ctx
target = support.target
budget_compiler = importlib.import_module("k0b01_v2.budget_compiler")
canonical = importlib.import_module("k0b01_v2.canonical")
production = importlib.import_module("k0b01_v2.registry_compiler")


@pytest.fixture(scope="session")
def receipts(ctx):
    a = production.compile_registry(ctx)
    b = budget_compiler.compile_budget(ctx, a, canonical.sha256(a))
    combined = production.aggregate(ctx, a, canonical.sha256(a), b, canonical.sha256(b))
    return a, b, combined


def test_receipt_partition_and_repeat_determinism(ctx, receipts):
    a, b, combined = receipts
    av, bv, cv = map(canonical.load_yaml, receipts)
    assert av["owner"] == "registry_and_routing" and len(av["outputs"]) == 5
    assert bv["owner"] == "resource_and_budget" and len(bv["outputs"]) == 3
    assert av["dependencies"] == {} and bv["dependencies"][
        "receipt_A_sha256"
    ] == canonical.sha256(a)
    assert len(cv["outputs"]) == len({row["family"] for row in cv["outputs"]}) == 8
    assert all(
        row["canonical_payload"]["runtime_enabled"] is False for row in cv["outputs"]
    )
    assert a == production.compile_registry(ctx)
    assert b == budget_compiler.compile_budget(ctx, a, canonical.sha256(a))
    assert combined == production.aggregate(
        ctx, a, canonical.sha256(a), b, canonical.sha256(b)
    )


@pytest.mark.parametrize("variant", ("cwd", "locale", "map_order"))
def test_compilation_environment_and_map_order_equivalence(
    ctx, receipts, target, monkeypatch, variant
):
    def reverse_maps(value):
        if isinstance(value, dict):
            return {key: reverse_maps(value[key]) for key in reversed(value)}
        if isinstance(value, list):
            return [reverse_maps(item) for item in value]
        return value

    original = locale.setlocale(locale.LC_ALL)
    try:
        if variant == "cwd":
            monkeypatch.chdir(target / ".tmp")
        elif variant == "locale":
            locale.setlocale(locale.LC_ALL, "C")
        else:
            monkeypatch.setattr(ctx, "registry", reverse_maps(ctx.registry))
            old_json = ctx.json
            monkeypatch.setattr(ctx, "json", lambda path: reverse_maps(old_json(path)))
        a = production.compile_registry(ctx)
        b = budget_compiler.compile_budget(ctx, a, canonical.sha256(a))
        combined = production.aggregate(
            ctx, a, canonical.sha256(a), b, canonical.sha256(b)
        )
        assert (a, b, combined) == receipts
    finally:
        locale.setlocale(locale.LC_ALL, original)


@pytest.mark.parametrize("event_type", EVENT_TYPES)
@pytest.mark.parametrize(
    "fault",
    (
        "producer",
        "subscriber",
        "policy",
        "state",
        "field",
        "activation",
        "replay",
        "key",
    ),
)
def test_normative_event_matrix_rejects(ctx, monkeypatch, event_type, fault):
    registry = copy.deepcopy(ctx.registry)
    row = next(row for row in registry["events"] if row["event_type"] == event_type)
    if fault == "producer":
        row["producer"] = "unknown"
    elif fault in ("subscriber", "state"):
        row["profile_branches"]["Alpha0"][fault] = "unknown"
    elif fault == "policy":
        row["profile_branches"]["Alpha0"]["terminal_policy"] = "unknown"
    elif fault == "field":
        row["profile_branches"]["Alpha0"]["fields_read"] += ["unknown"]
    elif fault == "activation":
        row["profile_branches"]["Alpha0"]["activation_work_item"] = "K0b-99"
    elif fault == "replay":
        row["replay_rule"] = "new unauthorized rule"
    else:
        row["idempotency_fields"] += ["unknown"]
    original = ctx.json
    monkeypatch.setattr(
        ctx,
        "json",
        lambda path: (
            registry if path == ctx.package["registry_locator"] else original(path)
        ),
    )
    with pytest.raises(canonical.ContractError):
        production.validate_registry(ctx)


@pytest.mark.parametrize(
    "fault",
    (
        "missing_event",
        "extra_event",
        "duplicate_event",
        "missing_F00",
        "extra_delivery",
        "unknown_family",
        "run_state",
        "runtime",
        "third_phase",
        "dynamic",
        "quorum",
        "owner_rule",
    ),
)
def test_registry_closed_catalog_rejects(ctx, monkeypatch, fault):
    value = copy.deepcopy(ctx.registry)
    if fault == "missing_event":
        value["events"].pop()
    elif fault == "extra_event":
        row = copy.deepcopy(value["events"][0])
        row["event_type"] = "unknown.event"
        value["events"].append(row)
    elif fault == "duplicate_event":
        value["events"][1] = copy.deepcopy(value["events"][0])
    elif fault == "missing_F00":
        del value["events"][0]["profile_branches"]["F00"]
    elif fault == "extra_delivery":
        value["events"][0]["profile_branches"]["extra"] = copy.deepcopy(
            value["events"][0]["profile_branches"]["Alpha0"]
        )
    elif fault == "unknown_family":
        value["output_families"]["registry_and_routing"][0] = "unknown"
    elif fault == "run_state":
        value["run_states"] += ["unknown"]
    elif fault == "runtime":
        value["phase_fences"]["runtime_enabled"] = True
    elif fault == "third_phase":
        value["phase_fences"]["phase_order"] += ["third"]
    elif fault == "dynamic":
        value["F04_rule"]["dynamic_membership"] = True
    elif fault == "quorum":
        value["F04_rule"]["barrier"] = "quorum"
    else:
        value["F05_rule"]["producer_invocation_is_lineage_only"] = False
    original = ctx.json
    monkeypatch.setattr(
        ctx,
        "json",
        lambda path: (
            value if path == ctx.package["registry_locator"] else original(path)
        ),
    )
    with pytest.raises(canonical.ContractError):
        production.validate_registry(ctx)


@pytest.mark.parametrize(
    "fault",
    (
        "nonpass",
        "diagnostic",
        "owner",
        "compiler",
        "source",
        "schema",
        "missing",
        "extra",
        "duplicate",
        "payload",
        "size",
        "runtime",
        "reverse",
        "stale_A",
        "stale_A_output",
        "accepted_hash",
    ),
)
def test_aggregate_rejects(ctx, receipts, fault):
    a, b, _ = receipts
    av, bv = canonical.load_yaml(a), canonical.load_yaml(b)
    if fault == "nonpass":
        bv["result"] = "fail"
    elif fault == "diagnostic":
        bv["diagnostics"] = ["problem"]
    elif fault == "owner":
        bv["owner"] = av["owner"]
    elif fault == "compiler":
        bv["compiler"] = av["compiler"]
    elif fault in ("source", "schema"):
        index = (
            0
            if fault == "source"
            else next(
                i
                for i, p in enumerate(bv["inputs"]["source_pins"])
                if p["path"].endswith("schema.json")
            )
        )
        bv["inputs"]["source_pins"][index]["sha256"] = "0" * 64
    elif fault == "missing":
        bv["outputs"].pop()
    elif fault == "extra":
        bv["outputs"].append(av["outputs"][0])
    elif fault == "duplicate":
        bv["outputs"][1] = copy.deepcopy(bv["outputs"][0])
    elif fault == "payload":
        bv["outputs"][0]["canonical_payload"]["new"] = True
    elif fault == "size":
        bv["outputs"][0]["bytes"] += 1
    elif fault == "runtime":
        bv["runtime_enabled"] = True
    elif fault == "reverse":
        av["dependencies"] = {"receipt_B_sha256": canonical.sha256(b)}
    elif fault == "stale_A":
        bv["dependencies"]["receipt_A_sha256"] = "0" * 64
    elif fault == "stale_A_output":
        family = next(iter(bv["dependencies"]["receipt_A_output_hashes"]))
        bv["dependencies"]["receipt_A_output_hashes"][family] = "0" * 64
    a, b = canonical.yaml_bytes(av), canonical.yaml_bytes(bv)
    with pytest.raises(canonical.ContractError):
        production.aggregate(
            ctx,
            a,
            "0" * 64 if fault == "accepted_hash" else canonical.sha256(a),
            b,
            canonical.sha256(b),
        )


def test_terminal_snapshot_has_no_semantic_downstream(receipts):
    a = canonical.load_yaml(receipts[0])
    graph = next(
        row["canonical_payload"]
        for row in a["outputs"]
        if row["family"] == "compiled_event_reachability_graph"
    )
    assert len(graph["edges"]) == 26
    for row in graph["edges"]:
        if row["terminal"]:
            assert row["downstream_semantic_routes"] == []
    terminal = {
        row["event_type"]
        for row in graph["edges"]
        if row["terminal"] and row["profile"] == "Alpha0"
    }
    assert {
        "run.blocked",
        "projection.failed",
        "error.schema_mismatch",
        "error.tool_failure",
        "error.security_policy",
        "meta.incident_detected",
    } <= terminal


def result(member, index):
    return {
        "member": member,
        "result_id": "result-" + str(index),
        "sha256": str(index) * 64,
        "terminal": "valid_terminal",
    }


def test_F04_all_required_deduplicated(ctx):
    rule = ctx.registry["F04_rule"]
    first, second = [
        result(member, index + 1) for index, member in enumerate(rule["members"])
    ]
    assert not production.barrier(rule, [])
    assert not production.barrier(rule, [first, first])
    assert production.barrier(rule, [second, first, first])


@pytest.mark.parametrize(
    "fault",
    (
        "unknown",
        "nonterminal",
        "conflicting",
        "cross_member_duplicate",
        "bad_sha",
        "quorum",
        "peer_visible",
        "dynamic",
    ),
)
def test_F04_rejects(ctx, fault):
    rule = copy.deepcopy(ctx.registry["F04_rule"])
    rows = [result(member, index + 1) for index, member in enumerate(rule["members"])]
    if fault == "unknown":
        rows[0]["member"] = "unknown"
    elif fault == "nonterminal":
        rows[0]["terminal"] = "pending"
    elif fault == "conflicting":
        extra = copy.deepcopy(rows[0])
        extra["sha256"] = "f" * 64
        rows += [extra]
    elif fault == "cross_member_duplicate":
        rows[1]["result_id"] = rows[0]["result_id"]
    elif fault == "bad_sha":
        rows[0]["sha256"] = "bad"
    elif fault == "quorum":
        rule["barrier"] = "quorum"
    elif fault == "peer_visible":
        rule["peer_visibility_before_barrier"] = True
    else:
        rule["dynamic_membership"] = True
    with pytest.raises(canonical.ContractError):
        production.barrier(rule, rows)


def revision(ctx):
    return {
        "revision_owner_zero_role_id": ctx.registry["F05_rule"][
            "revision_owner_zero_role_id"
        ],
        "producer_invocation_id": "producer-invocation",
        "producer_role_id": "fixture.alpha0.producer",
    }


def test_F05_owner_distinct_from_lineage(ctx):
    assert (
        production.revision_owner(ctx.registry["F05_rule"], revision(ctx))
        == "fixture.alpha0.upstream_zero"
    )


@pytest.mark.parametrize(
    "fault", ("owner", "producer_role", "invocation", "missing", "extra")
)
def test_F05_rejects(ctx, fault):
    proposal = revision(ctx)
    if fault == "owner":
        proposal["revision_owner_zero_role_id"] = "unknown"
    elif fault == "producer_role":
        proposal["producer_role_id"] = proposal["revision_owner_zero_role_id"]
    elif fault == "invocation":
        proposal["producer_invocation_id"] = proposal["revision_owner_zero_role_id"]
    elif fault == "missing":
        proposal.pop("producer_invocation_id")
    else:
        proposal["extra"] = 1
    with pytest.raises(canonical.ContractError):
        production.revision_owner(ctx.registry["F05_rule"], proposal)


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize(
    "fault", ("positive", "stale_partition", "unknown_phase", "direct_handoff")
)
def test_five_static_S_routes(ctx, index, fault):
    route = ctx.registry["routes"][index]
    proposal = {
        "route_id": route["route_id"],
        "phase_id": ctx.registry["phase_fences"]["phase_order"][0],
        "partition_digest": "a" * 64,
        "accepted_partition_digest": "a" * 64,
        "direct_actor_handoff": False,
        "revision_proposal": revision(ctx) if route["class"] == "revision" else None,
    }
    if fault == "stale_partition":
        proposal["partition_digest"] = "b" * 64
    elif fault == "unknown_phase":
        proposal["phase_id"] = "third"
    elif fault == "direct_handoff":
        proposal["direct_actor_handoff"] = True
    if fault != "positive":
        with pytest.raises(canonical.ContractError):
            production.static_route(ctx.registry, proposal)
    else:
        selected = production.static_route(ctx.registry, proposal)
        assert selected == route and selected["direct_actor_handoff"] is False
        if route["class"] == "compiled_nominal":
            assert selected["dispatcher_calls"] == 0
        if route["class"] == "layer0_fallback":
            assert selected["dispatcher_calls"] == 1
