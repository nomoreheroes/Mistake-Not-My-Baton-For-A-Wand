from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import json_bytes, require, sha256
from .store import K0b02Store


PHASES = ("K0b-runtime-operational", "K0b-F15-exact-measurement")
TRIGGERS = (
    "k0b.f15.boundary.entry_gate",
    "k0b.f15.boundary.program_owner_wait_or_exit",
    "k0b.f15.boundary.exit_gate",
    "k0b.f15.boundary.top_level_run_end",
)


def bind(database: Path, partition_digest: str) -> None:
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index, phase in enumerate(PHASES):
            connection.execute(
                "INSERT OR IGNORE INTO k0b02_phase_bindings(phase_id,partition_digest,phase_order,predecessor_phase_id,runtime_enabled) VALUES(?,?,?,?,0)",
                (
                    phase,
                    partition_digest,
                    index + 1,
                    PHASES[index - 1] if index else None,
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO k0b02_phase_counters(phase_id,cumulative_full_snapshot_bytes,publication_count,batch_publications,model_calls,boundary_trigger_count) VALUES(?,0,0,0,0,0)",
                (phase,),
            )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_publication(
    database: Path,
    phase_id: str,
    snapshot_bytes: int,
    checkpoint_hard: int = 104857600,
    phase_warning: int = 536870912,
    phase_hard: int = 1073741824,
) -> dict[str, Any]:
    require(
        phase_id in PHASES and 0 < snapshot_bytes < checkpoint_hard,
        "phase:checkpoint_hard",
    )
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        require(
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_phase_seals WHERE phase_id=?", (phase_id,)
            ).fetchone()[0]
            == 0,
            "phase:sealed",
        )
        if phase_id == PHASES[1]:
            require(
                connection.execute(
                    "SELECT COUNT(*) FROM k0b02_phase_seals WHERE phase_id=?",
                    (PHASES[0],),
                ).fetchone()[0]
                == 1,
                "phase:predecessor_seal",
            )
        row = connection.execute(
            "SELECT cumulative_full_snapshot_bytes,publication_count,batch_publications FROM k0b02_phase_counters WHERE phase_id=?",
            (phase_id,),
        ).fetchone()
        require(row is not None and row[2] < 12, "phase:batch_cap")
        cumulative, count = row[0] + snapshot_bytes, row[1] + 1
        require(cumulative < phase_hard, "phase:pack_hard")
        connection.execute(
            "UPDATE k0b02_phase_counters SET cumulative_full_snapshot_bytes=?,publication_count=?,batch_publications=? WHERE phase_id=?",
            (cumulative, count, row[2] + 1, phase_id),
        )
        connection.commit()
        return {
            "result": "above_warning"
            if cumulative >= phase_warning
            else "below_warning",
            "cumulative_full_snapshot_bytes": cumulative,
            "publication_count": count,
            "credit": 0,
        }
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_f15_trigger(database: Path, trigger_id: str) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        require(
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_phase_seals WHERE phase_id=?", (PHASES[0],)
            ).fetchone()[0]
            == 1,
            "phase:predecessor_seal",
        )
        require(
            connection.execute(
                "SELECT COUNT(*) FROM k0b02_phase_seals WHERE phase_id=?", (PHASES[1],)
            ).fetchone()[0]
            == 0,
            "phase:F15_sealed",
        )
        count, calls = connection.execute(
            "SELECT boundary_trigger_count,model_calls FROM k0b02_phase_counters WHERE phase_id=?",
            (PHASES[1],),
        ).fetchone()
        require(calls == 0 and count < len(TRIGGERS), "phase:F15_trigger_limit")
        require(trigger_id == TRIGGERS[count], "phase:F15_trigger_order")
        connection.execute(
            "UPDATE k0b02_phase_counters SET boundary_trigger_count=? WHERE phase_id=?",
            (count + 1, PHASES[1]),
        )
        connection.commit()
        return {
            "result": "synthetic_trigger_recorded",
            "boundary_trigger_count": count + 1,
            "model_calls": 0,
        }
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def reject_model_call(database: Path) -> None:
    connection = K0b02Store.connect(database)
    try:
        sealed = connection.execute(
            "SELECT COUNT(*) FROM k0b02_phase_seals WHERE phase_id=?", (PHASES[1],)
        ).fetchone()[0]
        require(
            False,
            "phase:post_F15_model_call" if sealed else "phase:runtime_not_authorized",
        )
    finally:
        connection.close()


def seal(
    database: Path, data: dict[str, Any], observer: Callable[[str], None] | None = None
) -> dict[str, Any]:
    require(data["phase_id"] in PHASES and data["result"] == "sealed", "seal:identity")
    require(
        data["all_admitted_members_terminal"] is True
        and data["no_unresolved_begun_effects"] is True,
        "seal:terminal",
    )
    connection = K0b02Store.connect(database)
    try:
        unresolved = connection.execute(
            "SELECT COUNT(*) FROM k0b02_publication_intents WHERE status='begun'"
        ).fetchone()[0]
        require(unresolved == 0, "seal:begun_effect")
        binding = connection.execute(
            "SELECT partition_digest FROM k0b02_phase_bindings WHERE phase_id=?",
            (data["phase_id"],),
        ).fetchone()
        counters = connection.execute(
            "SELECT cumulative_full_snapshot_bytes,publication_count,boundary_trigger_count,model_calls FROM k0b02_phase_counters WHERE phase_id=?",
            (data["phase_id"],),
        ).fetchone()
        require(
            binding is not None and binding[0] == data["partition_digest"],
            "seal:partition",
        )
        require(
            counters is not None
            and counters[0] == data["cumulative_full_bytes"]
            and counters[1] == data["publication_count"]
            and counters[3] == 0,
            "seal:counters",
        )
        publication = connection.execute(
            "SELECT snapshot_sha256 FROM k0b02_publication_results WHERE publication_id=?",
            (data["terminal_checkpoint_publication_id"],),
        ).fetchone()
        require(
            publication is not None
            and publication[0] == data["terminal_checkpoint_sha256"],
            "seal:terminal_checkpoint",
        )
        if data["phase_id"] == PHASES[1]:
            predecessor = connection.execute(
                "SELECT seal_id FROM k0b02_phase_seals WHERE phase_id=?", (PHASES[0],)
            ).fetchone()
            require(
                predecessor is not None
                and data["predecessor_seal_id"] == predecessor[0],
                "seal:predecessor",
            )
            require(data["authorities"] == list(TRIGGERS), "seal:four_triggers")
            require(counters[2] == 4, "seal:trigger_count")
        if observer:
            observer("terminal_checkpoint_before_seal")
        connection.execute(
            "INSERT INTO k0b02_phase_seals(seal_id,phase_id,partition_digest,predecessor_seal_id,terminal_checkpoint_publication_id,terminal_checkpoint_sha256,ready_pair_set_sha256,outbox_high_water,cumulative_full_bytes,publication_count,authorities_json,all_admitted_members_terminal,no_unresolved_begun_effects,result,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,1,1,'sealed',?)",
            (
                data["seal_id"],
                data["phase_id"],
                data["partition_digest"],
                data["predecessor_seal_id"],
                data["terminal_checkpoint_publication_id"],
                data["terminal_checkpoint_sha256"],
                data["ready_pair_set_sha256"],
                data["outbox_high_water"],
                data["cumulative_full_bytes"],
                data["publication_count"],
                json_bytes(data["authorities"]).decode().strip(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        if observer:
            observer("seal_committed_before_successor_admission")
        return {"result": "sealed", "seal_sha256": sha256(json_bytes(data))}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
