from __future__ import annotations

import hashlib
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import types
from contextlib import closing
from pathlib import Path

import pytest


if "test_k0b01_v2_contracts" not in sys.modules:
    path = Path(__file__).parents[1] / "contracts/test_k0b01_v2_contracts.py"
    spec = importlib.util.spec_from_file_location("test_k0b01_v2_contracts", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

support = sys.modules["test_k0b01_v2_contracts"]
REPOSITORY = support.REPOSITORY
ctx = support.ctx
oracle = support.oracle
target = support.target
canonical = importlib.import_module("k0b01_v2.canonical")
digest = importlib.import_module("k0b01_v2.digest")
production = importlib.import_module("k0b01_v2.store")


COPY_TABLES = ("runs", "events", "run_state_transitions", "event_deliveries")
FAULTS = (
    (
        "B00.before_wal_checkpoint",
        "B01.after_wal_checkpoint",
        "B02.before_backup",
        "B03.after_backup_close",
        "B04.after_backup_verify",
        "T00.before_begin_immediate",
        "T01.after_begin_immediate",
    )
    + tuple(
        "C." + table + "." + point
        for table in COPY_TABLES
        for point in ("before", "after")
    )
    + tuple(
        "D." + table + "." + point
        for table in reversed(COPY_TABLES)
        for point in ("before", "after")
    )
    + tuple(
        "R." + table + "." + point
        for table in COPY_TABLES
        for point in ("before", "after")
    )
    + (
        "S00.before_schema_objects",
        "S01.after_schema_objects",
        "M00.before_migration_row",
        "M01.after_migration_row",
        "M02.after_user_version",
        "V00.before_integrity_checks",
        "V01.after_integrity_checks",
        "T99.immediately_before_commit",
    )
)
CRASHES = (
    ("T01.after_begin_immediate",)
    + tuple("C." + table + ".after" for table in COPY_TABLES)
    + tuple("D." + table + ".after" for table in reversed(COPY_TABLES))
    + tuple("R." + table + ".after" for table in COPY_TABLES)
    + (
        "S01.after_schema_objects",
        "M01.after_migration_row",
        "M02.after_user_version",
        "V01.after_integrity_checks",
        "T99.immediately_before_commit",
    )
)
STAMP = "2026-09-16T00:00:00+00:00"


def hash_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def insert(connection, table, **values):
    columns = ",".join('"' + column + '"' for column in values)
    connection.execute(
        "INSERT INTO "
        + table
        + "("
        + columns
        + ") VALUES("
        + ",".join("?" for _ in values)
        + ")",
        tuple(values.values()),
    )


def rich_v3(path: Path, ctx) -> None:
    """New synthetic data, explicit pinned v1..3 SQL, no old scenario dispatch."""
    assert not path.exists()
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA recursive_triggers=ON")
        for version, pin in enumerate(
            ctx.package["migration"]["historical_migrations"], 1
        ):
            for sql in production.split_statements(
                ctx.raw(pin["path"]).decode("utf-8")
            ):
                connection.execute(sql)
            insert(
                connection,
                "schema_migrations",
                version=version,
                name=Path(pin["path"]).stem,
                sha256=pin["sha256"],
            )
        connection.execute("PRAGMA user_version=3")
        connection.execute("BEGIN IMMEDIATE")
        sha, git = "a" * 64, "b" * 40
        insert(
            connection,
            "runs",
            run_id="r",
            profile="F00",
            pipeline_commit=git,
            fixture_commit=git,
            fixture_tree=git,
            state="created",
            state_revision=0,
            created_at=STAMP,
        )
        insert(
            connection,
            "run_state_transitions",
            transition_id="r0",
            run_id="r",
            from_state=None,
            to_state="created",
            from_revision=None,
            to_revision=0,
            occurred_at=STAMP,
        )
        connection.execute(
            "UPDATE runs SET state='running',state_revision=1 WHERE run_id='r'"
        )
        insert(
            connection,
            "run_state_transitions",
            transition_id="r1",
            run_id="r",
            from_state="created",
            to_state="running",
            from_revision=0,
            to_revision=1,
            occurred_at=STAMP,
        )
        specifications = [
            ("d0", "i0", "S0", 1, False),
            ("d1", "i1", "synthetic_Layer0", 1, False),
            ("d2", "if", "fixture_worker", 1, True),
            ("d2", "i2", "fixture_worker", 2, False),
        ]
        for delivery, invocation, role, attempt, failed in specifications:
            if attempt == 1:
                insert(
                    connection,
                    "deliveries",
                    delivery_id=delivery,
                    run_id="r",
                    delivery_key=delivery,
                    role=role,
                    triggering_event_id=None,
                    state="result_validated",
                    current_physical_invocation_id=None,
                    created_at=STAMP,
                )
            insert(
                connection,
                "physical_invocations",
                invocation_id=invocation,
                delivery_id=delivery,
                run_id="r",
                attempt_number=attempt,
                state="dispatched",
                prompt_id="synthetic",
                prompt_version="1",
                prompt_sha256=sha,
                contract_id="synthetic",
                contract_version="1",
                contract_sha256=sha,
                result_schema_id="synthetic",
                result_schema_version="1",
                result_schema_sha256=sha,
                registry_sha256=sha,
                provider="openai.chatgpt-vscode-extension",
                model_profile="synthetic",
                model_identifier="gpt-5.6-sol",
                parameters_json='{ "temperature" : 0 }',
                context_limit_tokens=4096,
                response_accepted=0,
                fenced=0,
                failure_code=None,
                created_at=STAMP,
            )
            connection.execute(
                "UPDATE deliveries SET current_physical_invocation_id=? WHERE delivery_id=?",
                (invocation, delivery),
            )
            insert(
                connection,
                "invocation_state_transitions",
                transition_id=invocation + "0",
                invocation_id=invocation,
                from_state=None,
                to_state="prepared",
                occurred_at=STAMP,
            )
            context_text = "synthetic context \u96ea\u03bb\x00 " + invocation
            response = "synthetic response \u00e9 " + invocation
            for position in ("before",) if failed else ("before", "after"):
                if position == "after":
                    connection.execute(
                        "UPDATE physical_invocations SET state='response_captured',response_accepted=1 WHERE invocation_id=?",
                        (invocation,),
                    )
                    insert(
                        connection,
                        "invocation_telemetry",
                        telemetry_id="t" + invocation,
                        invocation_id=invocation,
                        provider="openai.chatgpt-vscode-extension",
                        model_profile="synthetic",
                        model_identifier=None,
                        parameters_json='{ "a": 1 }',
                        response_text=response,
                        response_sha256=hash_text(response),
                        started_at=STAMP,
                        completed_at=STAMP,
                        duration_ms=1,
                        monotonic_started_ns=0,
                        monotonic_completed_ns=1000000,
                        input_tokens=1,
                        output_tokens=2,
                        total_tokens=3,
                        usage_json='{"input_tokens":1,"output_tokens":2,"total_tokens":3}',
                        finish_reason=None,
                    )
                    insert(
                        connection,
                        "manual_receipts",
                        receipt_id="mr" + invocation,
                        dispatch_id="md" + invocation,
                        invocation_id=invocation,
                        response_text=response,
                        response_sha256=hash_text(response),
                        transcript_text="SYNTHETIC TRANSCRIPT NOT MODEL EVIDENCE "
                        + invocation,
                        transcript_sha256=hash_text(
                            "SYNTHETIC TRANSCRIPT NOT MODEL EVIDENCE " + invocation
                        ),
                        transcript_event_count=4,
                        receipt_source="extension_jsonl_or_ui_receipt",
                        tool_calls_observed=0,
                        transcript_complete=1,
                        validation_disposition="accepted",
                        accepted_at=STAMP,
                    )
                sequence = connection.execute(
                    "SELECT count(*) FROM replay_points"
                ).fetchone()[0]
                insert(
                    connection,
                    "replay_points",
                    replay_point_id=invocation + position,
                    run_id="r",
                    delivery_id=delivery,
                    invocation_id=invocation,
                    attempt_number=attempt,
                    position=position,
                    sequence_number=sequence,
                    pipeline_commit=git,
                    fixture_commit=git,
                    fixture_tree=git,
                    prompt_id="synthetic",
                    prompt_version="1",
                    prompt_sha256=sha,
                    contract_id="synthetic",
                    contract_version="1",
                    contract_sha256=sha,
                    result_schema_id="synthetic",
                    result_schema_version="1",
                    result_schema_sha256=sha,
                    registry_sha256=sha,
                    context_text=context_text,
                    context_sha256=hash_text(context_text),
                    context_fragments_json='[ {"role":"user","text":"\u96ea"} ]',
                    fragment_count=1,
                    provider="synthetic",
                    model_profile="synthetic",
                    model_identifier=None,
                    parameters_json='{ "p" : 1 }',
                    capabilities_json='{"policy_version":"synthetic","model_channel":"none","filesystem_roots":[],"tools":[]}',
                    environment_json='{"os":"synthetic","architecture":"AMD64","locale":"ru","timezone":"UTC","harness_version":"1","adapter_version":"1","tool_registry_version":"1","clock_binding":"fixed","random_seed":null,"dependency_lock_sha256":"synthetic","config_sha256":"synthetic"}',
                    capture_completeness="complete_harness_visible",
                    gap_code=None,
                    result_text=response if position == "after" else None,
                    result_sha256=hash_text(response) if position == "after" else None,
                    telemetry_id="t" + invocation if position == "after" else None,
                    envelope_json='{ "synthetic" : true }',
                    envelope_sha256=hash_text('{ "synthetic" : true }'),
                    created_at=STAMP,
                )
                insert(
                    connection,
                    "replay_context_fragments",
                    replay_point_id=invocation + position,
                    ordinal=0,
                    role="user",
                    content_text=context_text,
                    content_sha256=hash_text(context_text),
                )
                if position == "before":
                    insert(
                        connection,
                        "manual_dispatches",
                        dispatch_id="md" + invocation,
                        run_id="r",
                        invocation_id=invocation,
                        delivery_id=delivery,
                        role=role,
                        executor_key="chatgpt_gpt_5_6_sol",
                        execution_mode="manual_extension_handoff_v1",
                        extension_id="openai.chatgpt",
                        extension_version="SYNTHETIC",
                        provider="openai.chatgpt-vscode-extension",
                        model_profile="synthetic",
                        model_identifier="gpt-5.6-sol",
                        tool_enforcement="contract_forbidden_audited_zero_calls",
                        context_text=context_text,
                        context_sha256=hash_text(context_text),
                        before_replay_point_id=invocation + "before",
                        created_at=STAMP,
                    )
            if failed:
                connection.execute(
                    "UPDATE physical_invocations SET state='failed_invocation',failure_code='timeout_before_accepted_response',fenced=1 WHERE invocation_id=?",
                    (invocation,),
                )
                insert(
                    connection,
                    "manual_failures",
                    failure_receipt_id="mf",
                    dispatch_id="md" + invocation,
                    invocation_id=invocation,
                    failure_code="timeout_before_accepted_response",
                    receipt_source="extension_jsonl_or_ui_receipt",
                    tool_calls_observed=0,
                    transcript_complete=1,
                    recorded_at=STAMP,
                )
            else:
                connection.execute(
                    "UPDATE physical_invocations SET state='replay_after_committed' WHERE invocation_id=?",
                    (invocation,),
                )
        insert(
            connection,
            "route_proposals",
            proposal_id="rp",
            delivery_id="d0",
            invocation_id="i0",
            raw_output_type="s0_route_proposal",
            raw_output_text="synthetic route",
            raw_output_sha256=hash_text("synthetic route"),
            validation_disposition="accepted",
            persisted_output_type="validated_route_proposal",
            terminal_state=None,
            created_at=STAMP,
        )
        insert(
            connection,
            "route_proposal_consumptions",
            consumption_id="rc",
            proposal_id="rp",
            downstream_invocation_id="i1",
            created_at=STAMP,
        )
        for role, delivery, invocation, result_type in (
            ("synthetic_Layer0", "d1", "i1", "synthetic_layer0_invocation_proposal"),
            ("fixture_worker", "d2", "i2", "fixture_worker_publication_proposal"),
        ):
            response = "synthetic response \u00e9 " + invocation
            insert(
                connection,
                "actor_proposals",
                proposal_id="ap" + invocation,
                run_id="r",
                delivery_id=delivery,
                invocation_id=invocation,
                role=role,
                raw_output_text=response,
                raw_output_sha256=hash_text(response),
                result_type=result_type,
                validation_disposition="accepted",
                terminal_state=None,
                created_at=STAMP,
            )
        insert(
            connection,
            "actor_proposal_consumptions",
            consumption_id="ac",
            proposal_id="api1",
            run_id="r",
            downstream_invocation_id="if",
            created_at=STAMP,
        )
        content = "synthetic artifact \u96ea\u03bb\x00"
        insert(
            connection,
            "artifacts",
            artifact_id="a",
            run_id="r",
            artifact_type="bootstrap.synthetic_result",
            logical_owner="fixture.bootstrap_worker",
            created_at=STAMP,
        )
        insert(
            connection,
            "artifact_versions",
            artifact_version_id="av\u96ea",
            artifact_id="a",
            run_id="r",
            producing_invocation_id="i2",
            media_type="text/plain",
            encoding="utf-8",
            schema_id="synthetic",
            schema_version="1",
            schema_sha256=sha,
            hash_profile_id="sha256-utf8-v1",
            content_text=content,
            content_sha256=hash_text(content),
            content_size_bytes=len(content.encode("utf-8")),
            idempotency_key="av-key",
            created_at=STAMP,
        )
        insert(
            connection,
            "artifact_version_lineage",
            lineage_id="lineage",
            run_id="r",
            child_artifact_version_id="av\u96ea",
            parent_ref_kind="fixture_input",
            parent_artifact_version_id=None,
            parent_external_ref="synthetic-input-not-canonical",
            relation="produced_from",
        )

        def event(event_id, event_type, parent, artifact=False):
            old_contract_pin = ctx.registry["F00_contract"]
            payloads = {
                "command.received": {
                    "run_id": "r",
                    "profile": "F00",
                    "command": "bootstrap",
                    "contract_package_sha256": old_contract_pin["sha256"],
                },
                "run.started": {"run_id": "r", "state": "running"},
                "artifact.version_created": {
                    "artifact_version_id": "av\u96ea",
                    "artifact_type": "bootstrap.synthetic_result",
                    "content_sha256": hash_text(content),
                },
                "handoff.ready": {"artifact_version_id": "av\u96ea", "profile": "F00"},
                "run.completed": {
                    "run_id": "r",
                    "state": "completed",
                    "sink_acceptance_id": "sink",
                    "readback_gate_id": "gate",
                },
            }
            payload_value = payloads[event_type]
            registry = importlib.import_module("k0b01_v2.registry_compiler")
            registry.validate_event(
                ctx,
                event_type,
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "version": "1",
                    "run_id": "r",
                    "caused_by_event_id": parent or "",
                    "correlation_id": "r",
                    "artifact_version_id": "av\u96ea" if artifact else "",
                    "payload": payload_value,
                },
            )
            payload = json.dumps(payload_value, ensure_ascii=False, indent=2) + " \t"
            insert(
                connection,
                "events",
                event_id=event_id,
                run_id="r",
                event_type=event_type,
                event_version=1,
                initiated_by_invocation_id="i2" if artifact else None,
                artifact_version_id="av\u96ea" if artifact else None,
                caused_by_event_id=parent,
                correlation_id="r",
                schema_id="synthetic",
                schema_version="1",
                schema_sha256=sha,
                payload_json=payload,
                payload_sha256=hash_text(payload),
                idempotency_key=event_id + "-key",
                created_at=STAMP,
            )
            subscriber = (
                "s0_control_delivery"
                if event_type == "command.received"
                else "bootstrap_sink"
                if event_type == "handoff.ready"
                else "bootstrap_readback"
            )
            insert(
                connection,
                "event_deliveries",
                event_delivery_id="ed" + event_id,
                event_id=event_id,
                subscriber_id=subscriber,
                terminal_policy="control_delivery"
                if subscriber == "s0_control_delivery"
                else "fixture_terminal"
                if subscriber == "bootstrap_sink"
                else "observational_terminal",
                state="pending"
                if subscriber != "bootstrap_readback"
                else "observed_terminal",
                fields_read_json=json.dumps(
                    next(
                        row["profile_branches"]["F00"]["fields_read"]
                        for row in ctx.registry["events"]
                        if row["event_type"] == event_type
                    ),
                    indent=2,
                )
                + " ",
                created_at=STAMP,
            )

        event("e0", "command.received", None)
        event("e1", "run.started", "e0")
        event("e2", "artifact.version_created", "e1", True)
        event("e3", "handoff.ready", "e2", True)
        insert(
            connection,
            "publication_transactions",
            publication_transaction_id="pub",
            run_id="r",
            invocation_id="i2",
            idempotency_key="pub-key",
            request_sha256=sha,
            artifact_version_id="av\u96ea",
            version_created_event_id="e2",
            handoff_event_id="e3",
            expected_run_revision=0,
            committed_run_revision=1,
            committed_at=STAMP,
        )
        insert(
            connection,
            "sink_acceptances",
            sink_acceptance_id="sink",
            run_id="r",
            event_delivery_id="ede3",
            handoff_event_id="e3",
            artifact_version_id="av\u96ea",
            profile="F00",
            artifact_type="bootstrap.synthetic_result",
            logical_owner="fixture.bootstrap_worker",
            media_type="text/plain",
            content_text=content,
            content_sha256=hash_text(content),
            accepted_at=STAMP,
        )
        connection.execute(
            "UPDATE event_deliveries SET state='accepted_terminal' WHERE event_delivery_id='ede3'"
        )
        connection.execute(
            "UPDATE physical_invocations SET state='published' WHERE invocation_id IN ('i0','i1','i2')"
        )
        insert(
            connection,
            "readback_gates",
            readback_gate_id="gate",
            run_id="r",
            command_event_id="e0",
            started_event_id="e1",
            version_created_event_id="e2",
            handoff_event_id="e3",
            s0_invocation_id="i0",
            layer0_invocation_id="i1",
            worker_invocation_id="i2",
            publication_transaction_id="pub",
            artifact_version_id="av\u96ea",
            sink_acceptance_id="sink",
            graph_json='{ "synthetic_connected_retry_graph":true }',
            graph_sha256=hash_text('{ "synthetic_connected_retry_graph":true }'),
            status="passed",
            checked_at=STAMP,
        )
        connection.execute(
            "UPDATE runs SET state='completed',state_revision=2 WHERE run_id='r'"
        )
        insert(
            connection,
            "run_state_transitions",
            transition_id="r2",
            run_id="r",
            from_state="running",
            to_state="completed",
            from_revision=1,
            to_revision=2,
            occurred_at=STAMP,
        )
        event("e4", "run.completed", "e3")
        connection.execute("COMMIT")
        production.integrity(connection)
        assert connection.execute("PRAGMA user_version").fetchone() == (3,)
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        assert all(
            connection.execute("SELECT count(*) FROM " + table).fetchone()[0] > 0
            for table in tables
        )


