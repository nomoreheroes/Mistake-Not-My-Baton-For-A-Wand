from __future__ import annotations

import pytest

from fixture_support import ContractError, context, database_for, fixture, record
from k0b02_v1.binary_budget import stress_checkpoint
from k0b02_v1.phase import PHASES, bind, record_publication


def _bound(case_id: str):
    root, database, store = database_for(case_id)
    bind(database, "1" * 64)
    return database


def test_checkpoint_hard_limit_is_strict() -> None:
    database = _bound("checkpoint_hard_limit")
    with pytest.raises(ContractError, match="checkpoint_hard"):
        record_publication(database, PHASES[0], 104857600)
    record("checkpoint_hard_limit")


def test_phase_pack_hard_limit_uses_cumulative_full_bytes() -> None:
    database = _bound("phase_pack_hard_limit")
    record_publication(
        database, PHASES[0], 90, checkpoint_hard=1000, phase_warning=80, phase_hard=100
    )
    with pytest.raises(ContractError, match="phase:pack_hard"):
        record_publication(
            database,
            PHASES[0],
            10,
            checkpoint_hard=1000,
            phase_warning=80,
            phase_hard=100,
        )
    record("phase_pack_hard_limit", credit=0)


def test_publication_batch_cap_is_twelve() -> None:
    database = _bound("publication_batch_cap")
    for _ in range(12):
        record_publication(database, PHASES[0], 1)
    with pytest.raises(ContractError, match="batch_cap"):
        record_publication(database, PHASES[0], 1)
    record("publication_batch_cap", admitted=12)


def test_warning_reforecast_and_exact_stress_vector() -> None:
    ctx = context()
    policy = ctx.json(
        "new pipeline/registry/resource-budget-policy/k0b02-policy-v3.json"
    )
    inputs = ctx.json(
        "new pipeline/registry/resource-budget-policy/k0b01-reference-inputs-v2.json"
    )
    result = stress_checkpoint(inputs["current_stress_inputs"], policy["thresholds"])
    expected = fixture("budget-boundary-vectors-v1.json")
    assert (
        result["rounded_size_stressed_checkpoint_bytes"]
        == expected["checkpoint_size_stress_bytes"]
    )
    assert (
        result["size_stressed_phase_pack_bytes"]
        == expected["phase_pack_size_stress_bytes"]
    )
    assert result["phase_result"] == "above_warning" and result["credit"] == 0
    record("warning_reforecast", phase_margin_bytes=result["phase_margin_bytes"])
