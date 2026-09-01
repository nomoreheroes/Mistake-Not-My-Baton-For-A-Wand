"""Resumable K0a-03 manual handoff orchestration for VS Code extensions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
from typing import Any, Mapping

from harness.k0a01 import ArtifactPublication, InvocationSpec, InvocationTelemetry, LineageRef, ReplayPoint
from harness.k0a02.contract import (
    ContractValidationError,
    ResponseIdentity,
    canonical_json,
    load_contract_package,
    sha256_text,
)
from harness.k0a02.guards import CANONICAL_FIXTURE_ROOT, PIPELINE_ROOT, RootGuard
from harness.k0a02.orchestrator import (
    BootstrapSink,
    Clock,
    Guard,
    IdSource,
    OrchestrationError,
    RandomIds,
    RuntimeBinding,
    SystemClock,
)
from harness.k0a02.security import SensitiveDataError, scan_untrusted_text

from .profile import ExecutorBinding, ManualExecutionProfile, load_execution_profile
from .store import K0A03_MIGRATION_SHA256, K0a03Store


RETRIABLE_FAILURES = {
    "transient_unavailable_before_dispatch_ack",
    "timeout_before_accepted_response",
}
FIXED_RESULT_TEXT = "synthetic fixture result"


def _unique_json_object(pairs: list[tuple[str, Any]]) -> Mapping[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _strict_json_loads(value: str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )


@dataclass(frozen=True)
class RunProgress:
    run_id: str
    status: str
    role: str | None
    invocation_id: str | None
    request_path: Path | None
    physical_model_invocations: int
    successful_model_invocations: int
    pipeline_network_calls: int
    inspect: Mapping[str, Any]


class K0a03Harness:
    """One durable state transition per manual extension handoff boundary."""

    def __init__(
        self,
        *,
        profile: ManualExecutionProfile | None = None,
        guard: Guard | None = None,
        clock: Clock | None = None,
        ids: IdSource | None = None,
        pipeline_root: Path = PIPELINE_ROOT,
        canonical_fixture_root: Path = CANONICAL_FIXTURE_ROOT,
    ) -> None:
        self.package = load_contract_package()
        self.profile = profile or load_execution_profile()
        self.guard = guard or RootGuard(self.package)
        self.clock = clock or SystemClock()
        self.ids = ids or RandomIds()
        self.pipeline_root = pipeline_root.absolute()
        self.canonical_fixture_root = canonical_fixture_root.absolute()

    @staticmethod
    def _is_link_like(path: Path) -> bool:
        junction = getattr(path, "is_junction", None)
        return path.is_symlink() or (junction is not None and junction())

    @classmethod
    def _require_directory(cls, path: Path, *, create: bool) -> None:
        if not path.exists():
            if cls._is_link_like(path) or not create:
                raise OrchestrationError(f"fixed runtime directory is missing: {path.name}")
            path.mkdir()
        if (
            cls._is_link_like(path)
            or not path.is_dir()
            or os.path.normcase(str(path.resolve(strict=True)))
            != os.path.normcase(str(path.absolute()))
        ):
            raise OrchestrationError("fixed runtime directory is linked or escapes its root")

    @classmethod
    def _paths(cls, runtime_root: Path, *, create: bool) -> Mapping[str, Path]:
        metadata = runtime_root / ".pipeline"
        runtime = metadata / "runtime"
        operator = runtime / "operator"
        archive = runtime / "manual-receipts"
        for path in (metadata, runtime, operator, archive):
            cls._require_directory(path, create=create)
        return {
            "archive": archive,
            "database": runtime / "pipeline.sqlite3",
            "failure": operator / "failure.json",
            "operator": operator,
            "request": operator / "request.json",
            "response": operator / "response.json",
            "selection": operator / "next-executor.json",
        }

    def _guard(self, runtime_root: Path, expected_pipeline_commit: str | None):
        return self.guard.validate(
            pipeline_root=self.pipeline_root,
            canonical_fixture_root=self.canonical_fixture_root,
            runtime_root=runtime_root,
            expected_pipeline_commit=expected_pipeline_commit,
        )

    def initialize(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> RuntimeBinding:
        proof = self._guard(runtime_root.absolute(), expected_pipeline_commit)
        paths = self._paths(proof.runtime_fixture.root, create=True)
        K0a03Store(paths["database"]).initialize()
        return RuntimeBinding(proof.runtime_fixture.root, paths["database"], proof)

    def _open(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> tuple[RuntimeBinding, K0a03Store, Mapping[str, Path]]:
        proof = self._guard(runtime_root.absolute(), expected_pipeline_commit)
        paths = self._paths(proof.runtime_fixture.root, create=False)
        database = paths["database"]
        if (
            not database.is_file()
            or self._is_link_like(database)
            or os.path.normcase(str(database.resolve(strict=True)))
            != os.path.normcase(str(database.absolute()))
        ):
            raise OrchestrationError("runtime is not initialized at the fixed SQLite path")
        store = K0a03Store(database)
        store.initialize()
        return RuntimeBinding(proof.runtime_fixture.root, database, proof), store, paths

    @staticmethod
    def _read_fixed_json(path: Path, label: str, *, maximum: int = 65536) -> tuple[bytes, Mapping[str, Any]]:
        if (
            not path.is_file()
            or K0a03Harness._is_link_like(path)
            or os.path.normcase(str(path.resolve(strict=True)))
            != os.path.normcase(str(path.absolute()))
        ):
            raise OrchestrationError(f"{label} is missing, linked, or not the fixed file")
        payload = path.read_bytes()
        if len(payload) > maximum or payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
            raise OrchestrationError(f"{label} violates exact byte bounds")
        try:
            value = _strict_json_loads(payload.decode("utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OrchestrationError(f"{label} is not strict UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise OrchestrationError(f"{label} must be a JSON object")
        return payload, value

    @staticmethod
    def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
        payload = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
        temporary = path.with_name(f".{path.name}.tmp")
        if temporary.exists() or temporary.is_symlink():
            if (
                K0a03Harness._is_link_like(temporary)
                or not temporary.is_file()
                or temporary.stat(follow_symlinks=False).st_nlink != 1
                or os.path.normcase(str(temporary.resolve(strict=True)))
                != os.path.normcase(str(temporary.absolute()))
                or temporary.read_bytes() != payload
            ):
                raise OrchestrationError(
                    "fixed atomic-write temporary path is unsafe or differs"
                )
            os.replace(temporary, path)
            return
        temporary.write_bytes(payload)
        os.replace(temporary, path)

    def write_executor_selection(self, runtime_root: Path, executor_key: str) -> Path:
        """Write the fixed enumerated operator choice; no CLI/free provider surface."""

        self.profile.executor(executor_key)
        paths = self._paths(runtime_root.absolute(), create=False)
        self._write_atomic(
            paths["selection"],
            {"executor_key": executor_key, "type": "k0a03_executor_selection"},
        )
        return paths["selection"]

    @staticmethod
    def _fixture_input(runtime_root: Path) -> str:
        path = runtime_root / "fixture" / "request.yaml"
        if path.is_symlink() or path.resolve(strict=True) != path:
            raise OrchestrationError("fixed fixture input is linked")
        payload = path.read_bytes()
        if len(payload) > 4096 or payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
            raise OrchestrationError("fixed fixture input violates textual bounds")
        try:
            return payload.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise OrchestrationError("fixed fixture input is not strict UTF-8") from exc

    def _capabilities(self, binding: ExecutorBinding) -> Mapping[str, Any]:
        return {
            "filesystem_roots": [],
            "model_channel": binding.provider,
            "policy_version": self.profile.policy_version,
            "tools": [],
        }

    def _environment(self, binding: ExecutorBinding) -> Mapping[str, Any]:
        return {
            "adapter_version": f"{binding.extension_id}@{binding.extension_version}",
            "architecture": platform.machine() or "unknown",
            "clock_binding": "manual_extension_receipt",
            "config_sha256": self.profile.complete_file_sha256,
            "dependency_lock_sha256": K0A03_MIGRATION_SHA256,
            "harness_version": "k0a03-manual-v1",
            "locale": "C",
            "os": platform.system() or "unknown",
            "random_seed": None,
            "timezone": "UTC",
            "tool_registry_version": binding.tool_enforcement,
        }

    @staticmethod
    def _fragments(
        *, system: str, developer: Mapping[str, Any], user: Mapping[str, Any]
    ) -> tuple[Mapping[str, Any], ...]:
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

    def _required_output(
        self,
        *,
        role: str,
        invocation_id: str,
        run_id: str,
        triggering_event_id: str,
    ) -> Mapping[str, Any]:
        common = {
            "invocation_id": invocation_id,
            "run_id": run_id,
            "triggering_event_id": triggering_event_id,
        }
        if role == "S0":
            return {
                "action": "invoke",
                **common,
                "route": "synthetic_Layer0",
                "type": "s0_route_proposal",
            }
        if role == "synthetic_Layer0":
            return {
                "action": "invoke",
                **common,
                "route": "fixture_worker",
                "type": "synthetic_layer0_invocation_proposal",
            }
        schema = self.package.schema_identity("bootstrap_synthetic_result")
        return {
            "action": "publish",
            "artifact_type": "bootstrap.synthetic_result",
            "content_sha256": sha256_text(FIXED_RESULT_TEXT),
            "content_text": FIXED_RESULT_TEXT,
            **common,
            "logical_owner": "fixture.bootstrap_worker",
            "media_type": "text/plain",
            "parent_ref": "fixture:seed:request.yaml",
            "result_schema_id": schema.id,
            "result_schema_sha256": schema.sha256,
            "result_schema_version": schema.version,
            "type": "fixture_worker_publication_proposal",
        }

    def _context(
        self,
        *,
        role: str,
        actor_input: Mapping[str, Any],
        invocation_id: str,
        run_id: str,
        triggering_event_id: str,
        binding: ExecutorBinding,
    ) -> tuple[str, tuple[Mapping[str, Any], ...], Mapping[str, Any]]:
        actor = self.package.actor(role)
        actor_input = self.package.validate_actor_input(role, actor_input)
        required_output = self._required_output(
            role=role,
            invocation_id=invocation_id,
            run_id=run_id,
            triggering_event_id=triggering_event_id,
        )
        prompt = self.package.prompt(role)
        required_output_contract = {
            name: value
            for name, value in required_output.items()
            if name not in {"invocation_id", "run_id", "triggering_event_id"}
        }
        fragments = self._fragments(
            system=prompt["text"],
            developer={
                "capability_policy": self._capabilities(binding),
                "contract_sha256": actor["contract_sha256"],
                "execution_mode": self.profile.execution_mode,
                "extension_id": binding.extension_id,
                "extension_version": binding.extension_version,
                "required_output_contract": required_output_contract,
                "response_identity_source": "manual_dispatch_envelope",
                "runtime_profile_sha256": self.profile.complete_file_sha256,
                "tool_enforcement": binding.tool_enforcement,
            },
            user={"input": actor_input, "trust": "untrusted_content"},
        )
        context_text = canonical_json(fragments)
        scan_untrusted_text(context_text, label=f"{role} rendered context")
        return context_text, fragments, required_output

    @staticmethod
    def _command() -> Mapping[str, Any]:
        package = load_contract_package()
        return {
            "command": "bootstrap",
            "fixture_spec_sha256": package.fixture_binding["fixture_spec_sha256"],
            "profile": "F00",
            "type": "normalized_f00_command",
        }

    def _start(self, binding: RuntimeBinding, store: K0a03Store) -> str:
        command = self.package.validate_normalized_command(self._command())
        run_id = self.ids.new("run")
        correlation_id = self.ids.new("correlation")
        command_event_id = self.ids.new("event-command")
        started_event_id = self.ids.new("event-started")
        event_schema = self.package.schema_identity("f00_event_envelope")
        command_payload = {
            "command": command["command"],
            "contract_package_sha256": self.profile.complete_file_sha256,
            "profile": command["profile"],
            "run_id": run_id,
        }
        started_payload = {"run_id": run_id, "state": "running"}
        self.package.validate("event_command_received", command_payload)
        self.package.validate("event_run_started", started_payload)
        store.create_started_run(
            run_id=run_id,
            pipeline_commit=binding.guard_proof.pipeline.commit,
            fixture_commit=binding.guard_proof.runtime_fixture.commit,
            fixture_tree=binding.guard_proof.runtime_fixture.tree,
            created_at=self.clock.now(),
            transition_id=self.ids.new("run-started-transition"),
            transitioned_at=self.clock.now(),
            command_event_id=command_event_id,
            command_payload=command_payload,
            command_created_at=self.clock.now(),
            started_event_id=started_event_id,
            started_payload=started_payload,
            started_created_at=self.clock.now(),
            correlation_id=correlation_id,
            schema_id=event_schema.id,
            schema_version=event_schema.version,
            schema_sha256=event_schema.sha256,
        )
        return run_id

    def _next_role_input(
        self, runtime_root: Path, inspect: Mapping[str, Any]
    ) -> tuple[str | None, Mapping[str, Any] | None, str | None, str | None]:
        events = inspect["events"]
        command_event_id = events[0]["event_id"]
        started_event_id = events[1]["event_id"]
        proposals = inspect["proposals"]
        if not proposals["s0"]:
            return "S0", self._command(), command_event_id, None
        if not proposals["actor"]:
            s0 = proposals["s0"][0]
            return (
                "synthetic_Layer0",
                {
                    "action": "invoke",
                    "route": "synthetic_Layer0",
                    "run_id": inspect["run"]["run_id"],
                    "source_invocation_id": s0["invocation_id"],
                    "source_proposal_id": s0["proposal_id"],
                    "triggering_event_id": command_event_id,
                    "type": "validated_route_proposal",
                },
                command_event_id,
                s0["proposal_id"],
            )
        layer0 = [item for item in proposals["actor"] if item["role"] == "synthetic_Layer0"]
        worker = [item for item in proposals["actor"] if item["role"] == "fixture_worker"]
        if not worker:
            if len(layer0) != 1:
                raise OrchestrationError("accepted Layer0 proposal lineage is incomplete")
            layer0_result = _strict_json_loads(layer0[0]["raw_output_text"])
            fixture_input = self._fixture_input(runtime_root)
            return (
                "fixture_worker",
                {
                    "fixture_input": {
                        "content_sha256": sha256_text(fixture_input),
                        "content_text": fixture_input,
                        "ref": "fixture:seed:request.yaml",
                    },
                    "layer0_proposal": layer0_result,
                },
                started_event_id,
                layer0[0]["proposal_id"],
            )
        return None, None, None, None

    def _selection(self, paths: Mapping[str, Path]) -> ExecutorBinding | None:
        path = paths["selection"]
        if not path.exists():
            return None
        _, value = self._read_fixed_json(path, "executor selection", maximum=1024)
        if set(value) != {"executor_key", "type"} or value["type"] != "k0a03_executor_selection":
            raise OrchestrationError("executor selection fields differ")
        return self.profile.executor(value["executor_key"])

    def _stage(
        self,
        store: K0a03Store,
        paths: Mapping[str, Path],
        *,
        inspect: Mapping[str, Any],
        role: str,
        actor_input: Mapping[str, Any],
        triggering_event_id: str,
        proposal_to_consume: str | None,
        binding: ExecutorBinding,
        delivery_id: str | None = None,
        attempt_number: int = 1,
    ) -> Mapping[str, Any]:
        run_id = inspect["run"]["run_id"]
        if len(inspect["invocations"]) >= self.profile.physical_invocation_budget["worst_case"]:
            raise OrchestrationError("K0a-03 physical invocation budget is exhausted")
        if delivery_id is None:
            delivery_id = self.ids.new(f"delivery-{role.lower()}")
            store.create_delivery(
                delivery_id=delivery_id,
                run_id=run_id,
                delivery_key=f"{run_id}:{role}",
                role=role,
                triggering_event_id=triggering_event_id,
                created_at=self.clock.now(),
            )
        invocation_id = self.ids.new(f"{role}-invocation-{attempt_number}")
        context_text, fragments, required_output = self._context(
            role=role,
            actor_input=actor_input,
            invocation_id=invocation_id,
            run_id=run_id,
            triggering_event_id=triggering_event_id,
            binding=binding,
        )
        prompt = self.package.prompt_identity(role)
        contract = self.package.actor_contract_identity(role)
        result_schema = self.package.result_schema_identity(role)
        store.create_invocation(
            InvocationSpec(
                invocation_id=invocation_id,
                delivery_id=delivery_id,
                attempt_number=attempt_number,
                prompt_id=prompt.id,
                prompt_version=prompt.version,
                prompt_sha256=prompt.sha256,
                contract_id=contract.id,
                contract_version=contract.version,
                contract_sha256=contract.sha256,
                result_schema_id=result_schema.id,
                result_schema_version=result_schema.version,
                result_schema_sha256=result_schema.sha256,
                registry_sha256=self.profile.complete_file_sha256,
                provider=binding.provider,
                model_profile=binding.model_profile,
                model_identifier=binding.model_identifier,
                parameters=binding.parameters,
                context_limit_tokens=binding.context_limit_tokens,
                created_at=self.clock.now(),
            )
        )
        if attempt_number == 1 and proposal_to_consume is not None:
            if role == "synthetic_Layer0":
                store.consume_s0_route(
                    consumption_id=self.ids.new("s0-route-consumption"),
                    proposal_id=proposal_to_consume,
                    downstream_invocation_id=invocation_id,
                    created_at=self.clock.now(),
                )
            elif role == "fixture_worker":
                store.consume_actor_proposal(
                    consumption_id=self.ids.new("layer0-proposal-consumption"),
                    proposal_id=proposal_to_consume,
                    downstream_invocation_id=invocation_id,
                    created_at=self.clock.now(),
                )
        sequence = max((item["sequence_number"] for item in inspect["replay_points"]), default=-1) + 1
        before_id = self.ids.new(f"{invocation_id}-before")
        store.record_replay_point(
            ReplayPoint(
                replay_point_id=before_id,
                invocation_id=invocation_id,
                position="before",
                sequence_number=sequence,
                context_text=context_text,
                context_sha256=sha256_text(context_text),
                context_fragments=fragments,
                capabilities=self._capabilities(binding),
                environment=self._environment(binding),
                capture_completeness=binding.capture_completeness,
                gap_code=binding.gap_code,
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
        dispatch_id = self.ids.new("manual-dispatch")
        store.record_manual_dispatch(
            {
                "before_replay_point_id": before_id,
                "context_sha256": sha256_text(context_text),
                "context_text": context_text,
                "created_at": self.clock.now(),
                "delivery_id": delivery_id,
                "dispatch_id": dispatch_id,
                "execution_mode": self.profile.execution_mode,
                "executor_key": binding.key,
                "extension_id": binding.extension_id,
                "extension_version": binding.extension_version,
                "invocation_id": invocation_id,
                "model_identifier": binding.model_identifier,
                "model_profile": binding.model_profile,
                "provider": binding.provider,
                "role": role,
                "run_id": run_id,
                "tool_enforcement": binding.tool_enforcement,
            }
        )
        request = {
            "context_sha256": sha256_text(context_text),
            "context_text": context_text,
            "dispatch_id": dispatch_id,
            "execution_mode": self.profile.execution_mode,
            "executor_key": binding.key,
            "extension_id": binding.extension_id,
            "extension_version": binding.extension_version,
            "invocation_id": invocation_id,
            "manual_operator_instruction": "Do not call any tool. Return only the exact canonical JSON value in required_exact_output.",
            "model_identifier": binding.model_identifier,
            "model_profile": binding.model_profile,
            "provider": binding.provider,
            "required_exact_output": required_output,
            "role": role,
            "run_id": run_id,
            "tool_enforcement": binding.tool_enforcement,
            "type": "k0a03_manual_dispatch_request",
        }
        self._write_atomic(paths["request"], request)
        if paths["selection"].exists():
            paths["selection"].unlink()
        return request

    @staticmethod
    def _receipt_required_fields() -> set[str]:
        return {
            "completed_at",
            "dispatch_id",
            "duration_ms",
            "extension_id",
            "extension_version",
            "finish_reason",
            "input_tokens",
            "invocation_id",
            "model_identifier",
            "model_profile",
            "monotonic_completed_ns",
            "monotonic_started_ns",
            "output_tokens",
            "provider",
            "receipt_source",
            "response_sha256",
            "response_text",
            "started_at",
            "tool_calls_observed",
            "total_tokens",
            "transcript_event_count",
            "transcript_complete",
            "transcript_sha256",
            "transcript_text",
            "type",
            "usage",
        }

    def _binding_for_orphan(self, orphan: Mapping[str, Any]) -> ExecutorBinding:
        matches = []
        for key in ("chatgpt_gpt_5_6_sol", "claude_opus_4_6"):
            binding = self.profile.executor(key)
            if (
                binding.provider == orphan["provider"]
                and binding.model_profile == orphan["model_profile"]
                and binding.model_identifier == orphan["model_identifier"]
                and canonical_json(binding.parameters) == orphan["parameters_json"]
            ):
                matches.append(binding)
        if len(matches) != 1:
            raise OrchestrationError("orphan invocation executor pins are unknown or ambiguous")
        return matches[0]

    def _ensure_consumption(
        self,
        store: K0a03Store,
        inspect: Mapping[str, Any],
        *,
        role: str,
        proposal_id: str | None,
        invocation_id: str,
    ) -> None:
        if proposal_id is None:
            return
        key = "s0_consumptions" if role == "synthetic_Layer0" else "actor_consumptions"
        existing = [
            item for item in inspect["proposals"][key] if item["proposal_id"] == proposal_id
        ]
        if existing:
            target = [
                item for item in inspect["invocations"] if item["invocation_id"] == invocation_id
            ]
            consumed = [
                item
                for item in inspect["invocations"]
                if item["invocation_id"] == existing[0]["downstream_invocation_id"]
            ]
            if (
                len(existing) != 1
                or len(target) != 1
                or len(consumed) != 1
                or target[0]["delivery_id"] != consumed[0]["delivery_id"]
            ):
                raise OrchestrationError("orphan invocation proposal consumption differs")
            return
        if role == "synthetic_Layer0":
            store.consume_s0_route(
                consumption_id=self.ids.new("s0-route-consumption"),
                proposal_id=proposal_id,
                downstream_invocation_id=invocation_id,
                created_at=self.clock.now(),
            )
        elif role == "fixture_worker":
            store.consume_actor_proposal(
                consumption_id=self.ids.new("layer0-proposal-consumption"),
                proposal_id=proposal_id,
                downstream_invocation_id=invocation_id,
                created_at=self.clock.now(),
            )

    def _recover_orphan_dispatch(
        self,
        store: K0a03Store,
        paths: Mapping[str, Path],
        inspect: Mapping[str, Any],
        orphan: Mapping[str, Any],
        *,
        runtime_root: Path,
    ) -> Mapping[str, Any]:
        role, actor_input, triggering_event_id, proposal_id = self._next_role_input(
            runtime_root, inspect
        )
        if (
            role != orphan["role"]
            or actor_input is None
            or triggering_event_id != orphan["triggering_event_id"]
        ):
            raise OrchestrationError("orphan invocation role/input/event identity changed")
        binding = self._binding_for_orphan(orphan)
        context_text, fragments, required_output = self._context(
            role=role,
            actor_input=actor_input,
            invocation_id=orphan["invocation_id"],
            run_id=orphan["run_id"],
            triggering_event_id=triggering_event_id,
            binding=binding,
        )
        state = orphan["state"]
        self._ensure_consumption(
            store,
            inspect,
            role=role,
            proposal_id=proposal_id,
            invocation_id=orphan["invocation_id"],
        )
        before = [
            item
            for item in inspect["replay_points"]
            if item["invocation_id"] == orphan["invocation_id"] and item["position"] == "before"
        ]
        if state == "prepared":
            before_id = self.ids.new(f"{orphan['invocation_id']}-before")
            sequence = max(
                (item["sequence_number"] for item in inspect["replay_points"]), default=-1
            ) + 1
            store.record_replay_point(
                ReplayPoint(
                    replay_point_id=before_id,
                    invocation_id=orphan["invocation_id"],
                    position="before",
                    sequence_number=sequence,
                    context_text=context_text,
                    context_sha256=sha256_text(context_text),
                    context_fragments=fragments,
                    capabilities=self._capabilities(binding),
                    environment=self._environment(binding),
                    capture_completeness=binding.capture_completeness,
                    gap_code=binding.gap_code,
                    created_at=self.clock.now(),
                )
            )
            state = "replay_before_committed"
        else:
            if (
                len(before) != 1
                or before[0]["envelope"]["context"]["text"] != context_text
                or before[0]["envelope"]["context"]["sha256"] != sha256_text(context_text)
            ):
                raise OrchestrationError("orphan invocation before-replay differs")
            before_id = before[0]["replay_point_id"]
        if state == "replay_before_committed":
            store.transition_invocation(
                invocation_id=orphan["invocation_id"],
                expected_state="replay_before_committed",
                new_state="dispatched",
                transition_id=self.ids.new(f"{orphan['invocation_id']}-dispatched"),
                occurred_at=self.clock.now(),
            )
        dispatch_id = self.ids.new("manual-dispatch")
        store.record_manual_dispatch(
            {
                "before_replay_point_id": before_id,
                "context_sha256": sha256_text(context_text),
                "context_text": context_text,
                "created_at": self.clock.now(),
                "delivery_id": orphan["delivery_id"],
                "dispatch_id": dispatch_id,
                "execution_mode": self.profile.execution_mode,
                "executor_key": binding.key,
                "extension_id": binding.extension_id,
                "extension_version": binding.extension_version,
                "invocation_id": orphan["invocation_id"],
                "model_identifier": binding.model_identifier,
                "model_profile": binding.model_profile,
                "provider": binding.provider,
                "role": role,
                "run_id": orphan["run_id"],
                "tool_enforcement": binding.tool_enforcement,
            }
        )
        request = {
            "context_sha256": sha256_text(context_text),
            "context_text": context_text,
            "dispatch_id": dispatch_id,
            "execution_mode": self.profile.execution_mode,
            "executor_key": binding.key,
            "extension_id": binding.extension_id,
            "extension_version": binding.extension_version,
            "invocation_id": orphan["invocation_id"],
            "manual_operator_instruction": "Do not call any tool. Return only the exact canonical JSON value in required_exact_output.",
            "model_identifier": binding.model_identifier,
            "model_profile": binding.model_profile,
            "provider": binding.provider,
            "required_exact_output": required_output,
            "role": role,
            "run_id": orphan["run_id"],
            "tool_enforcement": binding.tool_enforcement,
            "type": "k0a03_manual_dispatch_request",
        }
        self._write_atomic(paths["request"], request)
        if paths["selection"].exists():
            selected = self._selection(paths)
            if selected is None or selected.key != binding.key:
                raise OrchestrationError("orphan invocation selection changed")
            paths["selection"].unlink()
        return request

    @staticmethod
    def _validate_transcript(receipt: Mapping[str, Any], response_text: str) -> tuple[str, int]:
        transcript = receipt["transcript_text"]
        if not isinstance(transcript, str) or not transcript:
            raise OrchestrationError("extension transcript violates exact textual bounds")
        try:
            transcript_size = len(transcript.encode("utf-8", errors="strict"))
            transcript_sha256 = sha256_text(transcript)
        except UnicodeError as exc:
            raise OrchestrationError("extension transcript is not strict UTF-8") from exc
        if transcript_size > 65536:
            raise OrchestrationError("extension transcript violates exact textual bounds")
        if transcript_sha256 != receipt["transcript_sha256"]:
            raise OrchestrationError("extension transcript hash differs")
        try:
            events = [
                _strict_json_loads(line) for line in transcript.splitlines() if line
            ]
        except (json.JSONDecodeError, ValueError) as exc:
            raise OrchestrationError("extension transcript is not strict JSONL") from exc
        if receipt["transcript_event_count"] != len(events) or len(events) != 4:
            raise OrchestrationError("extension transcript event cardinality differs")
        if any(not isinstance(event, dict) for event in events):
            raise OrchestrationError("extension transcript events must be JSON objects")
        if [event.get("type") for event in events] != [
            "thread.started",
            "turn.started",
            "item.completed",
            "turn.completed",
        ]:
            raise OrchestrationError("extension transcript event sequence contains an error or tool event")
        item = events[2].get("item")
        usage = events[3].get("usage")
        if (
            not isinstance(item, dict)
            or item.get("type") != "agent_message"
            or item.get("text") != response_text
            or not isinstance(usage, dict)
            or usage.get("input_tokens") != receipt["input_tokens"]
            or usage.get("output_tokens") != receipt["output_tokens"]
        ):
            raise OrchestrationError("extension transcript response/usage differs from the receipt")
        return transcript, len(events)

    def _archive(self, source: Path, archive: Path, invocation_id: str, kind: str) -> None:
        target = archive / f"{sha256_text(invocation_id)}-{kind}.json"
        if target.is_symlink():
            raise OrchestrationError("manual receipt archive target is linked")
        if target.exists():
            if not source.exists() or source.read_bytes() != target.read_bytes():
                raise OrchestrationError("manual receipt archive target differs")
            source.unlink()
            return
        os.replace(source, target)

    def _cleanup_completed_sidecars(
        self, store: K0a03Store, paths: Mapping[str, Path], inspect: Mapping[str, Any]
    ) -> None:
        proposals = inspect["proposals"]["s0"] + inspect["proposals"]["actor"]
        execution = store.execution_readback(inspect["run"]["run_id"])
        if paths["response"].exists():
            _, receipt = self._read_fixed_json(
                paths["response"], "completed manual response receipt"
            )
            invocation_id = receipt.get("invocation_id")
            if (
                not isinstance(invocation_id, str)
                or len(
                    [item for item in proposals if item["invocation_id"] == invocation_id]
                )
                != 1
                or len(
                    [
                        item
                        for item in execution["receipts"]
                        if item["invocation_id"] == invocation_id
                    ]
                )
                != 1
            ):
                raise OrchestrationError(
                    "stale response sidecar is not backed by one durable proposal/receipt"
                )
            self._archive(paths["response"], paths["archive"], invocation_id, "response")
        if paths["request"].exists():
            _, request = self._read_fixed_json(paths["request"], "completed manual request")
            invocation_id = request.get("invocation_id")
            dispatch_id = request.get("dispatch_id")
            if (
                not isinstance(invocation_id, str)
                or not isinstance(dispatch_id, str)
                or len(
                    [item for item in proposals if item["invocation_id"] == invocation_id]
                )
                != 1
                or len(
                    [
                        item
                        for item in execution["receipts"]
                        if item["invocation_id"] == invocation_id
                        and item["dispatch_id"] == dispatch_id
                    ]
                )
                != 1
            ):
                raise OrchestrationError(
                    "stale request sidecar is not backed by one durable proposal/receipt"
                )
            paths["request"].unlink()

    def _cleanup_failure_sidecars(
        self, paths: Mapping[str, Path], failed: Mapping[str, Any]
    ) -> None:
        if paths["failure"].exists():
            _, value = self._read_fixed_json(
                paths["failure"], "durable manual failure receipt", maximum=8192
            )
            if (
                value.get("invocation_id") != failed["invocation_id"]
                or value.get("dispatch_id") != failed["dispatch_id"]
            ):
                raise OrchestrationError("durable failure sidecar identity differs")
            self._archive(
                paths["failure"], paths["archive"], failed["invocation_id"], "failure"
            )
        if paths["request"].exists():
            _, request = self._read_fixed_json(paths["request"], "failed manual request")
            if (
                request.get("invocation_id") != failed["invocation_id"]
                or request.get("dispatch_id") != failed["dispatch_id"]
            ):
                raise OrchestrationError("failed request sidecar identity differs")
            paths["request"].unlink()
        if paths["selection"].exists():
            selected = self._selection(paths)
            if selected is not None and selected.key == failed["executor_key"]:
                paths["selection"].unlink()

    def _accept_response(
        self,
        store: K0a03Store,
        paths: Mapping[str, Path],
        pending: Mapping[str, Any],
        inspect: Mapping[str, Any],
    ) -> bool:
        _, receipt = self._read_fixed_json(paths["response"], "manual response receipt")
        if set(receipt) != self._receipt_required_fields() or receipt["type"] != "k0a03_manual_response_receipt":
            raise OrchestrationError("manual response receipt fields differ")
        pinned = {
            "dispatch_id": pending["dispatch_id"],
            "extension_id": pending["extension_id"],
            "extension_version": pending["extension_version"],
            "invocation_id": pending["invocation_id"],
            "model_identifier": pending["model_identifier"],
            "model_profile": pending["model_profile"],
            "provider": pending["provider"],
            "receipt_source": "extension_jsonl_or_ui_receipt",
            "tool_calls_observed": 0,
            "transcript_complete": True,
        }
        if any(receipt[name] != expected for name, expected in pinned.items()):
            revision = inspect["run"]["state_revision"]
            state = "blocked_policy" if receipt.get("tool_calls_observed") != 0 else "failed_validation"
            self._fail_run(store, inspect["run"]["run_id"], revision, state)
            raise OrchestrationError("manual receipt identity/capability proof differs; run blocked")
        response_text = receipt["response_text"]
        if sha256_text(response_text) != receipt["response_sha256"]:
            raise OrchestrationError("manual response text hash differs")
        try:
            _strict_json_loads(response_text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise OrchestrationError("manual response is not strict JSON") from exc
        try:
            transcript_text, transcript_event_count = self._validate_transcript(
                receipt, response_text
            )
        except OrchestrationError as exc:
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "blocked_policy",
            )
            raise OrchestrationError(
                "extension transcript could not prove zero-tool execution; run blocked"
            ) from exc
        try:
            scan_untrusted_text(response_text, label=f"{pending['role']} manual response")
        except SensitiveDataError as exc:
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "blocked_policy",
            )
            raise OrchestrationError("manual response failed secret/PII policy") from exc
        telemetry = InvocationTelemetry(
            telemetry_id=self.ids.new("manual-telemetry"),
            invocation_id=pending["invocation_id"],
            provider=receipt["provider"],
            model_profile=receipt["model_profile"],
            model_identifier=receipt["model_identifier"],
            parameters={},
            response_text=response_text,
            response_sha256=receipt["response_sha256"],
            started_at=receipt["started_at"],
            completed_at=receipt["completed_at"],
            duration_ms=receipt["duration_ms"],
            monotonic_started_ns=receipt["monotonic_started_ns"],
            monotonic_completed_ns=receipt["monotonic_completed_ns"],
            input_tokens=receipt["input_tokens"],
            output_tokens=receipt["output_tokens"],
            total_tokens=receipt["total_tokens"],
            usage=receipt["usage"],
            finish_reason=receipt["finish_reason"],
        )
        try:
            self.package.validate_response(
                pending["role"],
                response_text,
                ResponseIdentity(
                    pending["invocation_id"], pending["run_id"], self._triggering_event(inspect, pending["role"])
                ),
            )
            accepted = True
            validation_error: Exception | None = None
        except ContractValidationError as exc:
            accepted = False
            validation_error = exc
        state = pending["invocation_state"]
        if state == "dispatched":
            store.record_telemetry(telemetry)
            state = "response_captured"
        else:
            existing_telemetry = [
                item for item in inspect["telemetry"] if item["invocation_id"] == pending["invocation_id"]
            ]
            if (
                len(existing_telemetry) != 1
                or existing_telemetry[0]["response_text"] != response_text
                or existing_telemetry[0]["response_sha256"] != receipt["response_sha256"]
            ):
                raise OrchestrationError("resumed response differs from persisted telemetry")
        execution = store.execution_readback(pending["run_id"])
        existing_receipts = [
            item for item in execution["receipts"] if item["invocation_id"] == pending["invocation_id"]
        ]
        if not existing_receipts:
            store.record_manual_receipt(
                {
                    "accepted_at": self.clock.now(),
                    "dispatch_id": pending["dispatch_id"],
                    "invocation_id": pending["invocation_id"],
                    "receipt_id": self.ids.new("manual-receipt"),
                    "receipt_source": receipt["receipt_source"],
                    "response_sha256": receipt["response_sha256"],
                    "response_text": response_text,
                    "tool_calls_observed": receipt["tool_calls_observed"],
                    "transcript_event_count": transcript_event_count,
                    "transcript_complete": int(receipt["transcript_complete"]),
                    "transcript_sha256": receipt["transcript_sha256"],
                    "transcript_text": transcript_text,
                    "validation_disposition": "accepted" if accepted else "rejected",
                }
            )
        elif (
            len(existing_receipts) != 1
            or existing_receipts[0]["response_sha256"] != receipt["response_sha256"]
            or existing_receipts[0]["transcript_sha256"] != receipt["transcript_sha256"]
            or existing_receipts[0]["validation_disposition"]
            != ("accepted" if accepted else "rejected")
        ):
            raise OrchestrationError("resumed manual receipt differs from persisted evidence")
        if state == "response_captured":
            store.transition_invocation(
                invocation_id=pending["invocation_id"],
                expected_state="response_captured",
                new_state="validated",
                transition_id=self.ids.new("manual-schema-checked"),
                occurred_at=self.clock.now(),
            )
            state = "validated"
        inspect = store.inspect(pending["run_id"])
        if state == "validated":
            sequence = max(
                (item["sequence_number"] for item in inspect["replay_points"]), default=-1
            ) + 1
            before = [
                item
                for item in inspect["replay_points"]
                if item["invocation_id"] == pending["invocation_id"]
                and item["position"] == "before"
            ]
            if len(before) != 1:
                raise OrchestrationError("manual response lacks one exact before replay")
            envelope = before[0]["envelope"]
            store.record_replay_point(
                ReplayPoint(
                    replay_point_id=self.ids.new(f"{pending['invocation_id']}-after"),
                    invocation_id=pending["invocation_id"],
                    position="after",
                    sequence_number=sequence,
                    context_text=envelope["context"]["text"],
                    context_sha256=envelope["context"]["sha256"],
                    context_fragments=envelope["context"]["fragments"],
                    capabilities=envelope["capabilities"],
                    environment=envelope["environment"],
                    capture_completeness=envelope["capture_completeness"],
                    gap_code=envelope["gap_code"],
                    created_at=self.clock.now(),
                )
            )
            state = "replay_after_committed"
        inspect = store.inspect(pending["run_id"])
        proposals = inspect["proposals"]["s0"] + inspect["proposals"]["actor"]
        existing_proposals = [
            item for item in proposals if item["invocation_id"] == pending["invocation_id"]
        ]
        if state == "replay_after_committed" and not existing_proposals:
            proposal_id = self.ids.new(f"{pending['role']}-proposal")
            if pending["role"] == "S0":
                store.record_s0_route_validation(
                    proposal_id=proposal_id,
                    invocation_id=pending["invocation_id"],
                    accepted=accepted,
                    created_at=self.clock.now(),
                )
            else:
                store.record_actor_proposal(
                    proposal_id=proposal_id,
                    invocation_id=pending["invocation_id"],
                    accepted=accepted,
                    created_at=self.clock.now(),
                )
        elif len(existing_proposals) != 1:
            raise OrchestrationError("resumed actor proposal cardinality differs")
        self._archive(paths["response"], paths["archive"], pending["invocation_id"], "response")
        if paths["request"].exists():
            paths["request"].unlink()
        if not accepted:
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "failed_validation",
            )
            raise OrchestrationError("manual model response failed exact actor validation") from validation_error
        return pending["role"] == "fixture_worker"

    @staticmethod
    def _triggering_event(inspect: Mapping[str, Any], role: str) -> str:
        events = inspect["events"]
        return events[0]["event_id"] if role in {"S0", "synthetic_Layer0"} else events[1]["event_id"]

    def _fail_run(
        self, store: K0a03Store, run_id: str, revision: int, state: str
    ) -> None:
        store.transition_run(
            run_id=run_id,
            expected_state="running",
            expected_revision=revision,
            new_state=state,
            transition_id=f"{run_id}:{state}",
            occurred_at=self.clock.now(),
        )

    def _handle_failure(
        self,
        store: K0a03Store,
        paths: Mapping[str, Path],
        pending: Mapping[str, Any],
        inspect: Mapping[str, Any],
    ) -> bool:
        _, failure = self._read_fixed_json(paths["failure"], "manual failure receipt", maximum=8192)
        expected_keys = {
            "dispatch_id",
            "failure_code",
            "invocation_id",
            "receipt_source",
            "tool_calls_observed",
            "transcript_complete",
            "type",
        }
        if set(failure) != expected_keys or failure["type"] != "k0a03_manual_failure_receipt":
            raise OrchestrationError("manual failure receipt fields differ")
        if (
            failure["dispatch_id"] != pending["dispatch_id"]
            or failure["invocation_id"] != pending["invocation_id"]
            or failure["receipt_source"] != "extension_jsonl_or_ui_receipt"
            or failure["tool_calls_observed"] != 0
            or failure["transcript_complete"] is not True
            or failure["failure_code"] not in RETRIABLE_FAILURES | {"non_retriable_provider_failure"}
        ):
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "blocked_policy",
            )
            raise OrchestrationError("manual failure identity/capability proof differs")
        recorded_at = self.clock.now()
        store.record_manual_invocation_failure(
            {
                "dispatch_id": pending["dispatch_id"],
                "failure_code": failure["failure_code"],
                "failure_receipt_id": self.ids.new("manual-failure"),
                "invocation_id": pending["invocation_id"],
                "receipt_source": failure["receipt_source"],
                "recorded_at": recorded_at,
                "tool_calls_observed": failure["tool_calls_observed"],
                "transcript_complete": int(failure["transcript_complete"]),
            },
            transition_id=self.ids.new("manual-invocation-failed"),
        )
        self._archive(paths["failure"], paths["archive"], pending["invocation_id"], "failure")
        if paths["request"].exists():
            paths["request"].unlink()
        if failure["failure_code"] not in RETRIABLE_FAILURES or pending["attempt_number"] == 2:
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "failed_invocation",
            )
            return False
        return True

    def _publish_and_complete(
        self, store: K0a03Store, inspect: Mapping[str, Any]
    ) -> None:
        run_id = inspect["run"]["run_id"]
        events = inspect["events"]
        correlation_id = events[0]["correlation_id"]
        started_event_id = events[1]["event_id"]
        worker = [item for item in inspect["proposals"]["actor"] if item["role"] == "fixture_worker"]
        if len(worker) != 1:
            raise OrchestrationError("publication requires exactly one accepted worker proposal")
        event_schema = self.package.schema_identity("f00_event_envelope")
        if not inspect["publication"]:
            worker_result = _strict_json_loads(worker[0]["raw_output_text"])
            result_schema = self.package.schema_identity("bootstrap_synthetic_result")
            store.publish_artifact_version(
                ArtifactPublication(
                    publication_transaction_id=self.ids.new("publication"),
                    idempotency_key=f"{run_id}:publication",
                    run_id=run_id,
                    expected_run_revision=inspect["run"]["state_revision"],
                    invocation_id=worker[0]["invocation_id"],
                    artifact_id=self.ids.new("artifact"),
                    artifact_version_id=self.ids.new("artifact-version"),
                    content_text=worker_result["content_text"],
                    content_sha256=worker_result["content_sha256"],
                    media_type=worker_result["media_type"],
                    schema_id=result_schema.id,
                    schema_version=result_schema.version,
                    schema_sha256=result_schema.sha256,
                    correlation_id=correlation_id,
                    caused_by_event_id=started_event_id,
                    version_created_event_id=self.ids.new("event-version-created"),
                    version_created_idempotency_key=f"{run_id}:artifact.version_created",
                    handoff_event_id=self.ids.new("event-handoff"),
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
            inspect = store.inspect(run_id)
        artifact = inspect["artifact"]
        handoff = [event for event in inspect["events"] if event["event_type"] == "handoff.ready"]
        if len(handoff) != 1 or not artifact:
            raise OrchestrationError("published artifact/handoff readback is incomplete")
        if not inspect["sink_acceptance"]:
            BootstrapSink(self.package, store).accept(
                {
                    "accepted": True,
                    "artifact_version_id": artifact["artifact_version_id"],
                    "content_sha256": artifact["content_sha256"],
                    "content_text": artifact["content_text"],
                    "handoff_event_id": handoff[0]["event_id"],
                    "media_type": artifact["media_type"],
                    "profile": "F00",
                    "run_id": run_id,
                    "type": "bootstrap_sink_acceptance",
                },
                sink_acceptance_id=self.ids.new("sink-acceptance"),
                accepted_at=self.clock.now(),
            )
            inspect = store.inspect(run_id)
        if not inspect["readback_gate"]:
            store.create_readback_gate(
                readback_gate_id=self.ids.new("readback-gate"),
                run_id=run_id,
                checked_at=self.clock.now(),
            )
            inspect = store.inspect(run_id)
        sink_id = inspect["sink_acceptance"]["sink_acceptance_id"]
        gate_id = inspect["readback_gate"]["readback_gate_id"]
        completed_payload = {
            "readback_gate_id": gate_id,
            "run_id": run_id,
            "sink_acceptance_id": sink_id,
            "state": "completed",
        }
        self.package.validate("event_run_completed", completed_payload)
        store.complete_run(
            run_id=run_id,
            expected_revision=inspect["run"]["state_revision"],
            event_id=self.ids.new("event-completed"),
            correlation_id=correlation_id,
            schema_id=event_schema.id,
            schema_version=event_schema.version,
            schema_sha256=event_schema.sha256,
            idempotency_key=f"{run_id}:run.completed",
            occurred_at=self.clock.now(),
        )

    def _progress(
        self,
        store: K0a03Store,
        inspect: Mapping[str, Any],
        status: str,
        pending: Mapping[str, Any] | None,
        request_path: Path | None,
    ) -> RunProgress:
        execution = store.execution_readback(inspect["run"]["run_id"])
        return RunProgress(
            run_id=inspect["run"]["run_id"],
            status=status,
            role=None if pending is None else pending["role"],
            invocation_id=None if pending is None else pending["invocation_id"],
            request_path=request_path,
            physical_model_invocations=execution["physical_model_invocations"],
            successful_model_invocations=execution["successful_model_invocations"],
            pipeline_network_calls=0,
            inspect=inspect,
        )

    def run(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> RunProgress:
        binding, store, paths = self._open(runtime_root, expected_pipeline_commit=expected_pipeline_commit)
        if store.count_rows("runs") == 0:
            self._start(binding, store)
        inspect = store.inspect()
        state = inspect["run"]["state"]
        if state != "running":
            return self._progress(store, inspect, "completed" if state == "completed" else state, None, None)
        pending = store.pending_dispatch()
        if pending is not None:
            if paths["selection"].exists():
                selected = self._selection(paths)
                if selected is not None and selected.key == pending["executor_key"]:
                    paths["selection"].unlink()
            if paths["failure"].exists():
                should_retry = self._handle_failure(store, paths, pending, inspect)
                inspect = store.inspect()
                if not should_retry:
                    return self._progress(store, inspect, "failed_invocation", None, None)
                role, actor_input, triggering_event_id, proposal = self._next_role_input(
                    binding.runtime_root, inspect
                )
                if role != pending["role"] or actor_input is None or triggering_event_id is None:
                    raise OrchestrationError("retry role/input identity changed")
                request = self._stage(
                    store,
                    paths,
                    inspect=inspect,
                    role=role,
                    actor_input=actor_input,
                    triggering_event_id=triggering_event_id,
                    proposal_to_consume=proposal,
                    binding=self.profile.executor(pending["executor_key"]),
                    delivery_id=pending["delivery_id"],
                    attempt_number=2,
                )
                inspect = store.inspect()
                return self._progress(store, inspect, "awaiting_response", request, paths["request"])
            if paths["response"].exists():
                worker_finished = self._accept_response(store, paths, pending, inspect)
                inspect = store.inspect()
                if worker_finished:
                    self._publish_and_complete(store, inspect)
                    inspect = store.inspect()
                    self.package.validate("inspect_readback", inspect)
                    return self._progress(store, inspect, "completed", None, None)
            else:
                if not paths["request"].exists():
                    required_output = self._required_output(
                        role=pending["role"],
                        invocation_id=pending["invocation_id"],
                        run_id=pending["run_id"],
                        triggering_event_id=self._triggering_event(inspect, pending["role"]),
                    )
                    self._write_atomic(paths["request"], {
                        "context_sha256": pending["context_sha256"],
                        "context_text": pending["context_text"],
                        "dispatch_id": pending["dispatch_id"],
                        "execution_mode": self.profile.execution_mode,
                        "executor_key": pending["executor_key"],
                        "extension_id": pending["extension_id"],
                        "extension_version": pending["extension_version"],
                        "invocation_id": pending["invocation_id"],
                        "manual_operator_instruction": "Do not call any tool. Return only the exact canonical JSON value in required_exact_output.",
                        "model_identifier": pending["model_identifier"],
                        "model_profile": pending["model_profile"],
                        "provider": pending["provider"],
                        "required_exact_output": required_output,
                        "role": pending["role"],
                        "run_id": pending["run_id"],
                        "tool_enforcement": pending["tool_enforcement"],
                        "type": "k0a03_manual_dispatch_request",
                    })
                    if paths["selection"].exists():
                        selected = self._selection(paths)
                        if selected is not None and selected.key == pending["executor_key"]:
                            paths["selection"].unlink()
                return self._progress(store, inspect, "awaiting_response", pending, paths["request"])
        inspect = store.inspect()
        failed = store.unresolved_manual_failure()
        if failed is not None:
            self._cleanup_failure_sidecars(paths, failed)
            if (
                failed["failure_code"] not in RETRIABLE_FAILURES
                or failed["attempt_number"] == 2
            ):
                self._fail_run(
                    store,
                    inspect["run"]["run_id"],
                    inspect["run"]["state_revision"],
                    "failed_invocation",
                )
                inspect = store.inspect()
                return self._progress(store, inspect, "failed_invocation", None, None)
            role, actor_input, triggering_event_id, proposal = self._next_role_input(
                binding.runtime_root, inspect
            )
            if (
                role != failed["role"]
                or actor_input is None
                or triggering_event_id != failed["triggering_event_id"]
            ):
                raise OrchestrationError("recovered retry role/input identity changed")
            request = self._stage(
                store,
                paths,
                inspect=inspect,
                role=role,
                actor_input=actor_input,
                triggering_event_id=triggering_event_id,
                proposal_to_consume=proposal,
                binding=self.profile.executor(failed["executor_key"]),
                delivery_id=failed["delivery_id"],
                attempt_number=2,
            )
            inspect = store.inspect()
            return self._progress(
                store, inspect, "awaiting_response", request, paths["request"]
            )
        orphan = store.orphan_invocation()
        if orphan is not None:
            request = self._recover_orphan_dispatch(
                store,
                paths,
                inspect,
                orphan,
                runtime_root=binding.runtime_root,
            )
            inspect = store.inspect()
            return self._progress(store, inspect, "awaiting_response", request, paths["request"])
        self._cleanup_completed_sidecars(store, paths, inspect)
        rejected = [
            item
            for item in inspect["proposals"]["s0"] + inspect["proposals"]["actor"]
            if item["validation_disposition"] == "rejected"
        ]
        if rejected:
            if len(rejected) != 1:
                raise OrchestrationError("more than one rejected proposal exists")
            self._fail_run(
                store,
                inspect["run"]["run_id"],
                inspect["run"]["state_revision"],
                "failed_validation",
            )
            inspect = store.inspect()
            return self._progress(store, inspect, "failed_validation", None, None)
        if any(
            item["role"] == "fixture_worker"
            and item["validation_disposition"] == "accepted"
            for item in inspect["proposals"]["actor"]
        ):
            self._publish_and_complete(store, inspect)
            inspect = store.inspect()
            self.package.validate("inspect_readback", inspect)
            return self._progress(store, inspect, "completed", None, None)
        role, actor_input, triggering_event_id, proposal = self._next_role_input(
            binding.runtime_root, inspect
        )
        if role is None:
            raise OrchestrationError("run has no pending dispatch and no publishable worker result")
        executor = self._selection(paths)
        if executor is None:
            return self._progress(store, inspect, "awaiting_executor", None, None)
        incomplete = [
            item
            for item in inspect["control_deliveries"]
            if item["role"] == role
            and item["current_physical_invocation_id"] is None
            and item["state"] == "preflight_passed"
        ]
        if len(incomplete) > 1:
            raise OrchestrationError("more than one incomplete logical delivery exists")
        request = self._stage(
            store,
            paths,
            inspect=inspect,
            role=role,
            actor_input=actor_input,
            triggering_event_id=triggering_event_id,
            proposal_to_consume=proposal,
            binding=executor,
            delivery_id=None if not incomplete else incomplete[0]["delivery_id"],
        )
        inspect = store.inspect()
        return self._progress(store, inspect, "awaiting_response", request, paths["request"])

    def inspect(
        self, runtime_root: Path, *, expected_pipeline_commit: str | None = None
    ) -> Mapping[str, Any]:
        _, store, _ = self._open(runtime_root, expected_pipeline_commit=expected_pipeline_commit)
        pipeline = store.inspect()
        self.package.validate("inspect_readback", pipeline)
        return {
            "execution": store.execution_readback(pipeline["run"]["run_id"]),
            "pipeline": pipeline,
            "type": "k0a03_full_inspect",
        }