@pytest.fixture
def case(ctx, target, request):
    name = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:12]
    directory = target / ".tmp/runtime" / name
    directory.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="c", dir=directory))
    environment = "environment_A" if target.name.endswith("-a") else "environment_B"
    adapter = production.AlphaStore(ctx, target / ".tmp/runtime", environment)
    source = directory / "s.db"
    rich_v3(source, ctx)
    before = adapter.audit(source)
    return adapter, source, directory / "b.db", before


def check_recovery(adapter, source, before, version=3):
    actual = adapter.audit(source, before["historical_digest"])
    assert (
        actual["version"] == version
        and actual["payload_bytes"] == before["payload_bytes"]
    )
    with closing(production.readonly(source)) as connection:
        assert (
            production.migration_rows(connection)
            == adapter.expected.migration_rows[:version]
        )
        assert digest.schema_fingerprint(connection) == (
            adapter.expected.v3_fingerprint
            if version == 3
            else adapter.expected.v4_fingerprint
        )
        production.integrity(connection)
        assert connection.execute(
            "SELECT count(*) FROM readback_gates WHERE status='passed'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT state_revision FROM runs WHERE run_id='r'"
        ).fetchone() == (2,)
    with closing(sqlite3.connect(source, isolation_level=None)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        production.integrity(connection)
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode in ("wal", "delete")
        assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone() == (
            (0, 0, 0) if mode == "wal" else (0, -1, -1)
        )
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(source) + suffix)
        assert not sidecar.exists(), "owned recovery connection must close WAL/SHM"
    return actual


