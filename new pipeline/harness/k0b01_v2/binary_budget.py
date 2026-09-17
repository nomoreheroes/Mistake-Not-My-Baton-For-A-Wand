from __future__ import annotations

from typing import Any, Sequence

from .canonical import require


def integer(value: Any, name: str) -> int:
    require(type(value) is int and value >= 0, "budget:integer:" + name)
    return value


def ceiling(value: int, divisor: int) -> int:
    integer(value, "ceiling_value")
    require(type(divisor) is int and divisor > 0, "budget:divisor")
    return (value + divisor - 1) // divisor


def quantities(inputs: dict[str, Any]) -> dict[str, int]:
    nominal = integer(inputs["nominal_object_count"], "nominal_object_count")
    worst = integer(inputs["worst_case_object_count"], "worst_case_object_count")
    mean = integer(inputs["assumed_mean_object_bytes"], "assumed_mean_object_bytes")
    hard = integer(inputs["hard_per_object_bytes"], "hard_per_object_bytes")
    require(0 < nominal <= worst and 0 < mean <= hard, "binary:assumptions")
    return {
        "assumed_mean_object_bytes": mean,
        "nominal_expected_bytes": nominal * mean,
        "forecast_worst_by_count_bytes": worst * mean,
        "size_stressed_bytes": worst * hard,
    }


def validate_definition(definition: dict[str, Any]) -> dict[str, Any]:
    common = {
        "applicable",
        "producer",
        "contract_proof",
        "payload_classes",
        "media_types",
        "credit",
        "forecast_provenance",
    }
    applicable = definition.get("applicable")
    require(type(applicable) is bool, "binary:applicability")
    expected = common | (
        {
            "nominal_object_count",
            "worst_case_object_count",
            "assumed_mean_object_bytes",
            "hard_per_object_bytes",
            "maximum_aggregate_new_bytes",
            "runtime_aggregate_limit_bytes",
            "checkpoint_publications",
            "planning_pack_factor",
        }
        if applicable
        else {
            "nominal_object_count",
            "worst_case_object_count",
            "nominal_new_bytes",
            "worst_new_bytes",
        }
    )
    require(set(definition) == expected, "binary:fields")
    require(
        isinstance(definition["producer"], str) and definition["producer"],
        "binary:producer",
    )
    require(
        isinstance(definition["credit"], dict)
        and definition["credit"]
        and all(type(v) is int and v == 0 for v in definition["credit"].values()),
        "binary:credit",
    )
    proof = definition["contract_proof"]
    require(
        isinstance(proof, dict)
        and set(proof)
        == {
            "contract_ref",
            "binary_persistence",
            "uses_only_version_refs",
            "payload_budgeted_by_producer",
        },
        "binary:proof_fields",
    )
    require(
        isinstance(proof["contract_ref"], str) and proof["contract_ref"],
        "binary:proof_ref",
    )
    require(
        all(
            type(proof[k]) is bool
            for k in (
                "binary_persistence",
                "uses_only_version_refs",
                "payload_budgeted_by_producer",
            )
        ),
        "binary:proof_types",
    )
    provenance = definition["forecast_provenance"]
    require(isinstance(provenance, list) and bool(provenance), "binary:provenance")
    for source in provenance:
        require(
            set(source) == {"path", "sha256", "field_paths"}
            and isinstance(source["field_paths"], list)
            and source["field_paths"]
            and all(isinstance(p, str) and p for p in source["field_paths"]),
            "binary:provenance_fields",
        )
    if not applicable:
        require(
            proof["binary_persistence"] is False
            and proof["uses_only_version_refs"] is True
            and proof["payload_budgeted_by_producer"] is True,
            "binary:false_NA",
        )
        require(
            definition["payload_classes"] == [] and definition["media_types"] == [],
            "binary:NA_payload",
        )
        require(
            all(
                type(definition[k]) is int and definition[k] == 0
                for k in (
                    "nominal_object_count",
                    "worst_case_object_count",
                    "nominal_new_bytes",
                    "worst_new_bytes",
                )
            ),
            "binary:NA_count",
        )
        return {
            "applicable": False,
            "nominal_expected_bytes": 0,
            "forecast_worst_by_count_bytes": 0,
            "size_stressed_bytes": 0,
            "proof": proof,
        }
    require(
        proof["binary_persistence"] is True
        and proof["uses_only_version_refs"] is False,
        "binary:applicable_proof",
    )
    require(
        isinstance(definition["payload_classes"], list)
        and definition["payload_classes"]
        and isinstance(definition["media_types"], list)
        and definition["media_types"]
        and all(
            isinstance(v, str) and v
            for v in definition["payload_classes"] + definition["media_types"]
        ),
        "binary:payload_classes",
    )
    values = quantities(definition)
    maximum = integer(
        definition["maximum_aggregate_new_bytes"], "maximum_aggregate_new_bytes"
    )
    runtime = integer(
        definition["runtime_aggregate_limit_bytes"], "runtime_aggregate_limit_bytes"
    )
    require(
        values["size_stressed_bytes"] <= maximum
        and values["size_stressed_bytes"] <= runtime,
        "binary:size_stress_aggregate",
    )
    integer(definition["checkpoint_publications"], "checkpoint_publications")
    require(
        type(definition["planning_pack_factor"]) is int
        and definition["planning_pack_factor"] == 1,
        "binary:factor",
    )
    return {
        "applicable": True,
        **values,
        "maximum_aggregate_new_bytes": maximum,
        "runtime_aggregate_limit_bytes": runtime,
    }


