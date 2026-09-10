from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import validate_budget_evidence as validator

TOOLCHAIN_ROOT = Path(__file__).resolve().parent
VALIDATOR_PATH = TOOLCHAIN_ROOT / "validate_budget_evidence.py"
FORECAST_PATH = "new pipeline/evidence/k0b-00-updated-forecast-v3.yaml"
FORECAST_SHA256 = "ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a"
RECONCILIATION_PATH = (
    "new pipeline/evidence/k0b-00-forecast-binary-reconciliation-v3.yaml"
)
RECONCILIATION_SHA256 = (
    "d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb"
)


def _source(path: str, digest: str, field_path: str) -> dict[str, str]:
    return {"field_path": field_path, "path": path, "sha256": digest}


def _positive_document() -> dict[str, Any]:
    budget_inputs = {
        "checkpoint_count": {
            "provenance": [
                _source(FORECAST_PATH, FORECAST_SHA256, "forecast.checkpoint_count")
            ],
            "value": 12,
        },
        "max_publication_bytes": {
            "derivation": "bound deterministic derivation across both v3 sources",
            "provenance": [
                _source(
                    FORECAST_PATH,
                    FORECAST_SHA256,
                    "forecast.binary_budget_inputs",
                ),
                _source(
                    RECONCILIATION_PATH,
                    RECONCILIATION_SHA256,
                    "reconciliation.binary_budget_inputs",
                ),
            ],
            "value": 22_020_096,
        },
        "runtime_phase_publications": {
            "provenance": [
                _source(
                    RECONCILIATION_PATH,
                    RECONCILIATION_SHA256,
                    "reconciliation.runtime_phase_publications",
                )
            ],
            "reforecast_sensitive": True,
            "value": 34,
        },
    }
    return {
        "budget_inputs": budget_inputs,
        "calculation_input_sha256": validator.canonical_input_sha256(budget_inputs),
        "calculations": {
            "assumed_mean_object_bytes": 4096,
            "forecast_worst_by_count_bytes": 13_926_400,
            "nominal_expected_bytes": 11_141_120,
            "size_stressed_bytes": 16_711_680,
        },
        "claims": {"f15_size_stress": False, "phase_completion": False},
        "governance": {
            "final_implementation_disposition_gate_inventory": [
                "G-K0B01-HUMAN-SIGNOFF",
                "G-K0B01-TOOLCHAIN",
                "G-K0B01-IMPLEMENTATION-LEDGER",
                "G-K0B01-STATE-RENDERER",
                "G-K0B01-IMPLEMENTATION-DISPOSITION",
            ],
            "state_renderer_independent_authority_required": True,
        },
    }


def _errors(document: dict[str, Any]) -> list[str]:
    errors, _digest = validator.validate_document(document)
    return errors


def test_positive_evidence_and_cli(tmp_path: Path) -> None:
    document = _positive_document()
    assert _errors(document) == []
    evidence_path = tmp_path / "future-budget-evidence.json"
    evidence_path.write_text(
        json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--evidence", str(evidence_path)],
        check=False,
        capture_output=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["result"] == "pass"


def test_missing_exact_provenance_is_rejected() -> None:
    document = _positive_document()
    document["budget_inputs"]["checkpoint_count"]["provenance"] = []
    document["calculation_input_sha256"] = validator.canonical_input_sha256(
        document["budget_inputs"]
    )
    assert "budget_inputs:checkpoint_count:provenance_required" in _errors(document)


def test_changed_budget_input_makes_calculation_stale() -> None:
    document = _positive_document()
    document["budget_inputs"]["checkpoint_count"]["value"] = 13
    assert "calculation_input_sha256:stale" in _errors(document)


def test_f15_and_phase_claims_require_authoritative_count() -> None:
    document = _positive_document()
    document["claims"] = {"f15_size_stress": True, "phase_completion": True}
    errors = _errors(document)
    assert "f15:authoritative_worst_case_object_count_required" in errors


def test_runtime_publication_count_is_reforecast_sensitive() -> None:
    document = _positive_document()
    document["budget_inputs"]["runtime_phase_publications"]["reforecast_sensitive"] = (
        False
    )
    document["calculation_input_sha256"] = validator.canonical_input_sha256(
        document["budget_inputs"]
    )
    expected = "budget_inputs:runtime_phase_publications:reforecast_sensitive"
    assert expected in _errors(document)


@pytest.mark.parametrize("field", validator.REQUIRED_CALCULATION_FIELDS)
def test_all_four_size_fields_are_required(field: str) -> None:
    document = _positive_document()
    del document["calculations"][field]
    expected = f"calculations:{field}:nonnegative_integer_required"
    assert expected in _errors(document)


def test_state_renderer_independence_and_five_gate_inventory() -> None:
    document = copy.deepcopy(_positive_document())
    document["governance"]["state_renderer_independent_authority_required"] = False
    document["governance"]["final_implementation_disposition_gate_inventory"] = []
    errors = _errors(document)
    assert "governance:state_renderer_independence" in errors
    assert "governance:five_gate_inventory" in errors