def restore_backup(adapter, backup, before):
    verified = adapter.verify_backup(backup, before["historical_digest"])
    restored = adapter.restore(backup, backup.with_name("restored.db"), verified)
    assert (
        restored["version"] == 3
        and restored["restored_artifact_sha256"] == verified["artifact_sha256"]
    )


def test_rich_v3_to_v4_success_and_repeat(case, ctx):
    adapter, source, backup, before = case
    assert adapter.metadata["exception_faults"] == list(FAULTS) and len(FAULTS) == 39
    assert (
        adapter.metadata["process_loss_faults"] == list(CRASHES) and len(CRASHES) == 18
    )
    result = adapter.initialize(
        source, backup, expected_historical=before["historical_digest"]
    )
    assert result["migrated"] is True and result["observed_boundaries"] == list(FAULTS)
    check_recovery(adapter, source, before, 4)
    restore_backup(adapter, backup, before)
    again = adapter.initialize(source, expected_historical=before["historical_digest"])
    assert again["migrated"] is False and again["live_checks_repeated"] is True
    assert production._CACHE_BUILDS[adapter.expected.key] == 1
    assert (
        len(adapter.expected.key) == 5
        and adapter.expected.key[0] == sqlite3.sqlite_version
    )
    assert not any(isinstance(item, dict) for item in adapter.expected.migration_rows)


