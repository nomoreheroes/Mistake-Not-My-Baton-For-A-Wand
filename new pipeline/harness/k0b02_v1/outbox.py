from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import require
from .store import K0b02Store, runtime_profile


def claim(database: Path, outbox_id: str) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT o.decision_version_id,o.run_id,o.source_seq,o.projection_profile_sha256,o.pair_stem,o.status,o.attempts,o.requested_event_json,"
            "b.phase_id,b.partition_digest,d.phase_id,d.partition_digest "
            "FROM k0b02_projection_outbox AS o "
            "LEFT JOIN k0b02_outbox_phase_bindings AS b ON b.outbox_id=o.outbox_id "
            "JOIN k0b02_decision_versions AS d ON d.decision_version_id=o.decision_version_id "
            "WHERE o.outbox_id=?",
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
        profile = runtime_profile(connection)
        require(
            row[8] in profile["phases"] and row[8] == row[10] and row[9] == row[11],
            "outbox:phase_binding",
        )
        lower = connection.execute(
            "SELECT outbox_id FROM k0b02_projection_outbox "
            "WHERE run_id=? AND source_seq<? AND status IN ('pending','claimed') "
            "ORDER BY source_seq,outbox_id LIMIT 1",
            (row[1], row[2]),
        ).fetchone()
        require(lower is None, "outbox:claim_order")
        require(row[6] < profile["projection_attempt_cap"], "outbox:attempt_cap")
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
