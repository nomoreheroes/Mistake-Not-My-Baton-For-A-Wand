from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a01 import ArtifactPublication, MigrationError  # noqa: E402
from harness.k0a02 import K0a02Store, SensitiveDataError, sha256_text  # noqa: E402
from harness.k0a02.store import K0A01_MIGRATION_SHA256, K0A02_MIGRATION_SHA256  # noqa: E402


MIGRATION_0001 = PIPELINE_DIR / "harness" / "migrations" / "0001_k0a01.sql"
MIGRATION_0002 = PIPELINE_DIR / "harness" / "migrations" / "0002_k0a02.sql"


class K0a02StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pipeline-v2-k0a02-store-")
        self.db_path = Path(self.temporary.name) / "pipeline.sqlite3"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_forward_migrations_are_exact_deterministic_and_reinitializable(self) -> None:
        store = K0a02Store(self.db_path)
        migration_hash = store.initialize()
        fingerprint = store.schema_fingerprint()
        self.assertEqual(store.initialize(), migration_hash)
        self.assertEqual(store.schema_fingerprint(), fingerprint)
        self.assertEqual(
            store.migration_records(),
            (
                {"version": 1, "name": "0001_k0a01", "sha256": K0A01_MIGRATION_SHA256},
                {"version": 2, "name": "0002_k0a02", "sha256": K0A02_MIGRATION_SHA256},
            ),
        )
        self.assertEqual(store.integrity_results(), {"foreign_key_check": [], "integrity_check": "ok"})

    def test_changed_0002_bytes_are_rejected_after_initialization(self) -> None:
        store = K0a02Store(self.db_path)
        store.initialize()
        changed = Path(self.temporary.name) / "0002-changed.sql"
        changed.write_bytes(MIGRATION_0002.read_bytes() + b"\n")
        with self.assertRaises(MigrationError):
            K0a02Store(self.db_path, migration_0002_path=changed).initialize()

    def test_changed_0002_bytes_are_rejected_for_a_fresh_database(self) -> None:
        changed = Path(self.temporary.name) / "0002-changed-fresh.sql"
        changed.write_bytes(MIGRATION_0002.read_bytes() + b"\n")
        with self.assertRaises(MigrationError):
            K0a02Store(
                Path(self.temporary.name) / "fresh.sqlite3", migration_0002_path=changed
            ).initialize()

    def test_changed_historical_0001_bytes_are_rejected_without_rewriting_record(self) -> None:
        store = K0a02Store(self.db_path)
        store.initialize()
        changed = Path(self.temporary.name) / "0001-changed.sql"
        changed.write_bytes(MIGRATION_0001.read_bytes() + b"\n")
        with self.assertRaises(MigrationError):
            K0a02Store(self.db_path, migration_0001_path=changed).initialize()
        self.assertEqual(store.migration_records()[0]["sha256"], K0A01_MIGRATION_SHA256)

    def test_live_schema_drift_is_rejected(self) -> None:
        store = K0a02Store(self.db_path)
        store.initialize()
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("CREATE TABLE drift(value TEXT) STRICT")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(MigrationError):
            store.initialize()

    def test_0001_committed_bytes_and_effective_attributes_remain_unchanged(self) -> None:
        import hashlib
        import subprocess

        self.assertEqual(hashlib.sha256(MIGRATION_0001.read_bytes()).hexdigest(), K0A01_MIGRATION_SHA256)
        attributes = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "check-attr",
                "text",
                "eol",
                "--",
                "new pipeline/harness/migrations/0001_k0a01.sql",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn("text: set", attributes)
        self.assertIn("eol: lf", attributes)

    def test_artifact_writer_rejects_secret_before_opening_database(self) -> None:
        content = "API_KEY=synthetic-secret-material"
        publication = ArtifactPublication(
            publication_transaction_id="publication",
            idempotency_key="publication-key",
            run_id="run",
            expected_run_revision=0,
            invocation_id="worker",
            artifact_id="artifact",
            artifact_version_id="version",
            content_text=content,
            content_sha256=sha256_text(content),
            media_type="text/plain",
            schema_id="schema",
            schema_version="1.0.0",
            schema_sha256="0" * 64,
            correlation_id="correlation",
            caused_by_event_id="started",
            version_created_event_id="version-event",
            version_created_idempotency_key="version-event-key",
            handoff_event_id="handoff-event",
            handoff_idempotency_key="handoff-event-key",
            event_schema_id="event-schema",
            event_schema_version="1.0.0",
            event_schema_sha256="0" * 64,
            lineage=(),
            created_at="2026-08-30T00:00:00Z",
        )
        with self.assertRaises(SensitiveDataError):
            K0a02Store(self.db_path).publish_artifact_version(publication)
        self.assertFalse(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