def alpha_definitions(connection):
    rows = {
        "alpha_contract_bindings": dict(
            binding_id="b",
            contract_id="c",
            contract_version="v",
            contract_sha256="1" * 64,
            profile_id="p",
        ),
        "alpha_source_profiles": dict(
            source_profile_id="s",
            source_sha256="1" * 64,
            source_json="{}",
            runtime_enabled=0,
        ),
        "alpha_compiled_profiles": dict(
            compiled_profile_id="c",
            source_profile_id="s",
            compiled_sha256="1" * 64,
            compiled_json="{}",
            runtime_enabled=0,
        ),
        "alpha_compiler_receipts": dict(
            receipt_id="r",
            compiled_profile_id="c",
            compiler_id="compiler",
            compiler_sha256="1" * 64,
            receipt_sha256="1" * 64,
            result="pass",
        ),
        "alpha_compiled_output_families": dict(
            output_id="o",
            receipt_id="r",
            family="f",
            payload_sha256="1" * 64,
            payload_json="{}",
        ),
        "alpha_human_terminal_queue": dict(
            queue_id="h",
            event_id="e0",
            terminal_policy="block_run_and_enqueue_human",
            evidence_ref="SYNTHETIC",
            status="pending_human",
        ),
        "alpha_w5_terminal_queue": dict(
            queue_id="w",
            event_id="e1",
            terminal_policy="persist_incident_and_enqueue_W5",
            evidence_ref="SYNTHETIC",
            status="pending_W5",
        ),
    }
    for table, values in rows.items():
        insert(connection, table, **values)
    return rows


