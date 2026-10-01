from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class LifecycleError(ValueError):
    pass


@dataclass(frozen=True)
class Intent:
    effect_id: str
    state: str
    cancellable: bool
    result_known: bool


RUNNING_STATES = {"running", "waiting"}
TERMINAL_STATES = {"completed", "aborted", "blocked"}


def request_abort(run_state: str, revision_matches: bool) -> str:
    if not revision_matches:
        raise LifecycleError("stale revision")
    if run_state not in RUNNING_STATES:
        raise LifecycleError("abort is admitted only from running or waiting")
    return "aborting"


def reconcile_abort(intents: Iterable[Intent]) -> dict[str, object]:
    unknown: list[str] = []
    cancellable: list[str] = []
    completed: list[str] = []
    for intent in sorted(intents, key=lambda item: item.effect_id):
        if intent.state == "completed" and intent.result_known:
            completed.append(intent.effect_id)
        elif intent.cancellable and intent.state in {"prepared", "started"}:
            cancellable.append(intent.effect_id)
        elif not intent.result_known or intent.state not in {"prepared", "started", "completed", "blocked", "quarantined"}:
            unknown.append(intent.effect_id)
    if unknown:
        return {"terminal_state": "blocked", "code": "UNKNOWN_EFFECT_STATE", "unknown_effect_ids": unknown, "retry": False}
    return {"terminal_state": "aborted", "code": "CONSISTENT_ABORT", "cancel_effect_ids": cancellable, "completed_effect_ids": completed, "retry": False}


def security_policy_route(confirmed_leakage: bool) -> dict[str, object]:
    if confirmed_leakage:
        return {"event": "meta.incident_detected", "terminal_policy": "persist_incident_and_enqueue_W5", "publisher_frozen": True, "raw_material_persisted": False}
    return {"event": "error.security_policy", "terminal_policy": "block_run_and_enqueue_human", "publisher_frozen": False, "raw_material_persisted": False}


def admit_resume(pins_identical: bool, schema_compatible: bool, unknown_effects: bool) -> dict[str, object]:
    admitted = pins_identical and schema_compatible and not unknown_effects
    return {"result": "admissible_for_next_guard" if admitted else "blocked", "authorized": False, "retry": False}
