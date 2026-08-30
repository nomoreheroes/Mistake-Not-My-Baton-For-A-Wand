"""Harness-controlled adapter boundary and scripted-only K0a-02 test adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Mapping, Protocol, Sequence
import time

from .contract import PinnedContractPackage, canonical_json, sha256_text


RETRIABLE_FAILURES = {
    "transient_unavailable_before_dispatch_ack",
    "timeout_before_accepted_response",
}


class AdapterError(RuntimeError):
    """A scripted physical attempt failed before an accepted response."""

    def __init__(self, failure_code: str):
        if failure_code not in RETRIABLE_FAILURES | {"non_retriable_provider_failure"}:
            raise ValueError("unknown adapter failure code")
        super().__init__(failure_code)
        self.failure_code = failure_code


@dataclass(frozen=True)
class AdapterRequest:
    role: str
    invocation_id: str
    delivery_id: str
    run_id: str
    attempt_number: int
    triggering_event_id: str
    context_text: str
    context_sha256: str
    prompt_id: str
    prompt_version: str
    prompt_sha256: str
    contract_id: str
    contract_version: str
    contract_sha256: str
    result_schema_id: str
    result_schema_version: str
    result_schema_sha256: str
    package_sha256: str
    provider: str
    model_profile: str
    model_identifier: str
    parameters: Mapping[str, object]
    capabilities: Mapping[str, object]


@dataclass(frozen=True)
class AdapterReceipt:
    response_text: str
    response_sha256: str
    started_at: str
    completed_at: str
    duration_ms: int
    monotonic_started_ns: int
    monotonic_completed_ns: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    usage: Mapping[str, int]
    finish_reason: str


class ModelAdapter(Protocol):
    """Actors receive only this immutable envelope, never harness capabilities."""

    runtime_model_invocations: int
    network_calls: int

    def dispatch(self, request: AdapterRequest) -> AdapterReceipt:
        """Return one response or a typed pre-acceptance failure."""


Script = str | AdapterError | Callable[[AdapterRequest], str]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ScriptedAdapter:
    """No-network fake. It cannot perform a provider/model invocation."""

    runtime_model_invocations = 0
    network_calls = 0

    def __init__(
        self,
        scripts: Mapping[str, Sequence[Script]],
        *,
        on_dispatch: Callable[[AdapterRequest], None] | None = None,
    ) -> None:
        self._scripts = {role: list(items) for role, items in scripts.items()}
        self.on_dispatch = on_dispatch
        self.requests: list[AdapterRequest] = []

    def dispatch(self, request: AdapterRequest) -> AdapterReceipt:
        if self.on_dispatch is not None:
            self.on_dispatch(request)
        self.requests.append(request)
        queue = self._scripts.get(request.role)
        if not queue:
            raise AdapterError("non_retriable_provider_failure")
        script = queue.pop(0)
        if isinstance(script, AdapterError):
            raise script
        started_ns = time.monotonic_ns()
        started_at = _utc_now()
        response_text = script(request) if callable(script) else script
        completed_ns = time.monotonic_ns()
        if completed_ns == started_ns:
            completed_ns += 1
        completed_at = _utc_now()
        input_tokens = max(1, len(request.context_text.encode("utf-8")) // 4)
        output_tokens = max(1, len(response_text.encode("utf-8")) // 4)
        total_tokens = input_tokens + output_tokens
        return AdapterReceipt(
            response_text=response_text,
            response_sha256=sha256_text(response_text),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=(completed_ns - started_ns) // 1_000_000,
            monotonic_started_ns=started_ns,
            monotonic_completed_ns=completed_ns,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            finish_reason="scripted_fixture",
        )

    @classmethod
    def nominal(
        cls,
        package: PinnedContractPackage,
        *,
        result_text: str = "synthetic fixture result",
        on_dispatch: Callable[[AdapterRequest], None] | None = None,
        first_failures: Mapping[str, str] | None = None,
    ) -> ScriptedAdapter:
        result_schema = package.schema_identity("bootstrap_synthetic_result")

        def s0(request: AdapterRequest) -> str:
            return canonical_json(
                {
                    "action": "invoke",
                    "invocation_id": request.invocation_id,
                    "route": "synthetic_Layer0",
                    "run_id": request.run_id,
                    "triggering_event_id": request.triggering_event_id,
                    "type": "s0_route_proposal",
                }
            )

        def layer0(request: AdapterRequest) -> str:
            return canonical_json(
                {
                    "action": "invoke",
                    "invocation_id": request.invocation_id,
                    "route": "fixture_worker",
                    "run_id": request.run_id,
                    "triggering_event_id": request.triggering_event_id,
                    "type": "synthetic_layer0_invocation_proposal",
                }
            )

        def worker(request: AdapterRequest) -> str:
            return canonical_json(
                {
                    "action": "publish",
                    "artifact_type": "bootstrap.synthetic_result",
                    "content_sha256": sha256_text(result_text),
                    "content_text": result_text,
                    "invocation_id": request.invocation_id,
                    "logical_owner": "fixture.bootstrap_worker",
                    "media_type": "text/plain",
                    "parent_ref": "fixture:seed:request.yaml",
                    "result_schema_id": result_schema.id,
                    "result_schema_sha256": result_schema.sha256,
                    "result_schema_version": result_schema.version,
                    "run_id": request.run_id,
                    "triggering_event_id": request.triggering_event_id,
                    "type": "fixture_worker_publication_proposal",
                }
            )

        scripts: dict[str, list[Script]] = {
            "S0": [s0],
            "synthetic_Layer0": [layer0],
            "fixture_worker": [worker],
        }
        for role, failure_code in (first_failures or {}).items():
            if role not in scripts:
                raise ValueError(f"unknown scripted role {role!r}")
            scripts[role].insert(0, AdapterError(failure_code))
        return cls(scripts, on_dispatch=on_dispatch)