@pytest.mark.parametrize(
    "table",
    (
        "alpha_contract_bindings",
        "alpha_source_profiles",
        "alpha_compiled_profiles",
        "alpha_compiler_receipts",
        "alpha_compiled_output_families",
        "alpha_human_terminal_queue",
        "alpha_w5_terminal_queue",
    ),
)
@pytest.mark.parametrize("mutation", ("update", "delete", "duplicate", "invalid"))
def test_seven_STRICT_definitions_and_fourteen_immutable_guards(case, table, mutation):
    adapter, source, backup, before = case
    adapter.initialize(source, backup)
    with closing(sqlite3.connect(source, isolation_level=None)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        rows = alpha_definitions(connection)
        entry = next(
            row for row in connection.execute("PRAGMA table_list") if row[1] == table
        )
        assert entry[5] == 1
        with pytest.raises(sqlite3.IntegrityError):
            if mutation == "update":
                key = next(iter(rows[table]))
                connection.execute(f'UPDATE "{table}" SET "{key}"="{key}"')
            elif mutation == "delete":
                connection.execute(f'DELETE FROM "{table}"')
            else:
                values = dict(rows[table])
                if mutation == "invalid":
                    values[next(iter(values))] += "-new"
                    field = (
                        "contract_sha256"
                        if table == "alpha_contract_bindings"
                        else "runtime_enabled"
                        if table in ("alpha_source_profiles", "alpha_compiled_profiles")
                        else "result"
                        if table == "alpha_compiler_receipts"
                        else "payload_sha256"
                        if table == "alpha_compiled_output_families"
                        else "status"
                    )
                    values[field] = 1 if field == "runtime_enabled" else "invalid"
                insert(connection, table, **values)
        assert connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    check_recovery(adapter, source, before, 4)


def test_settings_order_and_transient_rename_validation_window(case, monkeypatch):
    adapter, source, backup, before = case
    original = production.rename_validation_window
    windows = []
    checks = []
    original_verify = adapter._verify
    original_configure = production.configure
    source_connections = []

    def configure(connection):
        original_configure(connection)
        source_connections.append(connection)

    def window(connection, active):
        assert (
            connection.in_transaction
            and connection.execute("PRAGMA legacy_alter_table").fetchone()[0] == 0
        )
        original(connection, active)
        windows.append(active)
        assert connection.execute("PRAGMA writable_schema").fetchone()[0] == int(active)

    def verify(connection, version, expected_historical=None):
        if connection in source_connections:
            settings = {
                name: connection.execute("PRAGMA " + name).fetchone()[0]
                for name in (
                    "busy_timeout",
                    "recursive_triggers",
                    "legacy_alter_table",
                    "journal_mode",
                    "synchronous",
                    "writable_schema",
                )
            }
            assert settings == {
                "busy_timeout": 5000,
                "recursive_triggers": 1,
                "legacy_alter_table": 0,
                "journal_mode": "wal",
                "synchronous": 2,
                "writable_schema": 0,
            }
            checks.append((version, connection.in_transaction))
        return original_verify(connection, version, expected_historical)

    monkeypatch.setattr(production, "rename_validation_window", window)
    monkeypatch.setattr(production, "configure", configure)
    monkeypatch.setattr(adapter, "_verify", verify)
    adapter.initialize(source, backup)
    assert windows == [True, False] and (4, True) in checks and checks[-1] == (4, False)
    check_recovery(adapter, source, before, 4)


def test_second_writer_is_rejected_before_any_DB_effect(case):
    adapter, source, backup, before = case
    original = {
        path.name: canonical.sha256(path.read_bytes())
        for path in source.parent.iterdir()
        if path.is_file()
    }
    lock = production._WRITER_LOCKS.setdefault(str(source), threading.Lock())
    assert lock.acquire(blocking=False)
    try:
        with pytest.raises(canonical.ContractError, match="second_writer"):
            adapter.initialize(source, backup)
    finally:
        lock.release()
    assert {
        path.name: canonical.sha256(path.read_bytes())
        for path in source.parent.iterdir()
        if path.is_file()
    } == original
    check_recovery(adapter, source, before)


@pytest.mark.parametrize("fault", FAULTS)
def test_all_39_exception_boundaries(case, fault):
    adapter, source, backup, before = case
    observed = []
    with pytest.raises(production.InjectedFault, match=fault):
        adapter.initialize(source, backup, fault=fault, observer=observed.append)
    assert observed[-1] == fault and observed == list(FAULTS[: FAULTS.index(fault) + 1])
    check_recovery(adapter, source, before)
    if backup.exists():
        restore_backup(adapter, backup, before)
    elif FAULTS.index(fault) >= FAULTS.index("B03.after_backup_close"):
        raise AssertionError("required backup missing")


@pytest.mark.parametrize("fault", CRASHES)
def test_all_18_owned_process_losses(case, ctx, target, fault):
    adapter, source, backup, before = case
    marker = source.with_name("marker.json")
    ready = marker.with_suffix(".ready")
    worker = REPOSITORY / "new pipeline/tests/k0b01_v2/migration_fault_worker.py"
    environment = "environment_A" if target.name.endswith("-a") else "environment_B"
    args = [
        sys.executable,
        "-B",
        "-I",
        str(worker),
        "--repository-root",
        str(REPOSITORY),
        "--manifest",
        str(ctx.manifest_path),
        "--source-pins",
        str(target / ".tmp/source-pins-accepted.json"),
        "--environment",
        environment,
        "--runtime-root",
        str(adapter.root.path),
        "--database",
        str(source),
        "--backup",
        str(backup),
        "--marker",
        str(marker),
        "--fault",
        fault,
    ]
    child = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 55
        while (
            not ready.exists() and child.poll() is None and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if not ready.exists():
            child.kill()
            stdout, stderr = child.communicate(timeout=10)
            pytest.fail(
                "durable owned child marker missing: "
                + stdout.decode()
                + stderr.decode()
            )
        record = json.loads(marker.read_text(encoding="utf-8"))
        assert ready.read_bytes() == b"durable marker closed\n"
        assert (
            record["parent_pid"] == child.pid
            and record["pid"] != os.getpid()
            and record["boundary"] == fault
            and record["database"] == str(source)
        )
        terminate_owned_worker(record, child.pid)
        stdout, stderr = child.communicate(timeout=10)
        assert child.returncode != 0 and stderr == b"" and fault.encode() in stdout
    finally:
        if child.poll() is None:
            if ready.exists():
                record = json.loads(marker.read_text(encoding="utf-8"))
                if (
                    record["parent_pid"] == child.pid
                    and record["database"] == str(source)
                    and record["boundary"] == fault
                ):
                    terminate_owned_worker(
                        record, child.pid, already_exited_allowed=True
                    )
            child.kill()
            child.communicate(timeout=10)
    check_recovery(adapter, source, before)
    restore_backup(adapter, backup, before)


def terminate_owned_worker(record, launcher_pid, already_exited_allowed=False):
    """Terminate only the durable-marker worker, not an inferred/global PID set."""
    assert record["parent_pid"] == launcher_pid and type(record["pid"]) is int
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    handle = kernel.OpenProcess(0x1000 | 0x0001 | 0x00100000, False, record["pid"])
    if not handle:
        assert already_exited_allowed and ctypes.get_last_error() == 87
        return
    try:
        if kernel.WaitForSingleObject(handle, 0) == 0:
            assert already_exited_allowed
            return
        image = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(image))
        assert kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
        assert Path(image.value).resolve() == Path(sys._base_executable).resolve()
        assert kernel.TerminateProcess(handle, 193)
        assert kernel.WaitForSingleObject(handle, 10000) == 0
    finally:
        assert kernel.CloseHandle(handle)


@pytest.mark.parametrize(
    "fault",
    (
        "source_equal_root",
        "source_outside",
        "backup_equal_source",
        "existing_backup",
        "missing_parent",
        "root_mismatch",
        "restore_existing",
    ),
)
def test_runtime_root_guards(case, ctx, target, fault):
    adapter, source, backup, before = case
    if fault == "root_mismatch":
        with pytest.raises(canonical.ContractError):
            production.RuntimeRoot(adapter.root.path.parent, adapter.root.path)
    elif fault == "restore_existing":
        adapter.initialize(source, backup)
        verified = adapter.verify_backup(backup, before["historical_digest"])
        with pytest.raises(canonical.ContractError):
            adapter.restore(backup, source, verified)
        check_recovery(adapter, source, before, 4)
    else:
        s, b = source, backup
        if fault == "source_equal_root":
            s = adapter.root.path
        elif fault == "source_outside":
            s = adapter.root.path.parent / "outside.db"
        elif fault == "backup_equal_source":
            b = source
        elif fault == "existing_backup":
            backup.write_bytes(b"already-owned-test-destination")
        elif fault == "missing_parent":
            b = source.parent / "missing/backup.db"
        with pytest.raises(canonical.ContractError):
            adapter.initialize(s, b)
        check_recovery(adapter, source, before)


def load_old_readers(ctx):
    """Explicit dependency modules only; no implicit harness-root traversal."""
    for name in ("harness", "harness.k0a01", "harness.k0a02", "harness.k0a03"):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = []
            sys.modules[name] = package
    modules = {}
    for name, relative in (
        ("harness.k0a01.store", "new pipeline/harness/k0a01/store.py"),
        ("harness.k0a02.security", "new pipeline/harness/k0a02/security.py"),
        ("harness.k0a02.store", "new pipeline/harness/k0a02/store.py"),
        ("harness.k0a03.store", "new pipeline/harness/k0a03/store.py"),
    ):
        ctx.raw(relative)
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, REPOSITORY / relative)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        modules[name] = sys.modules[name]
    return modules


