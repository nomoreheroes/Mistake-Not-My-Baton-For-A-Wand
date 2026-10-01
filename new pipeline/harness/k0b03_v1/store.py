from __future__ import annotations

import sqlite3
from pathlib import Path


class StoreError(ValueError):
    pass


class EvidenceStore:
    def __init__(self, database: Path):
        self.database = database

    def record_intent(self, effect_id: str, run_id: str, operation: str, envelope_sha256: str, timestamp: str) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO k0b03_effect_intents(effect_id,run_id,operation,state,envelope_sha256,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?,?)",
                (effect_id, run_id, operation, "prepared", envelope_sha256, timestamp, timestamp),
            )

    def transition_intent(self, effect_id: str, expected: str, target: str, timestamp: str, result_sha256: str | None = None) -> None:
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                "UPDATE k0b03_effect_intents SET state=?,result_sha256=?,updated_at_utc=? WHERE effect_id=? AND state=?",
                (target, result_sha256, timestamp, effect_id, expected),
            )
            if cursor.rowcount != 1:
                raise StoreError("stale or missing effect intent")

    def quarantine(self, quarantine_id: str, effect_id: str, reason_code: str, evidence_sha256: str, timestamp: str) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO k0b03_quarantine(quarantine_id,effect_id,reason_code,evidence_sha256,created_at_utc) VALUES(?,?,?,?,?)",
                (quarantine_id, effect_id, reason_code, evidence_sha256, timestamp),
            )
            connection.execute(
                "UPDATE k0b03_effect_intents SET state='quarantined',updated_at_utc=? WHERE effect_id=?",
                (timestamp, effect_id),
            )

    def unresolved(self, run_id: str) -> list[tuple[str, str]]:
        with sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True) as connection:
            return connection.execute(
                "SELECT effect_id,state FROM k0b03_effect_intents WHERE run_id=? AND state NOT IN ('completed','blocked','quarantined') ORDER BY effect_id",
                (run_id,),
            ).fetchall()
