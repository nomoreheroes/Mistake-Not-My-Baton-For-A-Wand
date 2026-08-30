"""Minimal fixture-only K0a-02 orchestration service.

The service performs no real F00/model execution.  Its adapter boundary is
exercised only with scripted/fake adapters until K0a-03 is separately allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import os
from pathlib import Path
import platform
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from harness.k0a01 import ArtifactPublication, InvocationSpec, InvocationTelemetry, LineageRef, ReplayPoint
from .adapters import AdapterError, AdapterRequest, ModelAdapter
from .contract import (
    ContractValidationError,
    PinnedContractPackage,
    ResponseIdentity,
    canonical_json,
    load_contract_package,
    sha256_text,
)
from .guards import CANONICAL_FIXTURE_ROOT, PIPELINE_ROOT, GuardProof, RootGuard
from .security import SensitiveDataError, scan_untrusted_text
from .store import K0a02Store, SinkAcceptance


class OrchestrationError(RuntimeError):
    """The scripted K0a-02 route stopped fail-closed."""


class Clock(Protocol):
    def now(self) -> str:
        """Return an explicit UTC RFC3339 timestamp."""


class SystemClock:
    def now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class IdSource(Protocol):
    def new(self, label: str) -> str:
        """Return a non-empty identity unique within one disposable DB."""


class RandomIds:
    def new(self, label: str) -> str:
        return f"{label}-{uuid4().hex}"


class Guard(Protocol):
    def validate(
        self,
        *,
        pipeline_root: Path,
        canonical_fixture_root: Path,
        runtime_root: Path,
        expected_pipeline_commit: str | None = None,
    ) -> GuardProof:
        """Return a complete exact-root proof or raise."""


@dataclass(frozen=True)
class RuntimeBinding:
    runtime_root: Path
    database_path: Path
    guard_proof: GuardProof


@dataclass(frozen=True)
class RunResult:
    run_id: str
    state_revision: int
    artifact_version_id: str
    sink_acceptance_id: str
    readback_gate_id: str
    inspect: Mapping[str, Any]
    runtime_model_invocations: int
    network_calls: int


class BootstrapSink:
    """Deterministic exact F00 terminal sink; it never mutates content."""

    def __init__(self, package: PinnedContractPackage, store: K0a02Store) -> None:
        self.package = package
        self.store = store

    def accept(
        self,
        request: Mapping[str, Any],
        *,
        sink_acceptance_id: str,
        accepted_at: str,
    ) -> str:
        self.package.validate("bootstrap_sink_acceptance", request)
        scan_untrusted_text(request["content_text"], label="sink candidate artifact")
        if sha256_text(request["content_text"]) != request["content_sha256"]:
            raise ContractValidationError("sink request content hash does not match exact text")
        bundle = self.store.sink_bundle(request["handoff_event_id"])
        expected = {
            "artifact_version_id": bundle["artifact_version_id"],
            "content_sha256": bundle["content_sha256"],
            "content_text": bundle["content_text"],
            "handoff_event_id": bundle["event_id"],
            "media_type": bundle["media_type"],
            "profile": bundle["payload"]["profile"],
            "run_id": bundle["run_id"],
        }
        if any(request[name] != value for name, value in expected.items()):
            raise ContractValidationError("sink profile/ref/hash/content differs from persisted handoff")
        if request["accepted"] is not True or request["type"] != "bootstrap_sink_acceptance":
            raise ContractValidationError("sink request is not an exact acceptance")
        artifact = self.package.artifact_profile
        if (
            bundle["event_type"] != "handoff.ready"
            or bundle["subscriber_id"] != "bootstrap_sink"
            or bundle["terminal_policy"] != "fixture_terminal"
            or bundle["delivery_state"] != "pending"
            or bundle["artifact_type"] != artifact["artifact_type"]
            or bundle["logical_owner"] != artifact["logical_owner"]
            or bundle["schema_id"] != self.package.schema_identity(artifact["schema_ref"]).id
            or bundle["schema_version"] != self.package.schema_identity(artifact["schema_ref"]).version
            or bundle["schema_sha256"] != self.package.schema_identity(artifact["schema_ref"]).sha256
        ):
            raise ContractValidationError("sink referenced artifact owner/media/schema is not pinned")
        self.store.accept_sink(
            SinkAcceptance(
                sink_acceptance_id=sink_acceptance_id,
                run_id=request["run_id"],
                event_delivery_id=bundle["event_delivery_id"],
                handoff_event_id=request["handoff_event_id"],
                artifact_version_id=request["artifact_version_id"],
                profile=request["profile"],
                artifact_type=bundle["artifact_type"],
                logical_owner=bundle["logical_owner"],
                media_type=request["media_type"],
                content_text=request["content_text"],
                content_sha256=request["content_sha256"],
                accepted_at=accepted_at,
            )
        )
        return sink_acceptance_id


class K0a02Harness:
    """One command -> S0 -> Layer0 -> worker -> sink/readback route."""

    def __init__(
        self,
        adapter: ModelAdapter,
        *,
        package: PinnedContractPackage | None = None,
        guard: Guard | None = None,
        clock: Clock | None = None,
        ids: IdSource | None = None,
        pipeline_root: Path = PIPELINE_ROOT,
        canonical_fixture_root: Path = CANONICAL_FIXTURE_ROOT,
    ) -> None:
        self.package = package or load_contract_package()
        self.adapter = adapter
        self.guard = guard or RootGuard(self.package)
        self.clock = clock or SystemClock()
        self.ids = ids or RandomIds()
        self.pipeline_root = pipeline_root.absolute()
        self.canonical_fixture_root = canonical_fixture_root.absolute()
        self._replay_sequence = 0

    def _guard(self, runtime_root: Path, expected_pipeline_commit: str | None) -> GuardProof:
        return self.guard.validate(
            pipeline_root=self.pipeline_root,
            canonical_fixture_root=self.canonical_fixture_root,
            runtime_root=runtime_root,
            expected_pipeline_commit=expected_pipeline_commit,
        )

    @staticmethod
    def _runtime_database_path(runtime_root: Path) -> Path:
        return runtime_root / ".pipeline" / "runtime" / "pipeline.sqlite3"

    @staticmethod
    def _is_link_like(path: Path) -> bool:
        is_junction = getattr(path, "is_junction", None)
        return path.is_symlink() or (is_junction is not None and is_junction())

    @classmethod
    def _require_exact_directory(cls, path: Path, label: str) -> None:
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise OrchestrationError(f"{label} is missing") from exc
        if (
            cls._is_link_like(path)
            or not path.is_dir()
            or os.path.normcase(str(resolved)) != os.path.normcase(str(path.absolute()))
        ):
            raise OrchestrationError(f"{label} is a symlink/junction or escapes the runtime root")

    @classmethod
    def _require_runtime_storage(cls, runtime_root: Path, *, create: bool) -> Path:
        metadata_directory = runtime_root / ".pipeline"
        runtime_directory = metadata_directory / "runtime"
        for directory, label in (
            (metadata_directory, "runtime metadata directory"),
            (runtime_directory, "runtime database directory"),
        ):
            if not directory.exists():
                if cls._is_link_like(directory):
                    raise OrchestrationError(f"{label} is a broken symlink/junction")
                if not create:
                    raise OrchestrationError(f"{label} is missing")
                directory.mkdir()
            cls._require_exact_directory(directory, label)
        return cls._runtime_database_path(runtime_root)

    def initialize(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> RuntimeBinding:
        runtime_root = runtime_root.absolute()
        proof = self._guard(runtime_root, expected_pipeline_commit)
        runtime_root = proof.runtime_fixture.root
        db_path = self._require_runtime_storage(runtime_root, create=True)
        K0a02Store(db_path).initialize()
        return RuntimeBinding(runtime_root, db_path, proof)

    def _open(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> tuple[RuntimeBinding, K0a02Store]:
        runtime_root = runtime_root.absolute()
        proof = self._guard(runtime_root, expected_pipeline_commit)
        runtime_root = proof.runtime_fixture.root
        db_path = self._require_runtime_storage(runtime_root, create=False)
        if (
            not db_path.is_file()
            or self._is_link_like(db_path)
            or os.path.normcase(str(db_path.resolve(strict=True)))
            != os.path.normcase(str(db_path.absolute()))
        ):
            raise OrchestrationError("runtime is not initialized at the exact fixed SQLite path")
        store = K0a02Store(db_path)
        store.initialize()
        return RuntimeBinding(runtime_root, db_path, proof), store

    @staticmethod
    def _fixture_input(runtime_root: Path) -> str:
        path = runtime_root / "fixture" / "request.yaml"
        if path.is_symlink() or path.resolve(strict=True) != path:
            raise OrchestrationError("fixed fixture input is a symlink/junction")
        payload = path.read_bytes()
        if len(payload) > 4096 or payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
            raise OrchestrationError("fixed fixture input violates textual bounds")
        try:
            return payload.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise OrchestrationError("fixed fixture input is not strict UTF-8") from exc

    def _environment(self) -> Mapping[str, Any]:
        migration_hash = sha256(
            (Path(__file__).resolve().parent.parent / "migrations" / "0002_k0a02.sql").read_bytes()
        ).hexdigest()
        return {
            "adapter_version": "k0a02-scripted-adapter-v1",
            "architecture": platform.machine() or "unknown",
            "clock_binding": "monotonic_ns",
            "config_sha256": self.package.complete_file_sha256,
            "dependency_lock_sha256": migration_hash,
            "harness_version": "k0a02-v1",
            "locale": "C",
            "os": platform.system() or "unknown",
            "random_seed": None,
            "timezone": "UTC",
            "tool_registry_version": "none-v1",
        }

    def _capability_snapshot(self) -> Mapping[str, Any]:
        capabilities = self.package.capability_profile
        return {
            "filesystem_roots": [],
            "model_channel": capabilities["model_channel"],
            "policy_version": capabilities["policy_version"],
            "tools": [],
        }

    @staticmethod
    def _fragments(*, system: str, developer: Mapping[str, Any], user: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
        values = (("system", system), ("developer", canonical_json(developer)), ("user", canonical_json(user)))
        return tuple(
            {
                "content_sha256": sha256_text(content),
                "content_text": content,
                "ordinal": ordinal,
                "role": role,
            }
            for ordinal, (role, content) in enumerate(values)
        )

    def _context(self, role: str, actor_input: Mapping[str, Any]) -> tuple[str, tuple[Mapping[str, Any], ...]]:
        actor = self.package.actor(role)
        actor_input = self.package.validate_actor_input(role, actor_input)
        if role == "fixture_worker" and sha256_text(
            actor_input["fixture_input"]["content_text"]
        ) != actor_input["fixture_input"]["content_sha256"]:
            raise ContractValidationError("fixture worker input content hash is wrong")
        prompt = self.package.prompt(role)
        fragments = self._fragments(
            system=prompt["text"],
            developer={
                "allowed_action": actor["allowed_action"],
                "allowed_output_type": actor["allowed_output_type"],
                "allowed_route": actor["allowed_route"],
                "capability_summary": self._capability_snapshot(),
                "contract_sha256": actor["contract_sha256"],
                "package_sha256": self.package.complete_file_sha256,
                "profile": "F00",
            },
            user={"input": actor_input, "trust": "untrusted_content"},
        )
        return canonical_json(fragments), fragments

    def _next_replay_sequence(self) -> int:
        value = self._replay_sequence
        self._replay_sequence += 1
        return value

    def _fail_run(
        self,
        store: K0a02Store,
        *,
        run_id: str,
        revision: int,
        state: str,
    ) -> None:
        store.transition_run(
            run_id=run_id,
            expected_state="running",
            expected_revision=revision,
            new_state=state,
            transition_id=self.ids.new(f"{run_id}-{state}"),
            occurred_at=self.clock.now(),
        )

    def _invoke(
        self,
        store: K0a02Store,
        *,
        run_id: str,
        role: str,
        delivery_id: str,
        triggering_event_id: str,
        actor_input: Mapping[str, Any],
        run_revision: int,
        on_first_invocation_created: Callable[[str], None] | None = None,
    ) -> tuple[str, str, Mapping[str, Any]]:
        prompt = self.package.prompt_identity(role)
        contract = self.package.actor_contract_identity(role)
        result_schema = self.package.result_schema_identity(role)
        model = self.package.model_profile
        context_text, fragments = self._context(role, actor_input)
        try:
            scan_untrusted_text(context_text, label=f"{role} rendered context")
        except SensitiveDataError as exc:
            self._fail_run(store, run_id=run_id, revision=run_revision, state="blocked_policy")
            raise OrchestrationError(f"{role} context failed secret/PII policy") from exc
        context_hash = sha256_text(context_text)
        proposal_id = self.ids.new(f"{role}-proposal")
        last_error: AdapterError | None = None
        store.create_delivery(
            delivery_id=delivery_id,
            run_id=run_id,
            delivery_key=f"{run_id}:{role}",
            role=role,
            triggering_event_id=triggering_event_id,
            created_at=self.clock.now(),
        )
        for attempt in (1, 2):
            invocation_id = self.ids.new(f"{role}-invocation-{attempt}")
            spec = InvocationSpec(
                invocation_id=invocation_id,
                delivery_id=delivery_id,
                attempt_number=attempt,
                prompt_id=prompt.id,
                prompt_version=prompt.version,
                prompt_sha256=prompt.sha256,
                contract_id=contract.id,
                contract_version=contract.version,
                contract_sha256=contract.sha256,
                result_schema_id=result_schema.id,
                result_schema_version=result_schema.version,
                result_schema_sha256=result_schema.sha256,
                registry_sha256=self.package.complete_file_sha256,
                provider=model["provider"],
                model_profile=model["model_profile"],
                model_identifier=model["model_identifier"],
                parameters=model["parameters"],
                context_limit_tokens=model["context_limit_tokens"],
                created_at=self.clock.now(),
            )
            store.create_invocation(spec)
            if attempt == 1 and on_first_invocation_created is not None:
                on_first_invocation_created(invocation_id)
            store.record_replay_point(
                ReplayPoint(
                    replay_point_id=self.ids.new(f"{invocation_id}-before"),
                    invocation_id=invocation_id,
                    position="before",
                    sequence_number=self._next_replay_sequence(),
                    context_text=context_text,
                    context_sha256=context_hash,
                    context_fragments=fragments,
                    capabilities=self._capability_snapshot(),
                    environment=self._environment(),
                    capture_completeness="complete_harness_visible",
                    gap_code=None,
                    created_at=self.clock.now(),
                )
            )
            store.transition_invocation(
                invocation_id=invocation_id,
                expected_state="replay_before_committed",
                new_state="dispatched",
                transition_id=self.ids.new(f"{invocation_id}-dispatched"),
                occurred_at=self.clock.now(),
            )
            request = AdapterRequest(
                role=role,
                invocation_id=invocation_id,
                delivery_id=delivery_id,
                run_id=run_id,
                attempt_number=attempt,
                triggering_event_id=triggering_event_id,
                context_text=context_text,
                context_sha256=context_hash,
                prompt_id=prompt.id,
                prompt_version=prompt.version,
                prompt_sha256=prompt.sha256,
                contract_id=contract.id,
                contract_version=contract.version,
                contract_sha256=contract.sha256,
                result_schema_id=result_schema.id,
                result_schema_version=result_schema.version,
                result_schema_sha256=result_schema.sha256,
                package_sha256=self.package.complete_file_sha256,
                provider=model["provider"],
                model_profile=model["model_profile"],
                model_identifier=model["model_identifier"],
                parameters=model["parameters"],
                capabilities=self.package.capability_profile,
            )
            try:
                receipt = self.adapter.dispatch(request)
            except AdapterError as exc:
                last_error = exc
                store.record_invocation_failure(
                    invocation_id=invocation_id,
                    failure_code=exc.failure_code,
                    transition_id=self.ids.new(f"{invocation_id}-failed"),
                    occurred_at=self.clock.now(),
                )
                if attempt == 1 and exc.failure_code in {
                    "transient_unavailable_before_dispatch_ack",
                    "timeout_before_accepted_response",
                }:
                    continue
                self._fail_run(
                    store,
                    run_id=run_id,
                    revision=run_revision,
                    state="failed_invocation",
                )
                raise OrchestrationError(f"{role} scripted adapter failure: {exc.failure_code}") from exc

            try:
                scan_untrusted_text(receipt.response_text, label=f"{role} adapter response")
            except SensitiveDataError as exc:
                store.record_invocation_failure(
                    invocation_id=invocation_id,
                    failure_code="non_retriable_provider_failure",
                    transition_id=self.ids.new(f"{invocation_id}-sensitive-response"),
                    occurred_at=self.clock.now(),
                )
                self._fail_run(store, run_id=run_id, revision=run_revision, state="blocked_policy")
                raise OrchestrationError(f"{role} response failed secret/PII policy") from exc
            try:
                parsed = self.package.validate_response(
                    role,
                    receipt.response_text,
                    ResponseIdentity(invocation_id, run_id, triggering_event_id),
                )
                accepted = True
            except ContractValidationError as exc:
                parsed = {}
                accepted = False
                validation_error = exc
            store.record_telemetry(
                InvocationTelemetry(
                    telemetry_id=self.ids.new(f"{invocation_id}-telemetry"),
                    invocation_id=invocation_id,
                    provider=request.provider,
                    model_profile=request.model_profile,
                    model_identifier=request.model_identifier,
                    parameters=request.parameters,
                    response_text=receipt.response_text,
                    response_sha256=receipt.response_sha256,
                    started_at=receipt.started_at,
                    completed_at=receipt.completed_at,
                    duration_ms=receipt.duration_ms,
                    monotonic_started_ns=receipt.monotonic_started_ns,
                    monotonic_completed_ns=receipt.monotonic_completed_ns,
                    input_tokens=receipt.input_tokens,
                    output_tokens=receipt.output_tokens,
                    total_tokens=receipt.total_tokens,
                    usage=receipt.usage,
                    finish_reason=receipt.finish_reason,
                )
            )
            store.transition_invocation(
                invocation_id=invocation_id,
                expected_state="response_captured",
                new_state="validated",
                transition_id=self.ids.new(f"{invocation_id}-schema-checked"),
                occurred_at=self.clock.now(),
            )
            store.record_replay_point(
                ReplayPoint(
                    replay_point_id=self.ids.new(f"{invocation_id}-after"),
                    invocation_id=invocation_id,
                    position="after",
                    sequence_number=self._next_replay_sequence(),
                    context_text=context_text,
                    context_sha256=context_hash,
                    context_fragments=fragments,
                    capabilities=self._capability_snapshot(),
                    environment=self._environment(),
                    capture_completeness="complete_harness_visible",
                    gap_code=None,
                    created_at=self.clock.now(),
                )
            )
            if role == "S0":
                store.record_s0_route_validation(
                    proposal_id=proposal_id,
                    invocation_id=invocation_id,
                    accepted=accepted,
                    created_at=self.clock.now(),
                )
            else:
                store.record_actor_proposal(
                    proposal_id=proposal_id,
                    invocation_id=invocation_id,
                    accepted=accepted,
                    created_at=self.clock.now(),
                )
            if not accepted:
                self._fail_run(
                    store,
                    run_id=run_id,
                    revision=run_revision,
                    state="failed_validation",
                )
                raise OrchestrationError(f"{role} response failed exact validation") from validation_error
            return invocation_id, proposal_id, parsed
        assert last_error is not None
        raise OrchestrationError(f"{role} exhausted its pinned retry") from last_error

    def run(
        self,
        runtime_root: Path,
        command: Mapping[str, Any],
        *,
        expected_pipeline_commit: str | None = None,
    ) -> RunResult:
        command = self.package.validate_normalized_command(command)
        binding, store = self._open(
            runtime_root, expected_pipeline_commit=expected_pipeline_commit
        )
        if store.count_rows("runs") != 0:
            raise OrchestrationError("the disposable K0a-02 runtime already contains a run")
        self._replay_sequence = 0
        run_id = self.ids.new("run")
        correlation_id = self.ids.new("correlation")
        command_event_id = self.ids.new("event-command")
        started_event_id = self.ids.new("event-started")
        event_schema = self.package.schema_identity("f00_event_envelope")
        command_payload = {
            "command": command["command"],
            "contract_package_sha256": self.package.complete_file_sha256,
            "profile": command["profile"],
            "run_id": run_id,
        }
        started_payload = {"run_id": run_id, "state": "running"}
        self.package.validate("event_command_received", command_payload)
        self.package.validate("event_run_started", started_payload)

        store.create_run(
            run_id=run_id,
            pipeline_commit=binding.guard_proof.pipeline.commit,
            fixture_commit=binding.guard_proof.runtime_fixture.commit,
            fixture_tree=binding.guard_proof.runtime_fixture.tree,
            created_at=self.clock.now(),
        )
        revision = store.transition_run(
            run_id=run_id,
            expected_state="created",
            expected_revision=0,
            new_state="running",
            transition_id=self.ids.new("run-started-transition"),
            occurred_at=self.clock.now(),
        )
        store.append_control_event(
            event_id=command_event_id,
            run_id=run_id,
            event_type="command.received",
            caused_by_event_id=None,
            correlation_id=correlation_id,
            schema_id=event_schema.id,
            schema_version=event_schema.version,
            schema_sha256=event_schema.sha256,
            payload=command_payload,
            idempotency_key=f"{run_id}:command.received",
            created_at=self.clock.now(),
        )
        store.append_control_event(
            event_id=started_event_id,
            run_id=run_id,
            event_type="run.started",
            caused_by_event_id=command_event_id,
            correlation_id=correlation_id,
            schema_id=event_schema.id,
            schema_version=event_schema.version,
            schema_sha256=event_schema.sha256,
            payload=started_payload,
            idempotency_key=f"{run_id}:run.started",
            created_at=self.clock.now(),
        )

        s0_delivery = self.ids.new("delivery-s0")
        s0_invocation, s0_proposal, _ = self._invoke(
            store,
            run_id=run_id,
            role="S0",
            delivery_id=s0_delivery,
            triggering_event_id=command_event_id,
            actor_input=command,
            run_revision=revision,
        )
        validated_route = {
            "action": "invoke",
            "route": "synthetic_Layer0",
            "run_id": run_id,
            "source_invocation_id": s0_invocation,
            "source_proposal_id": s0_proposal,
            "triggering_event_id": command_event_id,
            "type": "validated_route_proposal",
        }
        self.package.validate("validated_route_proposal", validated_route)
        layer0_delivery = self.ids.new("delivery-layer0")
        layer0_invocation, layer0_proposal, layer0_result = self._invoke(
            store,
            run_id=run_id,
            role="synthetic_Layer0",
            delivery_id=layer0_delivery,
            triggering_event_id=command_event_id,
            actor_input=validated_route,
            run_revision=revision,
            on_first_invocation_created=lambda downstream: store.consume_s0_route(
                consumption_id=self.ids.new("s0-route-consumption"),
                proposal_id=s0_proposal,
                downstream_invocation_id=downstream,
                created_at=self.clock.now(),
            ),
        )
        fixture_input = self._fixture_input(binding.runtime_root)
        worker_input = {
            "fixture_input": {
                "content_sha256": sha256_text(fixture_input),
                "content_text": fixture_input,
                "ref": "fixture:seed:request.yaml",
            },
            "layer0_proposal": layer0_result,
        }
        worker_delivery = self.ids.new("delivery-worker")
        worker_invocation, _worker_proposal, worker_result = self._invoke(
            store,
            run_id=run_id,
            role="fixture_worker",
            delivery_id=worker_delivery,
            triggering_event_id=started_event_id,
            actor_input=worker_input,
            run_revision=revision,
            on_first_invocation_created=lambda downstream: store.consume_actor_proposal(
                consumption_id=self.ids.new("layer0-proposal-consumption"),
                proposal_id=layer0_proposal,
                downstream_invocation_id=downstream,
                created_at=self.clock.now(),
            ),
        )
        artifact_id = self.ids.new("artifact")
        artifact_version_id = self.ids.new("artifact-version")
        version_event_id = self.ids.new("event-version-created")
        handoff_event_id = self.ids.new("event-handoff")
        result_schema = self.package.schema_identity("bootstrap_synthetic_result")
        version_payload = {
            "artifact_type": "bootstrap.synthetic_result",
            "artifact_version_id": artifact_version_id,
            "content_sha256": worker_result["content_sha256"],
        }
        handoff_payload = {"artifact_version_id": artifact_version_id, "profile": "F00"}
        self.package.validate("event_artifact_version_created", version_payload)
        self.package.validate("event_handoff_ready", handoff_payload)
        publication = store.publish_artifact_version(
            ArtifactPublication(
                publication_transaction_id=self.ids.new("publication"),
                idempotency_key=f"{run_id}:publication",
                run_id=run_id,
                expected_run_revision=revision,
                invocation_id=worker_invocation,
                artifact_id=artifact_id,
                artifact_version_id=artifact_version_id,
                content_text=worker_result["content_text"],
                content_sha256=worker_result["content_sha256"],
                media_type=worker_result["media_type"],
                schema_id=result_schema.id,
                schema_version=result_schema.version,
                schema_sha256=result_schema.sha256,
                correlation_id=correlation_id,
                caused_by_event_id=started_event_id,
                version_created_event_id=version_event_id,
                version_created_idempotency_key=f"{run_id}:artifact.version_created",
                handoff_event_id=handoff_event_id,
                handoff_idempotency_key=f"{run_id}:handoff.ready",
                event_schema_id=event_schema.id,
                event_schema_version=event_schema.version,
                event_schema_sha256=event_schema.sha256,
                lineage=(
                    LineageRef(
                        lineage_id=self.ids.new("lineage"),
                        parent_ref_kind="fixture_input",
                        parent_external_ref=worker_result["parent_ref"],
                        relation="produced_from",
                    ),
                ),
                created_at=self.clock.now(),
            )
        )
        revision = publication.committed_run_revision
        sink_id = self.ids.new("sink-acceptance")
        sink_request = {
            "accepted": True,
            "artifact_version_id": artifact_version_id,
            "content_sha256": worker_result["content_sha256"],
            "content_text": worker_result["content_text"],
            "handoff_event_id": handoff_event_id,
            "media_type": worker_result["media_type"],
            "profile": "F00",
            "run_id": run_id,
            "type": "bootstrap_sink_acceptance",
        }
        BootstrapSink(self.package, store).accept(
            sink_request,
            sink_acceptance_id=sink_id,
            accepted_at=self.clock.now(),
        )
        gate_id = self.ids.new("readback-gate")
        store.create_readback_gate(
            readback_gate_id=gate_id,
            run_id=run_id,
            checked_at=self.clock.now(),
        )
        completed_payload = {
            "readback_gate_id": gate_id,
            "run_id": run_id,
            "sink_acceptance_id": sink_id,
            "state": "completed",
        }
        self.package.validate("event_run_completed", completed_payload)
        revision = store.complete_run(
            run_id=run_id,
            expected_revision=revision,
            event_id=self.ids.new("event-completed"),
            correlation_id=correlation_id,
            schema_id=event_schema.id,
            schema_version=event_schema.version,
            schema_sha256=event_schema.sha256,
            idempotency_key=f"{run_id}:run.completed",
            occurred_at=self.clock.now(),
        )
        inspect = store.inspect(run_id)
        self.package.validate("inspect_readback", inspect)
        if inspect["run"]["state"] != "completed":
            raise OrchestrationError("final inspect did not observe completed state")
        return RunResult(
            run_id=run_id,
            state_revision=revision,
            artifact_version_id=artifact_version_id,
            sink_acceptance_id=sink_id,
            readback_gate_id=gate_id,
            inspect=inspect,
            runtime_model_invocations=self.adapter.runtime_model_invocations,
            network_calls=self.adapter.network_calls,
        )

    def inspect(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> Mapping[str, Any]:
        _, store = self._open(runtime_root, expected_pipeline_commit=expected_pipeline_commit)
        result = store.inspect()
        self.package.validate("inspect_readback", result)
        return result
