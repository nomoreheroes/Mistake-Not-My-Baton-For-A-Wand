from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a01.store import MigrationError  # noqa: E402
from harness.k0a03.store import K0a03Store  # noqa: E402
from harness.k0b01 import K0B01_MIGRATION_SHA256, K0b01Store  # noqa: E402
from harness.k0b01 import store as store_module  # noqa: E402


MIGRATION_PATH = PIPELINE_DIR / "harness" / "migrations" / "0004_k0b01.sql"
COMPILER_PATH = PIPELINE_DIR / "harness" / "k0b01" / "compiler.py"
CREATED_AT = "2026-09-07T09:00:00Z"


class InjectedFailure(RuntimeError):
    pass


def _seed_v3(path: Path) -> tuple[tuple[object, ...], tuple[object, ...]]:
    K0a03Store(path).initialize()
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO runs(run_id, profile, pipeline_commit, fixture_commit, fixture_tree, state, state_revision, created_at) "
            "VALUES ('run-generated-v3', 'F00', ?, ?, ?, 'created', 0, ?)",
            ("a" * 40, "b" * 40, "c" * 40, CREATED_AT),
        )
        connection.execute(
            "INSERT INTO run_state_transitions VALUES ('transition-generated-v3', 'run-generated-v3', NULL, 'created', NULL, 0, ?)",
            (CREATED_AT,),
        )
        connection.execute(
            "INSERT INTO events("
            "event_id, run_id, event_type, event_version, initiated_by_invocation_id, artifact_version_id, "
            "caused_by_event_id, correlation_id, schema_id, schema_version, schema_sha256, payload_json, "
            "payload_sha256, idempotency_key, created_at"
            ") VALUES (?, ?, ?, 1, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "event-generated-v3",
                "run-generated-v3",
                "command.received",
                "correlation-generated-v3",
                "pipeline-v2.command-received",
                "1.0.0",
                "d" * 64,
                "{}",
                sha256(b"{}").hexdigest(),
                "generated-command-key",
                CREATED_AT,
            ),
        )
        connection.commit()
        run = connection.execute(
            "SELECT * FROM runs WHERE run_id = 'run-generated-v3'"
        ).fetchone()
        event = connection.execute(
            "SELECT * FROM events WHERE event_id = 'event-generated-v3'"
        ).fetchone()
        assert run is not None and event is not None
        return tuple(run), tuple(event)
    finally:
        connection.close()