@pytest.mark.parametrize("reader", ("k0a01", "k0a02", "k0a03"))
def test_three_exact_old_readers_reject_v4_without_writes(case, ctx, reader):
    adapter, source, backup, before = case
    adapter.initialize(source, backup)
    modules = load_old_readers(ctx)
    original_files = {
        p.name: (canonical.sha256(p.read_bytes()), p.stat().st_size)
        for p in source.parent.iterdir()
        if p.is_file()
    }
    cls = getattr(
        modules["harness." + reader + ".store"], "K0a" + reader[-2:] + "Store"
    )
    old = cls(source)
    with pytest.raises(modules["harness.k0a01.store"].MigrationError) as error:
        old.initialize()
    assert str(error.value) == "unsupported schema version 4"
    actual_files = {
        p.name: (canonical.sha256(p.read_bytes()), p.stat().st_size)
        for p in source.parent.iterdir()
        if p.is_file()
    }
    assert actual_files == original_files
    check_recovery(adapter, source, before, 4)


@pytest.mark.parametrize("kind", ("schema", "migration_row", "payload", "FK"))
def test_every_v4_initialize_rechecks_live_data(case, kind):
    adapter, source, backup, before = case
    adapter.initialize(source, backup)
    with closing(sqlite3.connect(source, isolation_level=None)) as connection:
        if kind == "schema":
            connection.execute("CREATE INDEX unapproved_idx ON runs(state)")
        elif kind == "migration_row":
            connection.execute("DROP TRIGGER schema_migrations_immutable_update")
            connection.execute(
                "UPDATE schema_migrations SET sha256='" + "0" * 64 + "' WHERE version=4"
            )
        elif kind == "payload":
            connection.execute("DROP TRIGGER events_immutable_update")
            connection.execute(
                "UPDATE events SET payload_json='{\"changed\":true}' WHERE event_id='e0'"
            )
        else:
            connection.execute("DROP TRIGGER run_state_transitions_immutable_update")
            connection.execute(
                "UPDATE run_state_transitions SET run_id='missing' WHERE transition_id='r0'"
            )
    with pytest.raises(canonical.ContractError):
        adapter.initialize(source, expected_historical=before["historical_digest"])


