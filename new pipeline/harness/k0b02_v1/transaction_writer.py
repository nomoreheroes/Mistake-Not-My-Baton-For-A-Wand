from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import json_bytes, require, sha256
from .store import K0b02Store


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + "-" + sha256(json_bytes(list(parts)))[:32]


def ensure_run(connection: Any, run_id: str) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO runs(run_id,profile,pipeline_commit,fixture_commit,fixture_tree,state,state_revision,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (run_id, "Alpha0", "0" * 40, "0" * 40, "0" * 40, "running", 0, now()),
    )


def admit(
    database: Path,
    intent: dict[str, Any],
    observer: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    require(intent["pair_stem"] == "fixture-decision", "writer:pair_stem")
    canonical, digest = json_bytes(intent), sha256(json_bytes(intent))
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        ensure_run(connection, intent["run_id"])
        existing = connection.execute(
            "SELECT decision_version_id,source_seq,canonical_sha256 FROM k0b02_decision_versions WHERE decision_version_id=?",
            (intent["decision_version_id"],),
        ).fetchone()
        if existing:
            require(existing[2] == digest, "writer:conflicting_duplicate")
            row = connection.execute(
                "SELECT outbox_id,requested_event_json FROM k0b02_projection_outbox WHERE decision_version_id=?",
                (intent["decision_version_id"],),
            ).fetchone()
            connection.commit()
            return {
                "result": "duplicate_original",
                "decision_version_id": existing[0],
                "source_seq": existing[1],
                "outbox_id": row[0],
                "event": json.loads(row[1]),
            }
        seq = connection.execute(
            "SELECT next_source_seq FROM k0b02_source_sequences WHERE run_id=?",
            (intent["run_id"],),
        ).fetchone()
        source_seq = seq[0] if seq else 1
        if seq:
            connection.execute(
                "UPDATE k0b02_source_sequences SET next_source_seq=? WHERE run_id=?",
                (source_seq + 1, intent["run_id"]),
            )
        else:
            connection.execute(
                "INSERT INTO k0b02_source_sequences(run_id,next_source_seq,receipt_high_water) VALUES(?,?,0)",
                (intent["run_id"], 2),
            )
        require(intent["source_seq"] == source_seq, "writer:source_seq")
        event_id = stable_id(
            "event", intent["run_id"], intent["decision_version_id"], str(source_seq)
        )
        outbox_id = stable_id("outbox", event_id)
        payload = {
            "run_id": intent["run_id"],
            "decision_version_id": intent["decision_version_id"],
            "pair_stem": intent["pair_stem"],
            "projection_profile_sha256": intent["projection_profile_sha256"],
        }
        event = {
            "event_id": event_id,
            "event_type": "projection.requested",
            "event_version": 1,
            "payload": payload,
            "idempotency_key": "|".join(
                [
                    intent["run_id"],
                    "v1",
                    intent["decision_version_id"],
                    intent["projection_profile_sha256"],
                ]
            ),
        }
        connection.execute(
            "INSERT INTO k0b02_decision_versions(decision_version_id,run_id,phase_id,partition_digest,source_seq,canonical_sha256,canonical_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                intent["decision_version_id"],
                intent["run_id"],
                intent["phase_id"],
                intent["partition_digest"],
                source_seq,
                digest,
                canonical.decode().strip(),
                now(),
            ),
        )
        connection.execute(
            "INSERT INTO events(event_id,run_id,event_type,event_version,initiated_by_invocation_id,artifact_version_id,caused_by_event_id,correlation_id,schema_id,schema_version,schema_sha256,payload_json,payload_sha256,idempotency_key,created_at) VALUES(?,?,?,?,NULL,NULL,NULL,?,?,?,?,?,?,?,?)",
            (
                event_id,
                intent["run_id"],
                "projection.requested",
                1,
                intent["correlation_id"],
                "pipeline-v2.alpha0.event.projection.requested.v1",
                "1",
                "1a8735a7c8f35415f7eb8dd3f958740e31f2c1521b7fdbe75a9b3245c0c30454",
                json_bytes(payload).decode().strip(),
                sha256(json_bytes(payload)),
                event["idempotency_key"],
                now(),
            ),
        )
        connection.execute(
            "INSERT INTO k0b02_projection_outbox(outbox_id,decision_version_id,run_id,source_seq,projection_profile_sha256,pair_stem,requested_event_json,status,attempts,created_at) VALUES(?,?,?,?,?,?,?,'pending',0,?)",
            (
                outbox_id,
                intent["decision_version_id"],
                intent["run_id"],
                source_seq,
                intent["projection_profile_sha256"],
                intent["pair_stem"],
                json_bytes(event).decode().strip(),
                now(),
            ),
        )
        if observer:
            observer("decision_outbox_before_commit")
        connection.commit()
        if observer:
            observer("decision_outbox_after_commit_before_response")
        return {
            "result": "created",
            "decision_version_id": intent["decision_version_id"],
            "source_seq": source_seq,
            "outbox_id": outbox_id,
            "event": event,
        }
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
