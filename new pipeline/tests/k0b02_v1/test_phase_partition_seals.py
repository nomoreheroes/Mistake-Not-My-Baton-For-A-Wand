from __future__ import annotations

import sqlite3

import pytest

from fixture_support import ContractError, published, record, runtime_values
from k0b02_v1.phase import (
    bind,
    record_f15_trigger,
    record_publication,
    reject_model_call,
    seal,
)


def _phase_fixture(case_id: str):
    bundle, request, publication = published(case_id)
    bind(bundle["database"], "1" * 64)
    return bundle, request, publication


def _phases():
    return runtime_values()["phases"]


def _triggers():
    return runtime_values()["triggers"]


def _seal_data(request, publication, phase_id, *, predecessor=None, authorities=None):
    return {
        "seal_id": "seal-" + phase_id,
        "phase_id": phase_id,
        "partition_digest": "1" * 64,
        "predecessor_seal_id": predecessor,
        "terminal_checkpoint_publication_id": request["publication_id"],
        "terminal_checkpoint_sha256": publication["snapshot_sha256"],
        "ready_pair_set_sha256": request["ready_pair_set_sha256"],
        "outbox_high_water": 1,
        "cumulative_full_bytes": publication["snapshot_bytes"],
        "publication_count": 1,
        "authorities": [] if authorities is None else authorities,
        "all_admitted_members_terminal": True,
        "no_unresolved_begun_effects": True,
        "result": "sealed",
    }


def _seal_first(bundle, request, publication):
    phases = _phases()
    record_publication(bundle["database"], phases[0], publication["snapshot_bytes"])
    return seal(bundle["database"], _seal_data(request, publication, phases[0]))


def test_successor_before_seal_rejected() -> None:
    bundle, request, publication = _phase_fixture("phase_before_seal")
    with pytest.raises(ContractError, match="predecessor_seal"):
        record_publication(
            bundle["database"], _phases()[1], publication["snapshot_bytes"]
        )
    record("phase_before_seal")


def test_successor_after_seal_admitted() -> None:
    bundle, request, publication = _phase_fixture("phase_after_seal")
    first = _seal_first(bundle, request, publication)
    second = record_publication(
        bundle["database"], _phases()[1], publication["snapshot_bytes"]
    )
    assert first["result"] == "sealed" and second["publication_count"] == 1
    record("phase_after_seal")


def test_seal_cannot_reopen_or_reorder() -> None:
    bundle, request, publication = _phase_fixture("phase_reopen_or_reorder")
    _seal_first(bundle, request, publication)
    with pytest.raises((sqlite3.IntegrityError, ContractError)):
        seal(bundle["database"], _seal_data(request, publication, _phases()[0]))
    with pytest.raises(ContractError, match="trigger_order"):
        record_f15_trigger(bundle["database"], _triggers()[1])
    record("phase_reopen_or_reorder")


def test_unknown_partition_rejected() -> None:
    bundle, request, publication = _phase_fixture("phase_unknown_partition")
    record_publication(bundle["database"], _phases()[0], publication["snapshot_bytes"])
    data = _seal_data(request, publication, _phases()[0])
    data["partition_digest"] = "9" * 64
    with pytest.raises(ContractError, match="seal:partition"):
        seal(bundle["database"], data)
    record("phase_unknown_partition")


def test_exact_four_synthetic_F15_triggers_and_fifth_rejected() -> None:
    bundle, request, publication = _phase_fixture("F15_fifth_trigger")
    _seal_first(bundle, request, publication)
    record_publication(bundle["database"], _phases()[1], publication["snapshot_bytes"])
    for trigger in _triggers():
        result = record_f15_trigger(bundle["database"], trigger)
        assert result["model_calls"] == 0
    with pytest.raises(ContractError, match="trigger_limit"):
        record_f15_trigger(bundle["database"], _triggers()[-1])
    record("F15_fifth_trigger", trigger_count=4, actual_model_calls=0)


def test_F15_counter_is_explicitly_non_model_simulation() -> None:
    bundle, request, publication = _phase_fixture("F15_non_model_simulation")
    _seal_first(bundle, request, publication)
    connection = sqlite3.connect(bundle["database"])
    row = connection.execute(
        "SELECT model_calls,boundary_trigger_count FROM k0b02_phase_counters WHERE phase_id=?",
        (_phases()[1],),
    ).fetchone()
    connection.close()
    assert row == (0, 0)
    record(
        "F15_non_model_simulation",
        synthetic=True,
        actual_provider_calls=0,
        actual_model_calls=0,
    )


def test_post_F15_call_rejected_after_terminal_seal() -> None:
    bundle, request, publication = _phase_fixture("post_F15_call_rejection")
    _seal_first(bundle, request, publication)
    record_publication(bundle["database"], _phases()[1], publication["snapshot_bytes"])
    for trigger in _triggers():
        record_f15_trigger(bundle["database"], trigger)
    data = _seal_data(
        request,
        publication,
        _phases()[1],
        predecessor="seal-" + _phases()[0],
        authorities=_triggers(),
    )
    assert seal(bundle["database"], data)["result"] == "sealed"
    with pytest.raises(ContractError, match="post_F15_model_call"):
        reject_model_call(bundle["database"])
    record("post_F15_call_rejection", actual_model_calls=0)