def test_digest_streaming_matches_independent_oracle(oracle):
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(
            "CREATE TABLE composite(k TEXT COLLATE NOCASE,n INTEGER,value ANY,PRIMARY KEY(k,n)) STRICT"
        )
        rows = [
            ("z", -1, None),
            ("a", 1, 5),
            ("a", -1, -0.0),
            ("\u96ea", 9, b"\x00\xff"),
            ("Z", 9, "\u03bb\x00\u00e9"),
        ]
        connection.executemany("INSERT INTO composite VALUES (?,?,?)", reversed(rows))
        result = digest.content_digest(
            connection, digest.historical_manifest(connection), batch_rows=2
        )
        assert result["sha256"] == oracle.typed_digest(connection, ["composite"])
        assert result["maximum_batch_rows_observed"] == 2
        assert result["tables"][0]["rows"] == 5


@pytest.mark.parametrize(
    "fault",
    ("NaN", "invalid_UTF8", "unsupported", "missing_PK", "duplicate_PK", "batch_513"),
)
def test_digest_typed_negative(fault):
    if fault in ("NaN", "invalid_UTF8", "unsupported"):
        kind, value = {
            "NaN": ("real", float("nan")),
            "invalid_UTF8": ("text", b"\xff"),
            "unsupported": ("unknown", b""),
        }[fault]
        with pytest.raises(canonical.ContractError):
            digest.cell_frame(kind, value)
        return
    with closing(sqlite3.connect(":memory:")) as connection:
        if fault == "missing_PK":
            connection.execute("CREATE TABLE no_key(v TEXT)")
            with pytest.raises(canonical.ContractError):
                digest.historical_manifest(connection)
        elif fault == "duplicate_PK":
            connection.execute("CREATE TABLE nullable(k TEXT PRIMARY KEY,v INTEGER)")
            connection.executemany("INSERT INTO nullable VALUES(NULL,?)", [(1,), (2,)])
            with pytest.raises(canonical.ContractError):
                digest.content_digest(
                    connection, digest.historical_manifest(connection)
                )
        else:
            connection.execute("CREATE TABLE keyed(k INTEGER PRIMARY KEY)")
            with pytest.raises(canonical.ContractError):
                digest.content_digest(
                    connection, digest.historical_manifest(connection), batch_rows=513
                )


