from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a01 import IntegrityConflict, InvocationTelemetry, StaleState  # noqa: E402
from harness.k0a02 import (  # noqa: E402
    BootstrapSink,
    ContractValidationError,
    GuardProof,
    K0a02Harness,
    K0a02Store,
    OrchestrationError,
    RepositoryIdentity,
    ScriptedAdapter,
    canonical_json,
    load_contract_package,
    sha256_text,
)


class FixedClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)

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
    calls: int = 0

    def validate(self, **_: object) -> GuardProof:
        self.calls += 1
        return self.proof


def git_status(path: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={path.resolve()}",
            "-C",
            str(path),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


class K0a02OrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pipeline-v2-k0a02-")
        self.base = Path(self.temporary.name).resolve()
        self.package = load_contract_package()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_runtime(self, name: str = "runtime") -> Path:
        runtime = self.base / name
        (runtime / "fixture").mkdir(parents=True)
        (runtime / ".git-placeholder").mkdir()
        (runtime / "fixture" / "request.yaml").write_text(
            "request_id: fixture-request-001\nintent: produce a synthetic textual result\n",
            encoding="utf-8",
            newline="\n",
        )
        return runtime.resolve()

    def proof(self, runtime: Path) -> GuardProof:
        binding = self.package.fixture_binding
        return GuardProof(
            pipeline=RepositoryIdentity(ROOT, "a" * 40, "b" * 40, ROOT / ".git", True),
            canonical_fixture=RepositoryIdentity(
                ROOT / "projects" / "pipeline-v2-fixture",
                binding["canonical_fixture_commit"],
                binding["canonical_fixture_tree"],
                ROOT / "projects" / "pipeline-v2-fixture" / ".git",
                True,
            ),
            runtime_fixture=RepositoryIdentity(
                runtime,
                binding["canonical_fixture_commit"],
                binding["canonical_fixture_tree"],
                runtime / ".git-placeholder",
                True,
            ),
            fixture_spec_sha256=binding["fixture_spec_sha256"],
            forbidden_roots=(ROOT / "projects" / "swarm", ROOT / "research" / "old-swarm"),
            capabilities=self.package.capability_profile,
        )

    def harness(self, runtime: Path, adapter: ScriptedAdapter) -> K0a02Harness:
        return K0a02Harness(
            adapter,
            package=self.package,
            guard=StaticGuard(self.proof(runtime)),
            clock=FixedClock(),
            ids=SequentialIds(),
        )

    def command(self) -> dict[str, object]:
        return {
            "command": "bootstrap",
            "fixture_spec_sha256": self.package.fixture_binding["fixture_spec_sha256"],
            "profile": "F00",
            "type": "normalized_f00_command",
        }

    def test_nominal_scripted_route_commits_before_dispatch_and_finishes_through_sink_readback(self) -> None:
        runtime = self.make_runtime()
        db_path = runtime / ".pipeline" / "runtime" / "pipeline.sqlite3"
        dispatch_evidence: list[tuple[str, int, str]] = []

        def on_dispatch(request) -> None:
            connection = sqlite3.connect(db_path)
            try:
                state = connection.execute(
                    "SELECT state FROM physical_invocations WHERE invocation_id = ?",
                    (request.invocation_id,),
                ).fetchone()[0]
                before_count = connection.execute(
                    "SELECT count(*) FROM replay_points WHERE invocation_id = ? AND position = 'before'",
                    (request.invocation_id,),
                ).fetchone()[0]
                dispatch_evidence.append((state, before_count, request.context_sha256))
            finally:
                connection.close()

        adapter = ScriptedAdapter.nominal(self.package, on_dispatch=on_dispatch)
        harness = self.harness(runtime, adapter)
        binding = harness.initialize(runtime)
        result = harness.run(runtime, self.command())
        self.assertEqual(binding.database_path, db_path)
        self.assertEqual(result.inspect["run"]["state"], "completed")
        self.assertEqual(result.runtime_model_invocations, 0)
        self.assertEqual(result.network_calls, 0)
        self.assertEqual(len(adapter.requests), 3)
        self.assertEqual([request.role for request in adapter.requests], ["S0", "synthetic_Layer0", "fixture_worker"])
        self.assertEqual(dispatch_evidence, [("dispatched", 1, item[2]) for item in dispatch_evidence])
        self.assertTrue(all(request.capabilities["filesystem_roots"] == [] for request in adapter.requests))
        self.assertTrue(all(request.capabilities["tools"] == [] for request in adapter.requests))
        store = K0a02Store(db_path)
        self.assertEqual(store.integrity_results(), {"foreign_key_check": [], "integrity_check": "ok"})
        connection = sqlite3.connect(db_path)
        try:
            replay_ids = {
                (invocation_id, position): replay_point_id
                for invocation_id, position, replay_point_id in connection.execute(
                    "SELECT invocation_id, position, replay_point_id FROM replay_points"
                )
            }
        finally:
            connection.close()
        for request in adapter.requests:
            before = store.read_replay_envelope(replay_ids[(request.invocation_id, "before")])
            after = store.read_replay_envelope(replay_ids[(request.invocation_id, "after")])
            self.assertEqual(before["context"]["text"], request.context_text)
            self.assertEqual(before["context"]["sha256"], request.context_sha256)
            self.assertEqual(before["contract"]["sha256"], request.contract_sha256)
            self.assertEqual(before["prompt"]["sha256"], request.prompt_sha256)
            self.assertEqual(before["result_schema"]["sha256"], request.result_schema_sha256)
            self.assertEqual(before["registry_sha256"], request.package_sha256)
            self.assertIsNone(before["result"])
            self.assertEqual(after["context"], before["context"])
            self.assertEqual(after["capabilities"], before["capabilities"])
            self.assertIsNotNone(after["result"]["telemetry"]["usage"])
            self.assertEqual(after["result"]["sha256"], sha256_text(after["result"]["text"]))
        self.assertEqual(
            [event["event_type"] for event in result.inspect["events"]],
            ["command.received", "run.started", "artifact.version_created", "handoff.ready", "run.completed"],
        )
        self.assertEqual(len(result.inspect["invocations"]), 3)
        self.assertEqual(len(result.inspect["replay_points"]), 6)
        self.assertTrue(all("envelope" in point for point in result.inspect["replay_points"]))
        self.assertEqual(len(result.inspect["telemetry"]), 3)
        self.assertEqual(len(result.inspect["event_deliveries"]), 5)
        self.assertEqual(len(result.inspect["lineage"]["artifact_version_edges"]), 1)
        self.assertEqual(len(result.inspect["proposals"]["s0"]), 1)
        self.assertEqual(len(result.inspect["proposals"]["actor"]), 2)
        self.assertTrue(result.inspect["publication"])
        self.assertEqual(result.inspect["sink_acceptance"]["artifact_version_id"], result.artifact_version_id)
        self.assertEqual(result.inspect["readback_gate"]["status"], "passed")
        self.assertIn("graph", result.inspect["readback_gate"])
        self.assertEqual(harness.inspect(runtime), result.inspect)

    def test_invalid_command_causes_no_run_or_invocation_write(self) -> None:
        runtime = self.make_runtime()
        adapter = ScriptedAdapter.nominal(self.package)
        harness = self.harness(runtime, adapter)
        binding = harness.initialize(runtime)
        store = K0a02Store(binding.database_path)
        before = {table: store.count_rows(table) for table in ("runs", "events", "physical_invocations")}
        with self.assertRaises(ContractValidationError):
            harness.run(runtime, {**self.command(), "provider": "foreign"})
        after = {table: store.count_rows(table) for table in before}
        self.assertEqual(before, after)
        self.assertEqual(adapter.requests, [])

    def test_s0_blocker_abstention_malformed_unknown_or_extra_route_never_creates_layer0(self) -> None:
        responses = (
            '{"type":"semantic_blocker"}',
            '{"type":"abstention"}',
            "not-json",
            canonical_json(
                {
                    "action": "invoke",
                    "invocation_id": "wrong",
                    "route": "foreign",
                    "run_id": "wrong",
                    "triggering_event_id": "wrong",
                    "type": "s0_route_proposal",
                }
            ),
            canonical_json(
                {
                    "action": "invoke",
                    "extra": "tool",
                    "invocation_id": "wrong",
                    "route": "synthetic_Layer0",
                    "run_id": "wrong",
                    "triggering_event_id": "wrong",
                    "type": "s0_route_proposal",
                }
            ),
        )
        for index, response in enumerate(responses):
            with self.subTest(index=index):
                runtime = self.make_runtime(f"runtime-{index}")
                adapter = ScriptedAdapter({"S0": [response]})
                harness = self.harness(runtime, adapter)
                binding = harness.initialize(runtime)
                with self.assertRaises(OrchestrationError):
                    harness.run(runtime, self.command())
                connection = sqlite3.connect(binding.database_path)
                try:
                    roles = connection.execute(
                        "SELECT role FROM deliveries ORDER BY rowid"
                    ).fetchall()
                    state = connection.execute("SELECT state FROM runs").fetchone()[0]
                    proposal = connection.execute(
                        "SELECT validation_disposition, terminal_state FROM route_proposals"
                    ).fetchone()
                finally:
                    connection.close()
                self.assertEqual(roles, [("S0",)])
                self.assertEqual(state, "failed_validation")
                self.assertEqual(proposal, ("rejected", "failed_validation"))
                inspected = harness.inspect(runtime)
                self.assertEqual(inspected["run"]["state"], "failed_validation")
                self.assertEqual(inspected["artifact"], {})
                self.assertEqual(inspected["publication"], {})
                self.assertEqual(inspected["sink_acceptance"], {})
                self.assertEqual(inspected["readback_gate"], {})
                self.assertEqual(len(inspected["telemetry"]), 1)
                self.assertEqual(len(inspected["replay_points"]), 2)
                self.assertTrue(all("envelope" in point for point in inspected["replay_points"]))

    def test_wrong_identity_echo_stops_each_actor_before_next_boundary(self) -> None:
        for role in ("S0", "synthetic_Layer0", "fixture_worker"):
            with self.subTest(role=role):
                runtime = self.make_runtime(f"wrong-{role}")
                nominal = ScriptedAdapter.nominal(self.package)

                def wrong(request) -> str:
                    value = json.loads(ScriptedAdapter.nominal(self.package)._scripts[request.role][0](request))
                    value["run_id"] = "wrong-run"
                    return canonical_json(value)

                nominal._scripts[role] = [wrong]
                harness = self.harness(runtime, nominal)
                binding = harness.initialize(runtime)
                with self.assertRaises(OrchestrationError):
                    harness.run(runtime, self.command())
                connection = sqlite3.connect(binding.database_path)
                try:
                    roles = [row[0] for row in connection.execute("SELECT role FROM deliveries ORDER BY rowid")]
                    state = connection.execute("SELECT state FROM runs").fetchone()[0]
                    publication_count = connection.execute(
                        "SELECT count(*) FROM publication_transactions"
                    ).fetchone()[0]
                finally:
                    connection.close()
                expected_count = {"S0": 1, "synthetic_Layer0": 2, "fixture_worker": 3}[role]
                self.assertEqual(len(roles), expected_count)
                self.assertEqual(state, "failed_validation")
                self.assertEqual(publication_count, 0)

    def test_retry_reuses_pins_and_context_and_fences_late_attempt(self) -> None:
        runtime = self.make_runtime()
        adapter = ScriptedAdapter.nominal(
            self.package,
            first_failures={"S0": "timeout_before_accepted_response"},
        )
        harness = self.harness(runtime, adapter)
        binding = harness.initialize(runtime)
        result = harness.run(runtime, self.command())
        s0_requests = [request for request in adapter.requests if request.role == "S0"]
        self.assertEqual(len(s0_requests), 2)
        first, second = s0_requests
        self.assertNotEqual(first.invocation_id, second.invocation_id)
        self.assertEqual(first.delivery_id, second.delivery_id)
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.context_text, second.context_text)
        self.assertEqual(first.context_sha256, second.context_sha256)
        for field in (
            "prompt_sha256",
            "contract_sha256",
            "result_schema_sha256",
            "package_sha256",
            "provider",
            "model_profile",
            "model_identifier",
            "parameters",
            "capabilities",
        ):
            self.assertEqual(getattr(first, field), getattr(second, field), field)
        connection = sqlite3.connect(binding.database_path)
        try:
            fenced, state = connection.execute(
                "SELECT fenced, state FROM physical_invocations WHERE invocation_id = ?",
                (first.invocation_id,),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual((fenced, state), (1, "failed_invocation"))
        store = K0a02Store(binding.database_path)
        with self.assertRaises(StaleState):
            store.record_telemetry(
                InvocationTelemetry(
                    telemetry_id="late-telemetry",
                    invocation_id=first.invocation_id,
                    provider=first.provider,
                    model_profile=first.model_profile,
                    model_identifier=first.model_identifier,
                    parameters=first.parameters,
                    response_text="late",
                    response_sha256=sha256_text("late"),
                    started_at="2026-08-30T00:01:00Z",
                    completed_at="2026-08-30T00:01:01Z",
                    duration_ms=1000,
                    monotonic_started_ns=1_000_000_000,
                    monotonic_completed_ns=2_000_000_000,
                    input_tokens=1,
                    output_tokens=1,
                    total_tokens=2,
                    usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                    finish_reason="late",
                )
            )
        self.assertEqual(result.inspect["run"]["state"], "completed")

    def test_sink_rejects_wrong_profile_ref_hash_content_and_media(self) -> None:
        runtime = self.make_runtime()
        adapter = ScriptedAdapter.nominal(self.package)
        harness = self.harness(runtime, adapter)
        binding = harness.initialize(runtime)
        result = harness.run(runtime, self.command())
        store = K0a02Store(binding.database_path)
        artifact = result.inspect["artifact"]
        handoff = next(event for event in result.inspect["events"] if event["event_type"] == "handoff.ready")
        exact = {
            "accepted": True,
            "artifact_version_id": artifact["artifact_version_id"],
            "content_sha256": artifact["content_sha256"],
            "content_text": artifact["content_text"],
            "handoff_event_id": handoff["event_id"],
            "media_type": artifact["media_type"],
            "profile": "F00",
            "run_id": result.run_id,
            "type": "bootstrap_sink_acceptance",
        }
        variants = (
            {**exact, "profile": "F01"},
            {**exact, "handoff_event_id": "foreign"},
            {**exact, "artifact_version_id": "foreign"},
            {**exact, "content_sha256": "0" * 64},
            {**exact, "content_text": "changed", "content_sha256": sha256_text("changed")},
            {**exact, "media_type": "application/json"},
        )
        sink = BootstrapSink(self.package, store)
        for index, request in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises((ContractValidationError, IntegrityConflict)):
                    sink.accept(request, sink_acceptance_id=f"wrong-{index}", accepted_at="2026-08-30T01:00:00Z")
        self.assertEqual(store.count_rows("sink_acceptances"), 1)

    def test_completion_api_and_direct_sql_are_rejected_before_sink_readback_gate(self) -> None:
        runtime = self.make_runtime()
        harness = self.harness(runtime, ScriptedAdapter.nominal(self.package))
        binding = harness.initialize(runtime)
        store = K0a02Store(binding.database_path)
        store.create_run(
            run_id="ungated-run",
            pipeline_commit="a" * 40,
            fixture_commit=self.package.fixture_binding["canonical_fixture_commit"],
            fixture_tree=self.package.fixture_binding["canonical_fixture_tree"],
            created_at="2026-08-30T00:00:00Z",
        )
        revision = store.transition_run(
            run_id="ungated-run",
            expected_state="created",
            expected_revision=0,
            new_state="running",
            transition_id="ungated-running",
            occurred_at="2026-08-30T00:00:01Z",
        )
        event_schema = self.package.schema_identity("f00_event_envelope")
        with self.assertRaises(IntegrityConflict):
            store.complete_run(
                run_id="ungated-run",
                expected_revision=revision,
                event_id="forged-completed",
                correlation_id="correlation",
                schema_id=event_schema.id,
                schema_version=event_schema.version,
                schema_sha256=event_schema.sha256,
                idempotency_key="forged",
                occurred_at="2026-08-30T00:00:02Z",
            )
        connection = sqlite3.connect(binding.database_path)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "completion requires"):
                connection.execute("UPDATE runs SET state = 'completed' WHERE run_id = 'ungated-run'")
            connection.rollback()
        finally:
            connection.close()

    def test_publication_and_completion_require_persisted_worker_proposal(self) -> None:
        runtime = self.make_runtime()
        adapter = ScriptedAdapter.nominal(self.package)
        harness = self.harness(runtime, adapter)
        binding = harness.initialize(runtime)
        original = K0a02Store.record_actor_proposal
        calls = 0

        def omit_worker(store, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                return {}
            return original(store, *args, **kwargs)

        with patch.object(K0a02Store, "record_actor_proposal", new=omit_worker):
            with self.assertRaises(IntegrityConflict):
                harness.run(runtime, self.command())
        store = K0a02Store(binding.database_path)
        self.assertEqual(store.count_rows("publication_transactions"), 0)
        self.assertEqual(store.count_rows("artifact_versions"), 0)
        self.assertEqual(store.count_rows("readback_gates"), 0)
        inspected = harness.inspect(runtime)
        self.assertEqual(inspected["artifact"], {})
        self.assertEqual(inspected["readback_gate"], {})

    def test_terminal_sink_delivery_cannot_be_rewritten_and_inspect_revalidates_it(self) -> None:
        runtime = self.make_runtime()
        harness = self.harness(runtime, ScriptedAdapter.nominal(self.package))
        binding = harness.initialize(runtime)
        result = harness.run(runtime, self.command())
        connection = sqlite3.connect(binding.database_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE event_deliveries SET state = 'pending' "
                    "WHERE subscriber_id = 'bootstrap_sink'"
                )
            connection.rollback()
        finally:
            connection.close()
        inspected = harness.inspect(runtime)
        sink_delivery = next(
            row
            for row in inspected["event_deliveries"]
            if row["event_delivery_id"] == result.inspect["sink_acceptance"]["event_delivery_id"]
        )
        self.assertEqual(sink_delivery["state"], "accepted_terminal")

    def test_secret_or_pii_blocks_before_dispatch_or_persistence(self) -> None:
        input_runtime = self.make_runtime("sensitive-input")
        (input_runtime / "fixture" / "request.yaml").write_text(
            "api_key: synthetic-secret-material\n", encoding="utf-8", newline="\n"
        )
        input_adapter = ScriptedAdapter.nominal(self.package)
        input_harness = self.harness(input_runtime, input_adapter)
        input_harness.initialize(input_runtime)
        with self.assertRaises(OrchestrationError):
            input_harness.run(input_runtime, self.command())
        self.assertEqual([request.role for request in input_adapter.requests], ["S0", "synthetic_Layer0"])
        input_inspect = input_harness.inspect(input_runtime)
        self.assertEqual(input_inspect["run"]["state"], "blocked_policy")
        self.assertEqual(input_inspect["artifact"], {})

        output_runtime = self.make_runtime("sensitive-output")
        output_adapter = ScriptedAdapter.nominal(self.package)
        nominal_worker = output_adapter._scripts["fixture_worker"][0]

        def sensitive_worker(request) -> str:
            value = json.loads(nominal_worker(request))
            value["content_text"] = "API_KEY=synthetic-secret-material"
            value["content_sha256"] = sha256_text(value["content_text"])
            return canonical_json(value)

        output_adapter._scripts["fixture_worker"] = [sensitive_worker]
        output_harness = self.harness(output_runtime, output_adapter)
        output_binding = output_harness.initialize(output_runtime)
        with self.assertRaises(OrchestrationError):
            output_harness.run(output_runtime, self.command())
        connection = sqlite3.connect(output_binding.database_path)
        try:
            state = connection.execute("SELECT state FROM runs").fetchone()[0]
            secret_rows = connection.execute(
                "SELECT count(*) FROM invocation_telemetry "
                "WHERE response_text LIKE '%synthetic-secret-material%'"
            ).fetchone()[0]
            artifacts = connection.execute("SELECT count(*) FROM artifact_versions").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(state, "blocked_policy")
        self.assertEqual(secret_rows, 0)
        self.assertEqual(artifacts, 0)

    def test_run_and_inspect_reject_replaced_runtime_directory_junction(self) -> None:
        runtime = self.make_runtime()
        harness = self.harness(runtime, ScriptedAdapter.nominal(self.package))
        harness.initialize(runtime)
        runtime_directory = runtime / ".pipeline" / "runtime"
        escaped = self.base / "escaped-runtime-directory"
        runtime_directory.rename(escaped)
        try:
            if os.name == "nt":
                subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(runtime_directory), str(escaped)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                runtime_directory.symlink_to(escaped, target_is_directory=True)
            with self.assertRaises(OrchestrationError):
                harness.inspect(runtime)
            with self.assertRaises(OrchestrationError):
                harness.run(runtime, self.command())
        finally:
            if runtime_directory.exists() or runtime_directory.is_symlink():
                os.rmdir(runtime_directory)
            escaped.rename(runtime_directory)

    def test_canonical_fixture_swarm_and_research_are_not_written(self) -> None:
        runtime = self.make_runtime()
        fixture = ROOT / "projects" / "pipeline-v2-fixture"
        swarm = ROOT / "projects" / "swarm"
        research = ROOT / "research" / "old-swarm"
        before = {
            "fixture": git_status(fixture),
            "swarm": git_status(swarm) if swarm.exists() else "absent",
            "research_root": research.stat().st_mtime_ns if research.exists() else "absent",
        }
        adapter = ScriptedAdapter.nominal(self.package)
        harness = self.harness(runtime, adapter)
        harness.initialize(runtime)
        harness.run(runtime, self.command())
        after = {
            "fixture": git_status(fixture),
            "swarm": git_status(swarm) if swarm.exists() else "absent",
            "research_root": research.stat().st_mtime_ns if research.exists() else "absent",
        }
        self.assertEqual(before, after)
        forbidden = (str(swarm.resolve()), str(research.resolve()))
        for request in adapter.requests:
            self.assertTrue(all(path not in request.context_text for path in forbidden))
        self.assertTrue((runtime / ".pipeline" / "runtime" / "pipeline.sqlite3").is_file())

    def test_runtime_modules_have_no_provider_sdk_or_network_client_import(self) -> None:
        runtime_sources = (PIPELINE_DIR / "harness" / "k0a02").glob("*.py")
        forbidden_imports = (
            "import requests",
            "import socket",
            "import urllib",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
        )
        for source_path in runtime_sources:
            source = source_path.read_text(encoding="utf-8")
            with self.subTest(source=source_path.name):
                for forbidden in forbidden_imports:
                    self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