class K0b01MigrationTests(unittest.TestCase):
    def test_exact_forward_upgrade_preserves_v3_and_creates_verified_backup(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-migration-") as temporary:
            root = Path(temporary)
            database = root / "state.sqlite3"
            backup = root / "pre-v4.sqlite3"
            run_before, event_before = _seed_v3(database)
            store = K0b01Store(database, backup_path=backup)
            self.assertEqual(store.initialize(), K0B01_MIGRATION_SHA256)
            self.assertIsNotNone(store.last_backup_receipt)
            assert store.last_backup_receipt is not None
            self.assertEqual(store.last_backup_receipt.path, backup.resolve())
            self.assertEqual(
                store.last_backup_receipt.sha256,
                sha256(backup.read_bytes()).hexdigest(),
            )
            self.assertEqual(len(store.last_backup_receipt.content_sha256), 64)
            self.assertEqual(store.last_backup_receipt.table_counts["runs"], 1)
            self.assertEqual(store.last_backup_receipt.table_counts["events"], 1)
            source = sqlite3.connect(database)
            backup_connection = sqlite3.connect(backup)
            try:
                self.assertEqual(source.execute("PRAGMA user_version").fetchone()[0], 4)
                self.assertEqual(
                    backup_connection.execute("PRAGMA user_version").fetchone()[0], 3
                )
                self.assertEqual(
                    tuple(
                        source.execute(
                            "SELECT * FROM runs WHERE run_id = 'run-generated-v3'"
                        ).fetchone()
                    ),
                    run_before,
                )
                self.assertEqual(
                    tuple(
                        source.execute(
                            "SELECT * FROM events WHERE event_id = 'event-generated-v3'"
                        ).fetchone()
                    ),
                    event_before,
                )
                self.assertEqual(
                    tuple(
                        backup_connection.execute(
                            "SELECT * FROM runs WHERE run_id = 'run-generated-v3'"
                        ).fetchone()
                    ),
                    run_before,
                )
                self.assertEqual(
                    source.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )
                self.assertEqual(
                    source.execute("PRAGMA foreign_key_check").fetchall(), []
                )
            finally:
                source.close()
                backup_connection.close()
            restored_path = root / "restored-v3.sqlite3"
            backup_connection = sqlite3.connect(backup)
            restored_connection = sqlite3.connect(restored_path)
            try:
                backup_connection.backup(restored_connection)
                self.assertEqual(
                    restored_connection.execute("PRAGMA user_version").fetchone()[0], 3
                )
                self.assertEqual(
                    tuple(
                        restored_connection.execute(
                            "SELECT * FROM events WHERE event_id = 'event-generated-v3'"
                        ).fetchone()
                    ),
                    event_before,
                )
                self.assertEqual(
                    restored_connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            finally:
                restored_connection.close()
                backup_connection.close()
            self.assertEqual(store.initialize(), K0B01_MIGRATION_SHA256)
            with self.assertRaisesRegex(MigrationError, "unsupported schema version 4"):
                K0a03Store(database).initialize()

    def test_schema_v3_requires_explicit_new_backup_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-no-backup-") as temporary:
            database = Path(temporary) / "state.sqlite3"
            _seed_v3(database)
            with self.assertRaisesRegex(MigrationError, "explicit new backup path"):
                K0b01Store(database).initialize()
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone()[0], 3
                )
            finally:
                connection.close()

    def test_changed_migration_bytes_fail_before_backup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-stale-migration-") as temporary:
            root = Path(temporary)
            database = root / "state.sqlite3"
            backup = root / "pre-v4.sqlite3"
            changed = root / "0004_changed.sql"
            _seed_v3(database)
            changed.write_bytes(MIGRATION_PATH.read_bytes() + b"\n-- changed\n")
            with self.assertRaisesRegex(MigrationError, "committed bytes changed"):
                K0b01Store(
                    database, backup_path=backup, migration_0004_path=changed
                ).initialize()
            self.assertFalse(backup.exists())

    def test_failure_after_backup_rolls_back_every_v4_statement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-rollback-") as temporary:
            root = Path(temporary)
            database = root / "state.sqlite3"
            backup = root / "pre-v4.sqlite3"
            changed = root / "0004_failing.sql"
            _seed_v3(database)
            changed.write_bytes(
                MIGRATION_PATH.read_bytes()
                + b"SELECT * FROM table_that_does_not_exist;\n"
            )
            changed_hash = sha256(changed.read_bytes()).hexdigest()
            with (
                mock.patch.object(store_module, "K0B01_MIGRATION_SHA256", changed_hash),
                mock.patch.object(
                    K0b01Store,
                    "_expected_k0b01_schema",
                    return_value="not_reached_after_failure",
                ),
            ):
                with self.assertRaises(sqlite3.DatabaseError):
                    K0b01Store(
                        database, backup_path=backup, migration_0004_path=changed
                    ).initialize()
            self.assertTrue(backup.exists())
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone()[0], 3
                )
                self.assertIsNone(
                    connection.execute(
                        "SELECT name FROM sqlite_schema WHERE name = 'k0b_contract_profile_bindings'"
                    ).fetchone()
                )
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )
            finally:
                connection.close()

    def test_faults_at_each_migration_boundary_leave_exact_v3(self) -> None:
        points = {
            "before_backup": False,
            "after_backup": True,
            "during_schema_application": True,
            "before_migration_row_insert": True,
            "before_commit": True,
        }
        for point, backup_expected in points.items():
            with (
                self.subTest(point=point),
                tempfile.TemporaryDirectory(
                    prefix=f"k0b01-fault-{point}-"
                ) as temporary,
            ):
                root = Path(temporary)
                database = root / "state.sqlite3"
                backup = root / "pre-v4.sqlite3"
                run_before, event_before = _seed_v3(database)

                def inject(actual: str) -> None:
                    if actual == point:
                        raise InjectedFailure(point)

                with self.assertRaisesRegex(InjectedFailure, point):
                    K0b01Store(database, backup_path=backup).initialize(
                        fault_hook=inject
                    )
                self.assertEqual(backup.exists(), backup_expected)
                connection = sqlite3.connect(database)
                try:
                    self.assertEqual(
                        connection.execute("PRAGMA user_version").fetchone()[0], 3
                    )
                    self.assertEqual(
                        tuple(
                            connection.execute(
                                "SELECT * FROM runs WHERE run_id = 'run-generated-v3'"
                            ).fetchone()
                        ),
                        run_before,
                    )
                    self.assertEqual(
                        tuple(
                            connection.execute(
                                "SELECT * FROM events WHERE event_id = 'event-generated-v3'"
                            ).fetchone()
                        ),
                        event_before,
                    )
                    self.assertIsNone(
                        connection.execute(
                            "SELECT name FROM sqlite_schema "
                            "WHERE name = 'k0b_contract_profile_bindings'"
                        ).fetchone()
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                    )
                finally:
                    connection.close()

    def test_missing_extra_and_reidentified_migration_records_fail_closed(self) -> None:
        mutations = {
            "missing": (
                "DROP TRIGGER schema_migrations_immutable_delete",
                "DELETE FROM schema_migrations WHERE version = 2",
            ),
            "extra": (
                "INSERT INTO schema_migrations(version, name, sha256) "
                "VALUES (99, '0099_extra', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')",
            ),
            "reidentified": (
                "DROP TRIGGER schema_migrations_immutable_update",
                "UPDATE schema_migrations SET name = '0002_reidentified' WHERE version = 2",
            ),
        }
        for label, statements in mutations.items():
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory(
                    prefix=f"k0b01-history-{label}-"
                ) as temporary,
            ):
                root = Path(temporary)
                database = root / "state.sqlite3"
                K0b01Store(database, backup_path=root / "pre-v4.sqlite3").initialize()
                connection = sqlite3.connect(database)
                try:
                    for statement in statements:
                        connection.execute(statement)
                    connection.commit()
                finally:
                    connection.close()
                with self.assertRaisesRegex(
                    MigrationError,
                    "migration identities are incomplete, stale, or extra",
                ):
                    K0b01Store(database).initialize()

    def test_compiled_bundle_persistence_is_atomic_immutable_and_idempotent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-persistence-") as temporary:
            root = Path(temporary)
            store = K0b01Store(
                root / "state.sqlite3", backup_path=root / "pre-v4.sqlite3"
            )
            store.initialize()
            compiler_hash = sha256(COMPILER_PATH.read_bytes()).hexdigest()
            with self.assertRaisesRegex(MigrationError, "compiler SHA-256 differs"):
                store.record_compiled_bundle(
                    binding_id="binding-invalid-compiler",
                    compiler_sha256="0" * 64,
                    created_at=CREATED_AT,
                )
            self.assertEqual(
                store.k0b01_counts("binding-invalid-compiler")["bindings"], 0
            )
            digest = store.record_compiled_bundle(
                binding_id="binding-alpha0-v1",
                compiler_sha256=compiler_hash,
                created_at=CREATED_AT,
            )
            self.assertEqual(len(digest), 64)
            self.assertEqual(
                dict(store.k0b01_counts("binding-alpha0-v1")),
                {
                    "bindings": 1,
                    "compiled_outputs": 8,
                    "events": 21,
                    "subscription_routes": 16,
                    "s_routes": 5,
                    "budget_cases": 2,
                },
            )
            self.assertEqual(
                store.record_compiled_bundle(
                    binding_id="binding-alpha0-v1",
                    compiler_sha256=compiler_hash,
                    created_at=CREATED_AT,
                ),
                digest,
            )
            with self.assertRaisesRegex(MigrationError, "reused with different bytes"):
                store.record_compiled_bundle(
                    binding_id="binding-alpha0-v1",
                    compiler_sha256=compiler_hash,
                    created_at="2026-09-07T09:01:00Z",
                )
            connection = sqlite3.connect(root / "state.sqlite3")
            try:
                stored_event = connection.execute(
                    "SELECT payload_schema_sha256, allowed_subscribers_json, fields_consumed_json, "
                    "terminal_policy, terminal_disposition FROM k0b_event_type_definitions "
                    "WHERE binding_id = 'binding-alpha0-v1' AND event_type = 'command.received'"
                ).fetchone()
                self.assertIsNotNone(stored_event)
                assert stored_event is not None
                self.assertEqual(len(stored_event[0]), 64)
                self.assertEqual(
                    stored_event[1], '["shared_control.command_admission"]'
                )
                self.assertEqual(
                    stored_event[2], '["command_id","profile","authority_refs"]'
                )
                self.assertIsNone(stored_event[3])
                self.assertEqual(stored_event[4], "subscriber_snapshot")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE k0b_event_type_definitions SET producer_owner = 'other' "
                        "WHERE binding_id = 'binding-alpha0-v1' AND event_type = 'command.received'"
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO k0b_event_type_definitions("
                        "binding_id, event_type, event_version, payload_schema_id, "
                        "payload_schema_version, payload_schema_sha256, producer_owner, route_ref, "
                        "allowed_subscribers_json, terminal_policy, fields_consumed_json, "
                        "activation_work_item, replay_semantics, idempotency_scope, terminal_disposition"
                        ") VALUES (?, ?, 1, ?, 1, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                        (
                            "binding-alpha0-v1",
                            "unknown.twenty_second_event",
                            "pipeline-v2.unknown",
                            "a" * 64,
                            "shared_control",
                            "alpha0.control.command",
                            '["shared_control.command_admission"]',
                            '["command_id"]',
                            "K0b-01",
                            "append_once",
                            "run_event_type_key",
                            "subscriber_snapshot",
                        ),
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO k0b_subscription_terminal_definitions "
                        "VALUES (?, ?, 'subscriber', '[\"shared_control.command_admission\"]', "
                        "NULL, '[\"command_id\"]', 'K0b-01')",
                        ("binding-alpha0-v1", "alpha0.unknown.seventeenth_route"),
                    )
            finally:
                connection.close()

    def test_forbidden_fixture_path_is_rejected_without_opening_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-path-") as temporary:
            forbidden = Path(temporary) / "tests" / "fixtures" / "state.sqlite3"
            forbidden.parent.mkdir(parents=True)
            with self.assertRaisesRegex(MigrationError, "forbidden root"):
                K0b01Store(
                    forbidden, backup_path=Path(temporary) / "backup.sqlite3"
                ).initialize()
            self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()
