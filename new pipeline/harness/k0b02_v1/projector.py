from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import json_bytes, require, sha256
from .store import K0b02Store, runtime_profile
from .transaction_writer import stable_id


def _write_candidate(candidate: Path, target: Path, raw: bytes) -> None:
    require(
        candidate.parent == target.parent and candidate.name.startswith("."),
        "projector:temp_identity",
    )
    require(
        not candidate.exists() and not candidate.is_symlink(), "projector:temp_exists"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with candidate.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(candidate.read_bytes() == raw, "projector:candidate_readback")
    os.replace(candidate, target)
    with target.open("r+b") as stream:
        os.fsync(stream.fileno())


def _markdown(
    source: dict[str, Any], source_raw: bytes, profile_sha: str, pair_stem: str
) -> bytes:
    body = json.dumps(source, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    text = (
        "# "
        + pair_stem
        + "\n\n"
        + "Pipeline-Source-SHA256: "
        + sha256(source_raw)
        + "\n"
        + "Pipeline-Projection-Profile-SHA256: "
        + profile_sha
        + "\n\n"
        + "## Complete canonical source\n\n```json\n"
        + body
        + "```\n"
    )
    return text.encode("utf-8")


def project(
    database: Path,
    outbox_id: str,
    repository: Path,
    observer: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    row = None
    recordable = False
    terminal_existing = False
    try:
        profile = runtime_profile(connection)
        row = connection.execute(
            "SELECT decision_version_id,run_id,source_seq,projection_profile_sha256,pair_stem,status,requested_event_json FROM k0b02_projection_outbox WHERE outbox_id=?",
            (outbox_id,),
        ).fetchone()
        require(row is not None and row[4] == profile["pair_stem"], "projector:outbox")
        yaml_path, markdown_path = profile["pair_paths"]
        recordable = True
        existing = connection.execute(
            "SELECT projection_id,yaml_sha256,markdown_sha256,ready FROM k0b02_projection_pairs WHERE outbox_id=?",
            (outbox_id,),
        ).fetchone()
        if existing:
            terminal_existing = True
            require(existing[3] == 1, "projector:partial_ready")
            yaml_target = repository / yaml_path
            md_target = repository / markdown_path
            require(
                sha256(yaml_target.read_bytes()) == existing[1]
                and sha256(md_target.read_bytes()) == existing[2],
                "projector:existing_pair_drift",
            )
            return {
                "result": "original",
                "projection_id": existing[0],
                "yaml_sha256": existing[1],
                "markdown_sha256": existing[2],
                "ready": True,
            }
        decision = connection.execute(
            "SELECT canonical_json FROM k0b02_decision_versions WHERE decision_version_id=?",
            (row[0],),
        ).fetchone()
        require(decision is not None, "projector:decision")
        source_raw = (decision[0] + "\n").encode("utf-8")
        source = json.loads(decision[0])
        yaml_raw = json_bytes(source)
        markdown_raw = _markdown(source, source_raw, row[3], profile["pair_stem"])
        yaml_target = repository / yaml_path
        md_target = repository / markdown_path
        yaml_temp = yaml_target.with_name("." + yaml_target.name + ".tmp")
        md_temp = md_target.with_name("." + md_target.name + ".tmp")
        _write_candidate(yaml_temp, yaml_target, yaml_raw)
        if observer:
            observer("first_peer_replaced")
        _write_candidate(md_temp, md_target, markdown_raw)
        if observer:
            observer("both_peers_replaced_before_result")
        require(
            yaml_target.read_bytes() == yaml_raw
            and md_target.read_bytes() == markdown_raw,
            "projector:peer_readback",
        )
        projection_id = stable_id("projection", outbox_id, str(row[2]), row[3])
        payload = {
            "run_id": row[1],
            "projection_id": projection_id,
            "yaml_sha256": sha256(yaml_raw),
            "markdown_sha256": sha256(markdown_raw),
        }
        requested = json.loads(row[6])
        event_id = stable_id("event", projection_id, "written")
        connection.execute("BEGIN IMMEDIATE")
        seq = (
            connection.execute(
                "SELECT receipt_high_water FROM k0b02_source_sequences WHERE run_id=?",
                (row[1],),
            ).fetchone()[0]
            + 1
        )
        connection.execute(
            "UPDATE k0b02_source_sequences SET receipt_high_water=? WHERE run_id=?",
            (seq, row[1]),
        )
        connection.execute(
            "INSERT INTO k0b02_projection_pairs(projection_id,outbox_id,decision_version_id,run_id,source_seq,pair_stem,projection_profile_sha256,yaml_sha256,markdown_sha256,ready,created_at) VALUES(?,?,?,?,?,?,?,?,?,1,?)",
            (
                projection_id,
                outbox_id,
                row[0],
                row[1],
                row[2],
                row[4],
                row[3],
                payload["yaml_sha256"],
                payload["markdown_sha256"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.execute(
            "INSERT INTO events(event_id,run_id,event_type,event_version,initiated_by_invocation_id,artifact_version_id,caused_by_event_id,correlation_id,schema_id,schema_version,schema_sha256,payload_json,payload_sha256,idempotency_key,created_at) VALUES(?,?,?,?,NULL,NULL,?,?,?,?,?,?,?,?,?)",
            (
                event_id,
                row[1],
                "projection.written",
                1,
                requested["event_id"],
                row[1],
                "pipeline-v2.alpha0.event.projection.written.v1",
                "1",
                profile["event_schema_sha256"]["projection.written"],
                json_bytes(payload).decode().strip(),
                sha256(json_bytes(payload)),
                "|".join([row[1], "v1", projection_id]),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        result_id = stable_id("projection-result", projection_id)
        event = {
            "event_id": event_id,
            "event_type": "projection.written",
            "event_version": 1,
            "payload": payload,
        }
        connection.execute(
            "INSERT INTO k0b02_projection_results(result_id,outbox_id,projection_id,result,event_json,receipt_seq,created_at) VALUES(?,?,?,'written',?,?,?)",
            (
                result_id,
                outbox_id,
                projection_id,
                json_bytes(event).decode().strip(),
                seq,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.execute(
            "UPDATE k0b02_projection_outbox SET status='written' WHERE outbox_id=?",
            (outbox_id,),
        )
        connection.execute(
            "UPDATE k0b02_projection_attempts SET status='written' WHERE outbox_id=? AND status='begun'",
            (outbox_id,),
        )
        connection.commit()
        return {
            "result": "written",
            "projection_id": projection_id,
            "yaml_sha256": payload["yaml_sha256"],
            "markdown_sha256": payload["markdown_sha256"],
            "ready": True,
            "receipt_seq": seq,
        }
    except Exception as exc:
        connection.rollback()
        if recordable and row is not None and not terminal_existing:
            projection_id = stable_id("projection", outbox_id, str(row[2]), row[3])
            payload = {
                "run_id": row[1],
                "projection_id": projection_id,
                "failure_code": type(exc).__name__,
                "evidence_ref": "fixture://projection/" + outbox_id,
            }
            event_id = stable_id("event", projection_id, "failed", type(exc).__name__)
            connection.execute("BEGIN IMMEDIATE")
            seq = (
                connection.execute(
                    "SELECT receipt_high_water FROM k0b02_source_sequences WHERE run_id=?",
                    (row[1],),
                ).fetchone()[0]
                + 1
            )
            connection.execute(
                "UPDATE k0b02_source_sequences SET receipt_high_water=? WHERE run_id=?",
                (seq, row[1]),
            )
            connection.execute(
                "INSERT INTO events(event_id,run_id,event_type,event_version,initiated_by_invocation_id,artifact_version_id,caused_by_event_id,correlation_id,schema_id,schema_version,schema_sha256,payload_json,payload_sha256,idempotency_key,created_at) VALUES(?,?,?,?,NULL,NULL,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    row[1],
                    "projection.failed",
                    1,
                    json.loads(row[6])["event_id"],
                    row[1],
                    "pipeline-v2.alpha0.event.projection.failed.v1",
                    "1",
                    profile["event_schema_sha256"]["projection.failed"],
                    json_bytes(payload).decode().strip(),
                    sha256(json_bytes(payload)),
                    "|".join([row[1], "v1", projection_id, type(exc).__name__]),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                "INSERT INTO k0b02_projection_results(result_id,outbox_id,projection_id,result,event_json,receipt_seq,created_at) VALUES(?,?,?,'failed',?,?,?)",
                (
                    stable_id("projection-result", projection_id),
                    outbox_id,
                    projection_id,
                    json_bytes(
                        {
                            "event_id": event_id,
                            "event_type": "projection.failed",
                            "event_version": 1,
                            "payload": payload,
                        }
                    )
                    .decode()
                    .strip(),
                    seq,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                "UPDATE k0b02_projection_outbox SET status='failed' WHERE outbox_id=?",
                (outbox_id,),
            )
            connection.execute(
                "UPDATE k0b02_projection_attempts SET status='failed',evidence_ref=? WHERE outbox_id=? AND status='begun'",
                (payload["evidence_ref"], outbox_id),
            )
            connection.commit()
        raise
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