@pytest.mark.parametrize("kind", ("file_symlink", "directory_junction"))
def test_reparse_escape_rejected_before_DB_access(case, kind):
    adapter, source, backup, before = case
    link = source.with_name("link" + (".db" if kind == "file_symlink" else ""))
    if kind == "file_symlink":
        link.symlink_to(source)
    else:
        import _winapi

        _winapi.CreateJunction(str(source.parent), str(link))
    try:
        assert link.lstat().st_file_attributes & 0x400
        escaped = link if kind == "file_symlink" else link / "s.db"
        with pytest.raises(canonical.ContractError, match="reparse"):
            adapter.initialize(escaped, backup)
    finally:
        assert link.lstat().st_file_attributes & 0x400
        if kind == "file_symlink":
            link.unlink()
        else:
            os.rmdir(link)
    assert source.exists() and not link.exists()
    check_recovery(adapter, source, before)


@pytest.mark.parametrize(
    "mode",
    (
        "validate-inputs",
        "compile-registry",
        "compile-budget",
        "validate-binary",
        "verify-schema",
        "migrate-synthetic",
    ),
)
def test_six_closed_CLI_modes(case, ctx, target, mode):
    adapter, source, backup, before = case
    directory = source.parent
    output = directory / "out.json"
    environment = "environment_A" if target.name.endswith("-a") else "environment_B"
    args = [
        sys.executable,
        "-B",
        "-I",
        str(REPOSITORY / "new pipeline/harness/k0b01_v2/cli.py"),
        mode,
        "--repository-root",
        str(REPOSITORY),
        "--manifest",
        str(ctx.manifest_path),
        "--source-pins",
        str(target / ".tmp/source-pins-accepted.json"),
        "--environment",
        environment,
        "--temp-target",
        str(target),
        "--output",
        str(output),
    ]
    if mode == "compile-budget":
        registry = importlib.import_module("k0b01_v2.registry_compiler")
        receipt_a = registry.compile_registry(ctx)
        (directory / "a.yaml").write_bytes(receipt_a)
        args += [
            "--receipt-a",
            str(directory / "a.yaml"),
            "--accepted-a-sha256",
            canonical.sha256(receipt_a),
            "--aggregate-output",
            str(directory / "combined.yaml"),
        ]
    elif mode == "validate-binary":
        p = ctx.json(
            next(
                pin["path"]
                for pin in ctx.source_pins
                if pin["path"].endswith("/k0b01-policy-v2.json")
            )
        )
        definition = directory / "definition.json"
        definition.write_bytes(canonical.json_bytes(p["current_binary_definition"]))
        args += ["--definition", str(definition)]
    elif mode in ("verify-schema", "migrate-synthetic"):
        args += ["--database", str(source)]
        if mode == "migrate-synthetic":
            args += ["--backup", str(backup)]
    completed = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=55,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    record = json.loads(completed.stdout)
    assert record["result"] == "pass" and record["output_sha256"] == canonical.sha256(
        output.read_bytes()
    )
    assert record["runtime_enabled"] is False
    check_recovery(adapter, source, before, 4 if mode == "migrate-synthetic" else 3)


@pytest.mark.parametrize(
    "fault",
    (
        "missing_output",
        "runtime_mode",
        "output_outside",
        "output_existing",
        "target_mismatch",
        "missing_A",
        "missing_backup",
    ),
)
def test_closed_CLI_fail_without_effect(case, ctx, target, fault):
    adapter, source, backup, before = case
    directory = source.parent
    output = directory / "out.json"
    environment = "environment_A" if target.name.endswith("-a") else "environment_B"
    mode = (
        "compile-budget"
        if fault == "missing_A"
        else "migrate-synthetic"
        if fault == "missing_backup"
        else "dispatch"
        if fault == "runtime_mode"
        else "validate-inputs"
    )
    args = [
        sys.executable,
        "-B",
        "-I",
        str(REPOSITORY / "new pipeline/harness/k0b01_v2/cli.py"),
        mode,
        "--repository-root",
        str(REPOSITORY),
        "--manifest",
        str(ctx.manifest_path),
        "--source-pins",
        str(target / ".tmp/source-pins-accepted.json"),
        "--environment",
        environment,
        "--temp-target",
        str(target / ".tmp" if fault == "target_mismatch" else target),
    ]
    if fault == "output_outside":
        args += ["--output", str(target / "not-approved-output.json")]
    elif fault != "missing_output":
        args += ["--output", str(output)]
    if fault == "output_existing":
        output.write_bytes(b"test-existing")
    if fault == "missing_backup":
        args += ["--database", str(source)]
    completed = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=55,
    )
    assert completed.returncode != 0 and not backup.exists()
    assert not output.exists() or output.read_bytes() == b"test-existing"
    check_recovery(adapter, source, before)
