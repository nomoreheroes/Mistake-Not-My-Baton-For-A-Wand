"""Closed deterministic Alpha registry and routing compiler."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .budget import BudgetError, prove_reference_equivalence, validate_policy
from .contract import (
    CHECKPOINT_PHASE_ORDER,
    EXACT_EVENT_TYPES,
    EXACT_ROUTE_IDS,
    F15_TRIGGER_IDS,
    REQUIRED_OUTPUT_FAMILIES,
    ContractBundle,
    canonical_json,
    load_contract_bundle,
    sha256_json,
)


COMPILER_ID = "pipeline-v2.k0b01.registry-routing-compiler"
COMPILER_VERSION = "1.0.0"
COMPILER_PATH = Path(__file__).resolve()
RESOURCE_COMPILER_PATH = COMPILER_PATH.with_name("budget.py")
EXACT_EVENT_METADATA = {
    "command.received": ("shared_control", "K0b-01", "append_once"),
    "run.started": ("shared_control", "K0b-01", "immutable_observation"),
    "artifact.version_created": (
        "shared_artifact_event",
        "K0b-01",
        "immutable_lineage",
    ),
    "handoff.ready": ("shared_artifact_event", "K0b-01", "immutable_delivery"),
    "run.completed": ("shared_control", "K0b-01", "terminal_immutable"),
    "run.blocked": ("shared_control", "K0b-01", "terminal_immutable"),
    "run.abort_requested": (
        "human_operator_or_shared_control",
        "K0b-03",
        "append_once",
    ),
    "run.aborted": ("shared_control", "K0b-03", "terminal_immutable"),
    "artifact.published": ("shared_artifact_event", "K0b-02", "immutable_lineage"),
    "projection.requested": ("shared_control", "K0b-02", "durable_intent"),
    "projection.written": ("shared_artifact_event", "K0b-02", "immutable_result"),
    "projection.failed": ("shared_artifact_event", "K0b-02", "terminal_immutable"),
    "revision.requested": ("registered_consumer", "K0b-01", "append_once_new_revision"),
    "gate.passed": ("shared_control", "K0b-01", "immutable_observation"),
    "approval.requested": ("shared_control", "K0b-01", "durable_human_request"),
    "approval.granted": ("human_project_owner", "K0b-01", "immutable_owner_decision"),
    "approval.rejected": ("human_project_owner", "K0b-01", "immutable_owner_decision"),
    "error.schema_mismatch": (
        "deterministic_validator",
        "K0b-01",
        "terminal_immutable",
    ),
    "error.tool_failure": ("shared_control", "K0b-03", "terminal_immutable"),
    "error.security_policy": ("security_guard", "K0b-03", "terminal_immutable"),
    "meta.incident_detected": (
        "shared_control_or_security_guard",
        "K0b-01",
        "terminal_immutable",
    ),
}


class CompilerError(RuntimeError):
    """A source registry or compiled graph is incomplete, stale, or widened."""


class ReachabilityError(CompilerError):
    """An event, subscriber, terminal policy, or consumed field is dangling."""


class RoutingError(CompilerError):
    """The S route table or its barrier/freeze rules are invalid."""


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise CompilerError(
            f"{label} keys must be exactly {sorted(expected)!r}, got {actual!r}"
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CompilerError(f"{label} must be non-empty trimmed text")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise CompilerError(
            f"{label} must be {'a' if allow_empty else 'a non-empty'} list"
        )
    if any(
        not isinstance(item, str) or not item or item != item.strip() for item in value
    ):
        raise CompilerError(f"{label} contains invalid text")
    if len(value) != len(set(value)):
        raise CompilerError(f"{label} contains duplicates")
    return value


def _validate_event_and_subscription_profiles(
    bundle: ContractBundle,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    event_root = _exact_keys(
        bundle.event_profile,
        {"registry_id", "version", "profile", "events"},
        "event profile",
    )
    if (
        event_root["registry_id"] != "pipeline-v2.alpha0.event-profile"
        or event_root["version"] != "1.0.0"
        or event_root["profile"] != "Alpha0"
    ):
        raise ReachabilityError("event profile identity differs")
    events = event_root["events"]
    if (
        not isinstance(events, list)
        or tuple(item.get("event_type") for item in events) != EXACT_EVENT_TYPES
    ):
        raise ReachabilityError(
            "event profile is not the exact ordered 21-event catalog"
        )
    event_schema = bundle.package["schema_contracts"]["event_registry_entry"]
    required_event_fields = set(event_schema["required_fields"])
    for event in events:
        entry = _exact_keys(
            event, required_event_fields, f"event {event.get('event_type')}"
        )
        event_type = entry["event_type"]
        if entry["event_version"] != 1 or entry["payload_schema_version"] != 1:
            raise ReachabilityError(f"event version differs for {event_type}")
        expected_schema_id = (
            f"pipeline-v2.{event_type.replace('.', '-').replace('_', '-')}"
        )
        if entry["payload_schema_id"] != expected_schema_id:
            raise ReachabilityError(f"payload schema identity differs for {event_type}")
        _text(entry["route_ref"], f"{event_type}.route_ref")
        fields = _string_list(
            entry["fields_consumed"], f"{event_type}.fields_consumed", allow_empty=False
        )
        schema_identity = {
            "additional_properties": False,
            "id": entry["payload_schema_id"],
            "required_fields": fields,
            "version": entry["payload_schema_version"],
        }
        if entry["payload_schema_sha256"] != sha256_json(schema_identity):
            raise ReachabilityError(f"payload schema hash differs for {event_type}")
        expected_producer, expected_activation, expected_replay = EXACT_EVENT_METADATA[
            event_type
        ]
        if entry["producer_owner"] != expected_producer:
            raise ReachabilityError(f"producer owner differs for {event_type}")
        if entry["activation_work_item"] != expected_activation:
            raise ReachabilityError(f"activation work item differs for {event_type}")
        if entry["replay_semantics"] != expected_replay:
            raise ReachabilityError(f"replay semantics differ for {event_type}")
        if entry["idempotency_scope"] != "run_event_type_key":
            raise ReachabilityError(f"idempotency scope differs for {event_type}")
        _string_list(
            entry["allowed_subscribers"],
            f"{event_type}.allowed_subscribers",
            allow_empty=True,
        )
        if entry["terminal_policy"] is not None:
            _text(entry["terminal_policy"], f"{event_type}.terminal_policy")
        _text(entry["terminal_disposition"], f"{event_type}.terminal_disposition")

    route_root = _exact_keys(
        bundle.subscription_profile,
        {"registry_id", "version", "profile", "routes", "f00_exception"},
        "subscription profile",
    )
    if (
        route_root["registry_id"] != "pipeline-v2.alpha0.subscription-terminal-profile"
        or route_root["version"] != "1.0.0"
        or route_root["profile"] != "Alpha0"
    ):
        raise ReachabilityError("subscription profile identity differs")
    routes = route_root["routes"]
    if not isinstance(routes, list) or not routes:
        raise ReachabilityError("subscription profile is empty")
    route_schema = bundle.package["schema_contracts"]["subscription_terminal_entry"]
    required_route_fields = set(route_schema["required_fields"])
    route_by_id: dict[str, Mapping[str, Any]] = {}
    for route in routes:
        entry = _exact_keys(
            route, required_route_fields, f"subscription route {route.get('route_id')}"
        )
        route_id = _text(entry["route_id"], "subscription route id")
        if route_id in route_by_id:
            raise ReachabilityError(f"duplicate subscription route: {route_id}")
        kind = entry["kind"]
        subscribers = _string_list(
            entry["subscribers"], f"{route_id}.subscribers", allow_empty=True
        )
        fields_read = _string_list(
            entry["fields_read"], f"{route_id}.fields_read", allow_empty=False
        )
        terminal = entry["terminal_policy"]
        if kind == "subscriber":
            if not subscribers or terminal is not None:
                raise ReachabilityError(
                    f"subscriber route {route_id} is dangling or terminal"
                )
        elif kind == "terminal":
            if subscribers or not isinstance(terminal, str) or not terminal:
                raise ReachabilityError(
                    f"terminal route {route_id} has a subscriber or no policy"
                )
        else:
            raise ReachabilityError(f"unknown route kind for {route_id}")
        _text(entry["activation_work_item"], f"{route_id}.activation_work_item")
        if not fields_read:
            raise ReachabilityError(f"route {route_id} reads no fields")
        route_by_id[route_id] = entry
    referenced_route_ids = {event["route_ref"] for event in events}
    if referenced_route_ids != set(route_by_id):
        raise ReachabilityError("event-to-route graph has missing or unused routes")
    for event in events:
        route = route_by_id[event["route_ref"]]
        if event["fields_consumed"] != route["fields_read"]:
            raise ReachabilityError(f"consumed fields differ for {event['event_type']}")
        if event["allowed_subscribers"] != route["subscribers"]:
            raise ReachabilityError(
                f"subscriber snapshot differs for {event['event_type']}"
            )
        if event["terminal_policy"] != route["terminal_policy"]:
            raise ReachabilityError(
                f"terminal policy differs for {event['event_type']}"
            )
        expected_disposition = (
            "subscriber_snapshot"
            if route["kind"] == "subscriber"
            else route["terminal_policy"]
        )
        if event["terminal_disposition"] != expected_disposition:
            raise ReachabilityError(
                f"terminal disposition differs for {event['event_type']}"
            )
    expected_terminal = {
        "error.schema_mismatch": "block_run_and_enqueue_human",
        "error.tool_failure": "block_run_and_enqueue_human",
        "error.security_policy": "block_run_and_enqueue_human",
        "meta.incident_detected": "persist_incident_and_enqueue_W5",
    }
    for event_type, policy in expected_terminal.items():
        event = events[EXACT_EVENT_TYPES.index(event_type)]
        if route_by_id[event["route_ref"]]["terminal_policy"] != policy:
            raise ReachabilityError(f"terminal policy differs for {event_type}")
    f00 = _exact_keys(
        route_root["f00_exception"],
        {
            "event_type",
            "subscriber",
            "terminal_policy",
            "allowed_only_under_contract_sha256",
        },
        "F00 exception",
    )
    if f00 != {
        "event_type": "handoff.ready",
        "subscriber": "bootstrap_sink",
        "terminal_policy": "fixture_terminal",
        "allowed_only_under_contract_sha256": "5b8b677aa98416d85db29a12bb0369e98369dcdfae98249dfaf813eeb08a19c6",
    }:
        raise ReachabilityError("F00 bootstrap-sink exception differs")
    edges: list[Mapping[str, Any]] = []
    for event in events:
        route = route_by_id[event["route_ref"]]
        edges.append(
            {"from": f"event:{event['event_type']}", "to": f"route:{route['route_id']}"}
        )
        if route["kind"] == "terminal":
            edges.append(
                {
                    "from": f"route:{route['route_id']}",
                    "to": f"terminal:{route['terminal_policy']}",
                }
            )
        else:
            for subscriber in route["subscribers"]:
                edges.append(
                    {
                        "from": f"route:{route['route_id']}",
                        "to": f"subscriber:{subscriber}",
                    }
                )
    return events, routes, edges


def _validate_routing_profile(
    bundle: ContractBundle,
) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    root = _exact_keys(
        bundle.routing_profile,
        {
            "registry_id",
            "version",
            "profile",
            "routes",
            "barriers",
            "revision_owner_rule",
            "freeze_policy",
        },
        "S routing profile",
    )
    if (
        root["registry_id"] != "pipeline-v2.alpha0.s-routing-profile"
        or root["version"] != "1.0.0"
        or root["profile"] != "Alpha0"
    ):
        raise RoutingError("S routing profile identity differs")
    routes = root["routes"]
    if (
        not isinstance(routes, list)
        or tuple(route.get("route_id") for route in routes) != EXACT_ROUTE_IDS
    ):
        raise RoutingError("S route set or order differs")
    schema = bundle.package["schema_contracts"]["s_route_entry"]
    required_fields = set(schema["required_fields"])
    exact_semantics = {
        "s.alpha0.compiled_nominal.v1": {
            "predicate": "exact_machine_known_outcome_and_all_guards_true",
            "disposition": "compiled_nominal",
            "target": "compiled_exact_target",
            "barrier_ref": None,
            "call_class": "deterministic_zero_call",
            "capabilities": [],
            "allowed_events": ["gate.passed", "handoff.ready"],
        },
        "s.alpha0.layer0_fallback.v1": {
            "predicate": "registered_ambiguous_or_non_nominal_case_and_all_guards_true",
            "disposition": "dispatcher_required",
            "target": "fixture.alpha0.layer0_fallback",
            "barrier_ref": None,
            "call_class": "non_F15_physical_pre_seal",
            "capabilities": [
                "bounded_text_input",
                "bounded_schema_conforming_text_output",
            ],
            "allowed_events": [],
        },
        "s.alpha0.f04.parallel_review.v1": {
            "predicate": "exact_F04_compatible_reviewer_snapshot",
            "disposition": "parallel_review",
            "target": "fixture.alpha0.review_barrier",
            "barrier_ref": "f04.alpha0.all_required.v1",
            "call_class": "non_F15_physical_pre_seal",
            "capabilities": [
                "bounded_text_input",
                "bounded_schema_conforming_text_output",
            ],
            "allowed_events": ["gate.passed", "revision.requested"],
        },
        "s.alpha0.f05.revision.v1": {
            "predicate": "accepted_existing_version_and_registered_consumer_revision",
            "disposition": "owner_resolved",
            "target": "fixture.alpha0.upstream_zero",
            "barrier_ref": None,
            "call_class": "deterministic_zero_call",
            "capabilities": [],
            "allowed_events": ["revision.requested"],
        },
        "s.alpha0.blocked.v1": {
            "predicate": "missing_stale_conflicting_forbidden_incompatible_or_phase_fenced_input",
            "disposition": "blocked_input",
            "target": None,
            "barrier_ref": None,
            "call_class": "deterministic_zero_call",
            "capabilities": [],
            "allowed_events": ["run.blocked"],
        },
    }
    for raw_route in routes:
        route = _exact_keys(
            raw_route, required_fields, f"S route {raw_route.get('route_id')}"
        )
        for field in {
            "route_id",
            "predicate",
            "disposition",
            "call_class",
            "allowed_checkpoint_phase",
        }:
            _text(route[field], f"{route['route_id']}.{field}")
        if route["allowed_checkpoint_phase"] != "K0b-runtime-operational":
            raise RoutingError(
                f"S route is outside operational phase: {route['route_id']}"
            )
        if route["predecessor_seal_required"] is not False:
            raise RoutingError(
                f"pre-F15 S route unexpectedly requires a predecessor seal: {route['route_id']}"
            )
        _string_list(
            route["capabilities"], f"{route['route_id']}.capabilities", allow_empty=True
        )
        _string_list(
            route["allowed_events"],
            f"{route['route_id']}.allowed_events",
            allow_empty=True,
        )
        if any(event not in EXACT_EVENT_TYPES for event in route["allowed_events"]):
            raise RoutingError(f"S route emits an unknown event: {route['route_id']}")
        if route["call_class"] == "deterministic_zero_call" and route["capabilities"]:
            raise RoutingError(
                f"deterministic route has actor capabilities: {route['route_id']}"
            )
        if route["call_class"] not in {
            "deterministic_zero_call",
            "non_F15_physical_pre_seal",
        }:
            raise RoutingError(f"unknown S call class: {route['route_id']}")
        comparable = {
            name: route[name]
            for name in (
                "predicate",
                "disposition",
                "target",
                "barrier_ref",
                "call_class",
                "capabilities",
                "allowed_events",
            )
        }
        if comparable != exact_semantics[route["route_id"]]:
            raise RoutingError(f"S route semantics differ: {route['route_id']}")
    barriers = root["barriers"]
    if not isinstance(barriers, list) or len(barriers) != 1:
        raise RoutingError("F04 must have exactly one barrier")
    barrier = _exact_keys(
        barriers[0],
        {"barrier_id", "policy", "members", "deduplicate_by", "dynamic_membership"},
        "F04 barrier",
    )
    if barrier != {
        "barrier_id": "f04.alpha0.all_required.v1",
        "policy": "all_required",
        "members": [
            "fixture.alpha0.primary_reviewer",
            "fixture.alpha0.adversarial_reviewer",
        ],
        "deduplicate_by": "member_role_and_logical_result_identity",
        "dynamic_membership": False,
    }:
        raise RoutingError("F04 barrier membership or policy differs")
    if routes[2]["barrier_ref"] != barrier["barrier_id"] or any(
        route["barrier_ref"] is not None
        for index, route in enumerate(routes)
        if index != 2
    ):
        raise RoutingError(
            "F04 barrier reference is missing or attached to another route"
        )
    revision = _exact_keys(
        root["revision_owner_rule"],
        {
            "revision_owner_zero_role_id",
            "producer_invocation_id",
            "minimal_replay_required",
        },
        "revision owner rule",
    )
    if revision != {
        "revision_owner_zero_role_id": "fixture.alpha0.upstream_zero",
        "producer_invocation_id": "distinct_required_runtime_value",
        "minimal_replay_required": True,
    }:
        raise RoutingError("F05 revision owner/producer rule differs")
    freeze = _exact_keys(
        root["freeze_policy"],
        {"freeze_on", "terminal_outcomes", "resume_requires_same_bindings"},
        "route freeze policy",
    )
    _string_list(freeze["freeze_on"], "freeze_on", allow_empty=False)
    _string_list(freeze["terminal_outcomes"], "terminal_outcomes", allow_empty=False)
    if freeze["resume_requires_same_bindings"] is not True:
        raise RoutingError("route freeze resume can change bindings")
    return routes, {
        "barriers": barriers,
        "revision_owner_rule": revision,
        "freeze_policy": freeze,
    }


@dataclass(frozen=True)
class CompiledRegistryBundle:
    document: Mapping[str, Any]

    @property
    def aggregate_digest(self) -> str:
        return self.document["aggregate_digest"]

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json(self.document).encode("utf-8")


def compile_registry_bundle(
    bundle: ContractBundle | None = None,
) -> CompiledRegistryBundle:
    source = bundle if bundle is not None else load_contract_bundle()
    try:
        validate_policy(source.resource_policy)
        references = prove_reference_equivalence(
            source.reference_cases, source.resource_policy
        )
    except BudgetError as exc:
        raise CompilerError(str(exc)) from exc
    events, subscription_routes, reachability_edges = (
        _validate_event_and_subscription_profiles(source)
    )
    s_routes, fanout = _validate_routing_profile(source)
    reference_by_id = {item.case_id: item.result for item in references}
    try:
        k0b_forecast = reference_by_id["k0b-approved-two-phase-reference-v1"]
    except KeyError as exc:
        raise CompilerError("K0b reference forecast is missing") from exc
    outputs: dict[str, Any] = {
        "compiled_artifact_event_profile": {
            "profile": "Alpha0",
            "event_count": len(events),
            "events": events,
        },
        "compiled_event_reachability_graph": {
            "nodes": sorted(
                {edge["from"] for edge in reachability_edges}
                | {edge["to"] for edge in reachability_edges}
            ),
            "edges": sorted(
                reachability_edges, key=lambda edge: (edge["from"], edge["to"])
            ),
            "consumed_field_owners": [
                {
                    "event_type": event["event_type"],
                    "field": field,
                    "owner_schema_id": event["payload_schema_id"],
                    "owner_schema_sha256": event["payload_schema_sha256"],
                }
                for event in events
                for field in event["fields_consumed"]
            ],
        },
        "compiled_subscription_terminal_snapshot": {
            "routes": sorted(subscription_routes, key=lambda route: route["route_id"]),
            "f00_exception": source.subscription_profile["f00_exception"],
        },
        "compiled_s_route_table_v2": {
            "routes": s_routes,
            "phase_fence": "K0b-runtime-operational_before_terminal_seal",
            "physical_dispatch_authorized": False,
        },
        "compiled_fanout_barrier_profile": fanout,
        "compiled_resource_forecast": k0b_forecast,
        "compiled_checkpoint_phase_partition_v1": {
            "order": list(CHECKPOINT_PHASE_ORDER),
            "chronological": True,
            "contiguous": True,
            "non_overlapping": True,
            "exhaustive": True,
            "immutable_before_first_effect": True,
            "membership": source.resource_policy["k0b_work_item_membership"],
            "call_allocation": source.resource_policy["k0b_call_allocation"],
            "f15_boundary_trigger_ids": list(F15_TRIGGER_IDS),
        },
        "compiled_checkpoint_publication_budget_v2": {
            "checkpoint_policy": source.resource_policy["checkpoint"],
            "phase_forecasts": k0b_forecast["checkpoint_phases"],
            "f15_publication_limits": source.resource_policy["f15_publication_limits"],
            "runtime_phase_activation": False,
        },
    }
    if tuple(outputs) != REQUIRED_OUTPUT_FAMILIES:
        raise CompilerError("compiled output family order differs")
    output_hashes = {name: sha256_json(value) for name, value in outputs.items()}
    compiler_hashes = {
        "registry_routing_sha256": sha256(COMPILER_PATH.read_bytes()).hexdigest(),
        "resource_budget_sha256": sha256(
            RESOURCE_COMPILER_PATH.read_bytes()
        ).hexdigest(),
    }
    digest_payload = {
        "compiler_id": COMPILER_ID,
        "compiler_version": COMPILER_VERSION,
        "compiler_hashes": compiler_hashes,
        "source_hashes": dict(source.source_hashes),
        "output_hashes": output_hashes,
    }
    document = {
        "compiler_id": COMPILER_ID,
        "compiler_version": COMPILER_VERSION,
        "compiler_hashes": compiler_hashes,
        "source_hashes": dict(source.source_hashes),
        "outputs": outputs,
        "output_hashes": output_hashes,
        "aggregate_digest": sha256_json(digest_payload),
    }
    return CompiledRegistryBundle(document=document)


def compile_registry_bytes(bundle: ContractBundle | None = None) -> bytes:
    return compile_registry_bundle(bundle).canonical_bytes
