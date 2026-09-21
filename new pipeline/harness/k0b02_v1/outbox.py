from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import require
from .store import K0b02Store


def claim(database: Path, outbox_id: str) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT decision_version_id,run_id,source_seq,projection_profile_sha256,pair_stem,status,attempts,requested_event_json FROM k0b02_projection_outbox WHERE outbox_id=?",
            (outbox_id,),
        ).fetchone()
        require(row is not None, "outbox:missing")
        if row[5] in ("written", "failed"):
            connection.commit()
            return {
                "result": "terminal_original",
                "status": row[5],
                "outbox_id": outbox_id,
            }
        attempt = row[6] + 1
        connection.execute(
            "UPDATE k0b02_projection_outbox SET status='claimed',attempts=? WHERE outbox_id=?",
            (attempt, outbox_id),
        )
        attempt_id = outbox_id + "-attempt-" + str(attempt)
        connection.execute(
            "INSERT INTO k0b02_projection_attempts(attempt_id,outbox_id,attempt_no,status,evidence_ref,created_at) VALUES(?,?,?,'begun',NULL,?)",
            (attempt_id, outbox_id, attempt, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
        return {
            "result": "claimed",
            "attempt_id": attempt_id,
            "outbox_id": outbox_id,
            "decision_version_id": row[0],
            "run_id": row[1],
            "source_seq": row[2],
            "projection_profile_sha256": row[3],
            "pair_stem": row[4],
            "requested_event_json": row[7],
        }
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