def validate_actual(
    objects: Sequence[bytes], definition: dict[str, Any]
) -> dict[str, int]:
    require(isinstance(objects, (list, tuple)), "binary:actual_objects")
    total = 0
    for item in objects:
        require(type(item) is bytes, "binary:actual_type")
        require(
            len(item)
            <= integer(definition["hard_per_object_bytes"], "hard_per_object_bytes"),
            "binary:actual_per_object",
        )
        total += len(item)
    require(
        total
        <= integer(
            definition["runtime_aggregate_limit_bytes"], "runtime_aggregate_limit_bytes"
        ),
        "binary:actual_aggregate",
    )
    require(
        len(objects)
        <= integer(definition["worst_case_object_count"], "worst_case_object_count"),
        "binary:actual_count",
    )
    return {"actual_object_count": len(objects), "actual_aggregate_bytes": total}


def stress_checkpoint(
    inputs: dict[str, Any], thresholds: dict[str, Any]
) -> dict[str, Any]:
    values = quantities(inputs)
    nonbinary = integer(inputs["non_binary_worst_bytes"], "non_binary_worst_bytes")
    publications = integer(inputs["publications"], "publications")
    require(
        type(inputs["planning_pack_factor"]) is int
        and inputs["planning_pack_factor"] == 1,
        "budget:factor",
    )
    require(type(inputs["credit"]) is int and inputs["credit"] == 0, "budget:credit")
    unrounded = nonbinary + values["size_stressed_bytes"]
    rounded = ceiling(unrounded, 1048576) * 1048576
    pack = rounded * publications
    checkpoint_hard = integer(
        thresholds["checkpoint_hard_bytes"], "checkpoint_hard_bytes"
    )
    phase_hard = integer(thresholds["phase_pack_hard_bytes"], "phase_pack_hard_bytes")
    warning = integer(thresholds["warning_bytes"], "warning_bytes")
    return {
        **values,
        "unrounded_size_stressed_checkpoint_bytes": unrounded,
        "rounded_size_stressed_checkpoint_bytes": rounded,
        "size_stressed_phase_pack_bytes": pack,
        "phase_margin_bytes": phase_hard - pack,
        "checkpoint_result": "below_hard"
        if rounded < checkpoint_hard
        else "above_hard",
        "phase_result": "above_hard"
        if pack >= phase_hard
        else "above_warning"
        if pack >= warning
        else "below_warning",
        "publications": publications,
        "credit": 0,
    }
