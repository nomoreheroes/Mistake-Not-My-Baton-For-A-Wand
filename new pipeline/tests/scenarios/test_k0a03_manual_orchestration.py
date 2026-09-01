from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a02 import GuardProof, RepositoryIdentity, canonical_json, load_contract_package, sha256_text  # noqa: E402
from harness.k0a03 import K0a03Harness, K0a03Store, load_execution_profile  # noqa: E402


class FixedClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)

    def now(self) -> str:
        result = self.value.isoformat(timespec="microseconds").replace("+00:00", "Z")
        self.value += timedelta(microseconds=1)
        return result


class SequentialIds:
    def __init__(self) -> None:
        self.counter = 0

    def new(self, label: str) -> str:
        self.counter += 1
        return f"{label}-{self.counter:04d}"


@dataclass
class StaticGuard:
    proof: GuardProof

    def validate(self, **_: object) -> GuardProof:
        return self.proof


class K0a03ManualOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pipeline-v2-k0a03-")
        self.base = Path(self.temporary.name).resolve()
        self.runtime = self.base / "runtime"
        (self.runtime / "fixture").mkdir(parents=True)
        (self.runtime / ".git-placeholder").mkdir()
        (self.runtime / "fixture" / "request.yaml").write_text(
            "request_id: fixture-request-001\nintent: produce a synthetic textual result\n",
            encoding="utf-8",
            newline="\n",
        )
        package = load_contract_package()
        binding = package.fixture_binding
        proof = GuardProof(
            pipeline=RepositoryIdentity(ROOT, "a" * 40, "b" * 40, ROOT / ".git", True),
            canonical_fixture=RepositoryIdentity(
                ROOT / "projects" / "pipeline-v2-fixture",
                binding["canonical_fixture_commit"],
                binding["canonical_fixture_tree"],
                ROOT / "projects" / "pipeline-v2-fixture" / ".git",
                True,
            ),
            runtime_fixture=RepositoryIdentity(
                self.runtime,
                binding["canonical_fixture_commit"],
                binding["canonical_fixture_tree"],
                self.runtime / ".git-placeholder",
                True,
            ),
            fixture_spec_sha256=binding["fixture_spec_sha256"],
            forbidden_roots=(ROOT / "projects" / "swarm", ROOT / "research" / "old-swarm"),
            capabilities=package.capability_profile,
        )
        self.harness = K0a03Harness(
            profile=load_execution_profile(),
            guard=StaticGuard(proof),
            clock=FixedClock(),
            ids=SequentialIds(),
        )
        self.harness.initialize(self.runtime)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def operator(self) -> Path:
        return self.runtime / ".pipeline" / "runtime" / "operator"

    def write_receipt(
        self,
        *,
        tool_calls: int = 0,
        mutate_output: bool = False,
        inject_transcript_tool_event: bool = False,
        inject_duplicate_transcript_item_key: bool = False,
    ) -> dict[str, object]:
        request = json.loads((self.operator / "request.json").read_text(encoding="utf-8"))
        output = dict(request["required_exact_output"])
        if mutate_output:
            output["route"] = "forbidden"
        response_text = canonical_json(output)
        usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        transcript_events = [
            {"thread_id": "fixture-thread", "type": "thread.started"},
            {"type": "turn.started"},
            {
                "item": {"id": "item-0", "text": response_text, "type": "agent_message"},
                "type": "item.completed",
            },
            {"type": "turn.completed", "usage": usage},
        ]
        if inject_transcript_tool_event:
            transcript_events.insert(
                2,
                {
                    "item": {"id": "tool-0", "type": "command_execution"},
                    "type": "item.completed",
                },
            )
        transcript_lines = [canonical_json(event) for event in transcript_events]
        if inject_duplicate_transcript_item_key:
            transcript_lines[2] = (
                '{"item":{"id":"tool-0","type":"command_execution"},"item":'
                + canonical_json(transcript_events[2]["item"])
                + ',"type":"item.completed"}'
            )
        transcript_text = "\n".join(transcript_lines) + "\n"
        receipt = {
            "completed_at": "2026-08-31T00:00:01.000000Z",
            "dispatch_id": request["dispatch_id"],
            "duration_ms": 1000,
            "extension_id": request["extension_id"],
            "extension_version": request["extension_version"],
            "finish_reason": "stop",
            "input_tokens": 100,
            "invocation_id": request["invocation_id"],
            "model_identifier": request["model_identifier"],
            "model_profile": request["model_profile"],
            "monotonic_completed_ns": 2_000_000_000,
            "monotonic_started_ns": 1_000_000_000,
            "output_tokens": 50,
            "provider": request["provider"],
            "receipt_source": "extension_jsonl_or_ui_receipt",
            "response_sha256": sha256_text(response_text),
            "response_text": response_text,
            "started_at": "2026-08-31T00:00:00.000000Z",
            "tool_calls_observed": tool_calls,
            "total_tokens": 150,
            "transcript_event_count": len(transcript_events),
            "transcript_complete": True,
            "transcript_sha256": sha256_text(transcript_text),
            "transcript_text": transcript_text,
            "type": "k0a03_manual_response_receipt",
            "usage": usage,
        }
        (self.operator / "response.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return request

    def stage_and_accept(self, executor: str = "chatgpt_gpt_5_6_sol"):
        self.harness.write_executor_selection(self.runtime, executor)
        staged = self.harness.run(self.runtime)
        self.assertEqual(staged.status, "awaiting_response")
        self.write_receipt()
        return self.harness.run(self.runtime)

    def write_failure(self, failure_code: str) -> dict[str, object]:
        request = json.loads((self.operator / "request.json").read_text(encoding="utf-8"))
        failure = {
            "dispatch_id": request["dispatch_id"],
            "failure_code": failure_code,
            "invocation_id": request["invocation_id"],
            "receipt_source": "extension_jsonl_or_ui_receipt",
            "tool_calls_observed": 0,
            "transcript_complete": True,
            "type": "k0a03_manual_failure_receipt",
        }
        (self.operator / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return request

    def test_nominal_three_real_receipts_complete_exact_route(self) -> None:
        first = self.harness.run(self.runtime)
        self.assertEqual(first.status, "awaiting_executor")
        after_s0 = self.stage_and_accept("chatgpt_gpt_5_6_sol")
        self.assertEqual(after_s0.status, "awaiting_executor")
        after_layer0 = self.stage_and_accept("claude_opus_4_6")
        self.assertEqual(after_layer0.status, "awaiting_executor")
        completed = self.stage_and_accept("chatgpt_gpt_5_6_sol")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.physical_model_invocations, 3)
        self.assertEqual(completed.successful_model_invocations, 3)
        self.assertEqual(completed.pipeline_network_calls, 0)
        full = self.harness.inspect(self.runtime)
        pipeline = full["pipeline"]
        self.assertEqual(pipeline["run"]["state"], "completed")
        self.assertEqual(
            [event["event_type"] for event in pipeline["events"]],
            [
                "command.received",
                "run.started",
                "artifact.version_created",
                "handoff.ready",
                "run.completed",
            ],
        )
        self.assertEqual(
            [item["executor_key"] for item in full["execution"]["dispatches"]],
            ["chatgpt_gpt_5_6_sol", "claude_opus_4_6", "chatgpt_gpt_5_6_sol"],
        )
        self.assertEqual(len(pipeline["replay_points"]), 6)
        self.assertEqual(
            [item["envelope"]["capture_completeness"] for item in pipeline["replay_points"]],
            [
                "typed_gap",
                "typed_gap",
                "complete_harness_visible",
                "complete_harness_visible",
                "typed_gap",
                "typed_gap",
            ],
        )
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        self.assertEqual(store.integrity_results(), {"foreign_key_check": [], "integrity_check": "ok"})

    def test_observed_tool_call_blocks_without_publication(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt(tool_calls=1)
        with self.assertRaisesRegex(Exception, "blocked"):
            self.harness.run(self.runtime)
        full = self.harness.inspect(self.runtime)
        self.assertEqual(full["pipeline"]["run"]["state"], "blocked_policy")
        self.assertEqual(full["pipeline"]["artifact"], {})
        self.assertEqual(full["pipeline"]["publication"], {})

    def test_transcript_tool_event_blocks_even_when_operator_count_claims_zero(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt(inject_transcript_tool_event=True)
        with self.assertRaisesRegex(Exception, "zero-tool execution"):
            self.harness.run(self.runtime)
        full = self.harness.inspect(self.runtime)
        self.assertEqual(full["pipeline"]["run"]["state"], "blocked_policy")
        self.assertEqual(full["pipeline"]["artifact"], {})
        self.assertEqual(full["pipeline"]["publication"], {})

    def test_duplicate_transcript_item_key_blocks_without_publication(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt(inject_duplicate_transcript_item_key=True)
        with self.assertRaisesRegex(Exception, "zero-tool execution"):
            self.harness.run(self.runtime)
        full = self.harness.inspect(self.runtime)
        self.assertEqual(full["pipeline"]["run"]["state"], "blocked_policy")
        self.assertEqual(full["execution"]["receipts"], [])
        self.assertEqual(full["pipeline"]["artifact"], {})
        self.assertEqual(full["pipeline"]["publication"], {})

    def test_invalid_route_fails_validation_without_publication(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt(mutate_output=True)
        with self.assertRaisesRegex(Exception, "exact actor validation"):
            self.harness.run(self.runtime)
        full = self.harness.inspect(self.runtime)
        self.assertEqual(full["pipeline"]["run"]["state"], "failed_validation")
        self.assertEqual(full["pipeline"]["artifact"], {})
        self.assertEqual(len(full["execution"]["receipts"]), 1)
        self.assertEqual(full["execution"]["receipts"][0]["validation_disposition"], "rejected")
        self.assertEqual(full["execution"]["successful_model_invocations"], 0)

    def test_crash_after_rejected_proposal_resumes_terminal_validation_state(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt(mutate_output=True)
        with patch.object(
            self.harness, "_fail_run", side_effect=RuntimeError("injected reject crash")
        ):
            with self.assertRaisesRegex(RuntimeError, "injected reject crash"):
                self.harness.run(self.runtime)
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "failed_validation")
        self.assertEqual(resumed.successful_model_invocations, 0)
        self.assertEqual(resumed.inspect["artifact"], {})
        self.assertEqual(resumed.inspect["publication"], {})

    def test_named_preacceptance_failure_retries_once_with_identical_context_and_executor(self) -> None:
        self.stage_and_accept("chatgpt_gpt_5_6_sol")
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        first_request = self.write_failure("timeout_before_accepted_response")
        retry = self.harness.run(self.runtime)
        self.assertEqual(retry.status, "awaiting_response")
        second_request = json.loads((self.operator / "request.json").read_text(encoding="utf-8"))
        self.assertNotEqual(first_request["invocation_id"], second_request["invocation_id"])
        self.assertEqual(first_request["context_text"], second_request["context_text"])
        self.assertEqual(first_request["context_sha256"], second_request["context_sha256"])
        self.assertEqual(first_request["executor_key"], second_request["executor_key"])
        self.write_receipt()
        accepted = self.harness.run(self.runtime)
        self.assertEqual(accepted.status, "awaiting_executor")
        self.assertEqual(accepted.physical_model_invocations, 3)
        self.assertEqual(accepted.successful_model_invocations, 2)
        completed = self.stage_and_accept("chatgpt_gpt_5_6_sol")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.physical_model_invocations, 4)
        self.assertEqual(completed.successful_model_invocations, 3)
        full = self.harness.inspect(self.runtime)
        self.assertEqual(len(full["execution"]["failures"]), 1)
        self.assertEqual(full["pipeline"]["run"]["state"], "completed")

    def test_executor_change_is_not_consumed_during_an_active_worker(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        staged = self.harness.run(self.runtime)
        self.harness.write_executor_selection(self.runtime, "claude_opus_4_6")
        still_pending = self.harness.run(self.runtime)
        self.assertEqual(still_pending.invocation_id, staged.invocation_id)
        self.assertEqual(still_pending.physical_model_invocations, 1)
        self.assertTrue((self.operator / "next-executor.json").is_file())

    def test_second_named_failure_exhausts_retry_and_terminates_run(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_failure("timeout_before_accepted_response")
        retry = self.harness.run(self.runtime)
        self.assertEqual(retry.physical_model_invocations, 2)
        self.write_failure("timeout_before_accepted_response")
        failed = self.harness.run(self.runtime)
        self.assertEqual(failed.status, "failed_invocation")
        self.assertEqual(failed.inspect["run"]["state"], "failed_invocation")
        again = self.harness.run(self.runtime)
        self.assertEqual(again.status, "failed_invocation")
        self.assertEqual(again.physical_model_invocations, 2)

    def test_crash_after_telemetry_resumes_same_response_without_restaging(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        staged = self.harness.run(self.runtime)
        self.write_receipt()
        original = K0a03Store.record_manual_receipt
        with patch.object(K0a03Store, "record_manual_receipt", side_effect=RuntimeError("injected crash")):
            with self.assertRaisesRegex(RuntimeError, "injected crash"):
                self.harness.run(self.runtime)
        database = self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3"
        store = K0a03Store(database)
        pending = store.pending_dispatch()
        self.assertIsNotNone(pending)
        self.assertEqual(pending["invocation_id"], staged.invocation_id)
        self.assertEqual(pending["invocation_state"], "response_captured")
        self.assertIs(K0a03Store.record_manual_receipt, original)
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_executor")
        self.assertEqual(resumed.physical_model_invocations, 1)
        self.assertEqual(resumed.successful_model_invocations, 1)

    def test_crash_before_manual_dispatch_recovers_same_invocation(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        with patch.object(
            K0a03Store,
            "record_manual_dispatch",
            side_effect=RuntimeError("injected dispatch crash"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected dispatch crash"):
                self.harness.run(self.runtime)
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        orphan = store.orphan_invocation()
        self.assertIsNotNone(orphan)
        self.assertEqual(orphan["state"], "dispatched")
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_response")
        self.assertEqual(resumed.invocation_id, orphan["invocation_id"])
        self.assertEqual(resumed.physical_model_invocations, 1)
        self.write_receipt()
        accepted = self.harness.run(self.runtime)
        self.assertEqual(accepted.status, "awaiting_executor")
        self.assertEqual(accepted.successful_model_invocations, 1)

    def test_atomic_start_rolls_back_and_restart_creates_complete_run(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        original = K0a03Store._insert_start_event

        def crash_after_first_event(connection, **values: object) -> None:
            original(connection, **values)
            if values["event_type"] == "command.received":
                raise RuntimeError("injected atomic start crash")

        with patch.object(
            K0a03Store, "_insert_start_event", side_effect=crash_after_first_event
        ):
            with self.assertRaisesRegex(RuntimeError, "injected atomic start crash"):
                self.harness.run(self.runtime)
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        self.assertEqual(store.count_rows("runs"), 0)
        self.assertEqual(store.count_rows("events"), 0)
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_response")
        inspect = store.inspect()
        self.assertEqual(inspect["run"]["state"], "running")
        self.assertEqual(
            [event["event_type"] for event in inspect["events"]],
            ["command.received", "run.started"],
        )

    def test_crash_after_dispatch_rebuilds_exact_manual_request(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        original = self.harness._write_atomic

        def crash_before_request(path: Path, value: dict[str, object]) -> None:
            if path.name == "request.json":
                raise RuntimeError("injected request staging crash")
            original(path, value)

        with patch.object(self.harness, "_write_atomic", side_effect=crash_before_request):
            with self.assertRaisesRegex(RuntimeError, "injected request staging crash"):
                self.harness.run(self.runtime)
        self.assertFalse((self.operator / "request.json").exists())
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        pending = store.pending_dispatch()
        self.assertIsNotNone(pending)
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_response")
        request = json.loads((self.operator / "request.json").read_text(encoding="utf-8"))
        expected = {
            "context_sha256": pending["context_sha256"],
            "context_text": pending["context_text"],
            "dispatch_id": pending["dispatch_id"],
            "execution_mode": self.harness.profile.execution_mode,
            "executor_key": pending["executor_key"],
            "extension_id": pending["extension_id"],
            "extension_version": pending["extension_version"],
            "invocation_id": pending["invocation_id"],
            "manual_operator_instruction": "Do not call any tool. Return only the exact canonical JSON value in required_exact_output.",
            "model_identifier": pending["model_identifier"],
            "model_profile": pending["model_profile"],
            "provider": pending["provider"],
            "required_exact_output": self.harness._required_output(
                role=pending["role"],
                invocation_id=pending["invocation_id"],
                run_id=pending["run_id"],
                triggering_event_id=self.harness._triggering_event(
                    store.inspect(), pending["role"]
                ),
            ),
            "role": pending["role"],
            "run_id": pending["run_id"],
            "tool_enforcement": pending["tool_enforcement"],
            "type": "k0a03_manual_dispatch_request",
        }
        self.assertEqual(request, expected)

    def test_crash_after_atomic_temp_write_completes_matching_request(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        with patch(
            "harness.k0a03.orchestrator.os.replace",
            side_effect=RuntimeError("injected replace crash"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected replace crash"):
                self.harness.run(self.runtime)
        temporary = self.operator / ".request.json.tmp"
        self.assertTrue(temporary.is_file())
        self.assertFalse((self.operator / "request.json").exists())
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_response")
        self.assertEqual(resumed.physical_model_invocations, 1)
        self.assertTrue((self.operator / "request.json").is_file())
        self.assertFalse(temporary.exists())

    def test_matching_hardlinked_atomic_temp_fails_closed(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        with patch(
            "harness.k0a03.orchestrator.os.replace",
            side_effect=RuntimeError("injected replace crash"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected replace crash"):
                self.harness.run(self.runtime)
        temporary = self.operator / ".request.json.tmp"
        alias = self.base / "attacker-alias.json"
        os.link(temporary, alias)
        self.assertGreater(temporary.stat().st_nlink, 1)

        with self.assertRaisesRegex(
            RuntimeError, "fixed atomic-write temporary path is unsafe or differs"
        ):
            self.harness.run(self.runtime)

        self.assertFalse((self.operator / "request.json").exists())
        self.assertTrue(temporary.exists())
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        execution = store.execution_readback(store.inspect()["run"]["run_id"])
        self.assertEqual(execution["physical_model_invocations"], 1)

    def test_crash_after_request_write_consumes_only_stale_current_selection(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        original = self.harness._write_atomic

        def crash_after_request(path: Path, value: dict[str, object]) -> None:
            original(path, value)
            if path.name == "request.json":
                raise RuntimeError("injected request crash")

        with patch.object(self.harness, "_write_atomic", side_effect=crash_after_request):
            with self.assertRaisesRegex(RuntimeError, "injected request crash"):
                self.harness.run(self.runtime)
        self.assertTrue((self.operator / "request.json").exists())
        self.assertTrue((self.operator / "next-executor.json").exists())
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_response")
        self.assertEqual(resumed.physical_model_invocations, 1)
        self.assertFalse((self.operator / "next-executor.json").exists())

    def test_crash_after_response_archive_cleans_stale_request(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_receipt()
        original = self.harness._archive

        def crash_after_archive(
            source: Path, archive: Path, invocation_id: str, kind: str
        ) -> None:
            original(source, archive, invocation_id, kind)
            if kind == "response":
                raise RuntimeError("injected archive crash")

        with patch.object(self.harness, "_archive", side_effect=crash_after_archive):
            with self.assertRaisesRegex(RuntimeError, "injected archive crash"):
                self.harness.run(self.runtime)
        self.assertFalse((self.operator / "response.json").exists())
        self.assertTrue((self.operator / "request.json").exists())
        resumed = self.harness.run(self.runtime)
        self.assertEqual(resumed.status, "awaiting_executor")
        self.assertFalse((self.operator / "request.json").exists())

    def test_failure_commit_crashes_resume_retry_and_attempt_two_is_terminal(self) -> None:
        self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
        self.harness.run(self.runtime)
        self.write_failure("timeout_before_accepted_response")
        with patch.object(
            self.harness, "_stage", side_effect=RuntimeError("injected retry crash")
        ):
            with self.assertRaisesRegex(RuntimeError, "injected retry crash"):
                self.harness.run(self.runtime)
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        unresolved = store.unresolved_manual_failure()
        self.assertIsNotNone(unresolved)
        self.assertEqual(unresolved["attempt_number"], 1)
        retry = self.harness.run(self.runtime)
        self.assertEqual(retry.status, "awaiting_response")
        self.assertEqual(retry.physical_model_invocations, 2)
        self.write_failure("timeout_before_accepted_response")
        with patch.object(
            self.harness, "_fail_run", side_effect=RuntimeError("injected terminal crash")
        ):
            with self.assertRaisesRegex(RuntimeError, "injected terminal crash"):
                self.harness.run(self.runtime)
        unresolved = store.unresolved_manual_failure()
        self.assertIsNotNone(unresolved)
        self.assertEqual(unresolved["attempt_number"], 2)
        failed = self.harness.run(self.runtime)
        self.assertEqual(failed.status, "failed_invocation")
        self.assertEqual(failed.physical_model_invocations, 2)

    def test_completion_gate_rejects_missing_manual_receipt(self) -> None:
        with patch.object(K0a03Store, "record_manual_receipt", return_value=None):
            for _ in range(2):
                self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
                self.harness.run(self.runtime)
                self.write_receipt()
                progressed = self.harness.run(self.runtime)
                self.assertEqual(progressed.status, "awaiting_executor")
            self.harness.write_executor_selection(self.runtime, "chatgpt_gpt_5_6_sol")
            self.harness.run(self.runtime)
            self.write_receipt()
            with self.assertRaisesRegex(Exception, "manual transcript receipts"):
                self.harness.run(self.runtime)
        store = K0a03Store(self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3")
        inspect = store.inspect()
        self.assertEqual(inspect["run"]["state"], "running")
        self.assertEqual(inspect["events"][-1]["event_type"], "run.started")
        self.assertEqual(inspect["artifact"], {})
        self.assertEqual(inspect["publication"], {})


if __name__ == "__main__":
    unittest.main()
