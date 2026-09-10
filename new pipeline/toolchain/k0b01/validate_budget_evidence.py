from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SUCCESS = 0
INVALID_INPUT = 2
BUDGET_EVIDENCE_INVALID = 5

BOUND_SOURCES = {
    "new pipeline/evidence/k0b-00-forecast-binary-reconciliation-v3.yaml": (
        "d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb"
    ),
    "new pipeline/evidence/k0b-00-updated-forecast-v3.yaml": (
        "ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a"
    ),
}
EXPECTED_INPUT_VALUES = {
    "checkpoint_count": 12,
    "max_publication_bytes": 22_020_096,
    "runtime_phase_publications": 34,
}
REQUIRED_CALCULATION_FIELDS = (
    "assumed_mean_object_bytes",
    "forecast_worst_by_count_bytes",
    "nominal_expected_bytes",
    "size_stressed_bytes",
)
REQUIRED_GATE_INVENTORY = (
    "G-K0B01-HUMAN-SIGNOFF",
    "G-K0B01-TOOLCHAIN",
    "G-K0B01-IMPLEMENTATION-LEDGER",
    "G-K0B01-STATE-RENDERER",
    "G-K0B01-IMPLEMENTATION-DISPOSITION",
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def canonical_input_sha256(budget_inputs: Any) -> str:
    payload = json.dumps(
        budget_inputs,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        return yaml.load(text)


def _valid_authority(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    path = value.get("path")
    digest = value.get("sha256")
    field_path = value.get("field_path")
    return (
        isinstance(path, str)
        and bool(path)
        and isinstance(digest, str)
        and SHA256_PATTERN.fullmatch(digest) is not None
        and isinstance(field_path, str)
        and bool(field_path)
    )


def _check_bound_provenance(
    errors: list[str],
    name: str,
    value: Any,
    *,
    require_both_sources: bool = False,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"budget_inputs:{name}:object_required")
        return
    if value.get("value") != EXPECTED_INPUT_VALUES[name]:
        errors.append(f"budget_inputs:{name}:value")
    provenance = value.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        errors.append(f"budget_inputs:{name}:provenance_required")
        return
    observed_sources: set[str] = set()
    for item in provenance:
        if not _valid_authority(item):
            errors.append(f"budget_inputs:{name}:provenance_shape")
            continue
        source_path = item["path"]
        if BOUND_SOURCES.get(source_path) != item["sha256"]:
            errors.append(f"budget_inputs:{name}:provenance_binding")
            continue
        observed_sources.add(source_path)
    if require_both_sources and observed_sources != set(BOUND_SOURCES):
        errors.append(f"budget_inputs:{name}:both_v3_sources_required")


def validate_document(document: Any) -> tuple[list[str], str | None]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["document:object_required"], None

    budget_inputs = document.get("budget_inputs")
    if not isinstance(budget_inputs, dict):
        return ["budget_inputs:object_required"], None

    _check_bound_provenance(
        errors,
        "max_publication_bytes",
        budget_inputs.get("max_publication_bytes"),
        require_both_sources=True,
    )
    _check_bound_provenance(
        errors,
        "checkpoint_count",
        budget_inputs.get("checkpoint_count"),
    )
    _check_bound_provenance(
        errors,
        "runtime_phase_publications",
        budget_inputs.get("runtime_phase_publications"),
    )

    max_publication = budget_inputs.get("max_publication_bytes")
    if (
        not isinstance(max_publication, dict)
        or not isinstance(max_publication.get("derivation"), str)
        or not max_publication.get("derivation")
    ):
        errors.append("budget_inputs:max_publication_bytes:derivation_required")

    runtime_publications = budget_inputs.get("runtime_phase_publications")
    if not isinstance(runtime_publications, dict) or (
        runtime_publications.get("reforecast_sensitive") is not True
    ):
        errors.append("budget_inputs:runtime_phase_publications:reforecast_sensitive")

    input_digest = canonical_input_sha256(budget_inputs)
    if document.get("calculation_input_sha256") != input_digest:
        errors.append("calculation_input_sha256:stale")

    calculations = document.get("calculations")
    if not isinstance(calculations, dict):
        errors.append("calculations:object_required")
    else:
        for field in REQUIRED_CALCULATION_FIELDS:
            value = calculations.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"calculations:{field}:nonnegative_integer_required")
        assumed_mean = calculations.get("assumed_mean_object_bytes")
        if isinstance(assumed_mean, int) and not isinstance(assumed_mean, bool):
            if assumed_mean <= 0:
                errors.append(
                    "calculations:assumed_mean_object_bytes:positive_required"
                )

    claims = document.get("claims")
    if not isinstance(claims, dict):
        errors.append("claims:object_required")
        claims = {}
    f15_claimed = claims.get("f15_size_stress") is True
    phase_claimed = claims.get("phase_completion") is True
    if f15_claimed or phase_claimed:
        f15 = document.get("f15")
        if not isinstance(f15, dict):
            errors.append("f15:authoritative_worst_case_object_count_required")
        else:
            count = f15.get("worst_case_object_count")
            if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                errors.append("f15:authoritative_worst_case_object_count_required")
            if not _valid_authority(f15.get("authority")):
                errors.append("f15:authority_required")

    governance = document.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance:object_required")
    else:
        if governance.get("state_renderer_independent_authority_required") is not True:
            errors.append("governance:state_renderer_independence")
        gate_inventory = governance.get(
            "final_implementation_disposition_gate_inventory"
        )
        if gate_inventory != list(REQUIRED_GATE_INVENTORY):
            errors.append("governance:five_gate_inventory")

    return sorted(set(errors)), input_digest


def _emit(value: dict[str, Any]) -> None:
    output = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    sys.stdout.write(output + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    arguments = parser.parse_args(argv)
    if not arguments.evidence.is_file():
        _emit({"exit_code": INVALID_INPUT, "result": "invalid_input"})
        return INVALID_INPUT
    try:
        document = _load_document(arguments.evidence)
    except (OSError, UnicodeError, ValueError):
        _emit(
            {
                "errors": ["document:parse_error"],
                "exit_code": BUDGET_EVIDENCE_INVALID,
                "result": "budget_evidence_invalid",
            }
        )
        return BUDGET_EVIDENCE_INVALID
    errors, input_digest = validate_document(document)
    if errors:
        _emit(
            {
                "errors": errors,
                "exit_code": BUDGET_EVIDENCE_INVALID,
                "result": "budget_evidence_invalid",
            }
        )
        return BUDGET_EVIDENCE_INVALID
    _emit(
        {
            "calculation_input_sha256": input_digest,
            "exit_code": SUCCESS,
            "result": "pass",
        }
    )
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
