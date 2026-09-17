"""Test-only arithmetic oracle. No production import, builder, or truth table."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any


def up(value: int, divisor: int) -> int:
    if type(value) is not int or type(divisor) is not int or value < 0 or divisor < 1:
        raise ValueError("oracle integer")
    quotient, remainder = divmod(value, divisor)
    return quotient + bool(remainder)


def binary(definition: dict[str, Any]) -> dict[str, Any]:
    if definition["applicable"] is False:
        return {
            "applicable": False,
            "nominal_expected_bytes": 0,
            "forecast_worst_by_count_bytes": 0,
            "size_stressed_bytes": 0,
            "proof": definition["contract_proof"],
        }
    return {
        "applicable": True,
        "assumed_mean_object_bytes": definition["assumed_mean_object_bytes"],
        "nominal_expected_bytes": definition["nominal_object_count"]
        * definition["assumed_mean_object_bytes"],
        "forecast_worst_by_count_bytes": definition["worst_case_object_count"]
        * definition["assumed_mean_object_bytes"],
        "size_stressed_bytes": definition["worst_case_object_count"]
        * definition["hard_per_object_bytes"],
        "maximum_aggregate_new_bytes": definition["maximum_aggregate_new_bytes"],
        "runtime_aggregate_limit_bytes": definition["runtime_aggregate_limit_bytes"],
    }


def packages(case: dict[str, Any]) -> dict[str, Any]:
    calls = {
        "nominal": 0,
        "worst_case": 0,
        "checkpointed_nominal": 0,
        "checkpointed_worst_case": 0,
    }
    attention = {
        metric + "_" + mode: 0
        for metric in ("sessions", "blocking_decisions", "active_minutes")
        for mode in ("nominal", "worst_case")
    }
    for package in case["packages"]:
        for mode, source_mode in (("nominal", "nominal"), ("worst_case", "worst")):
            count = sum(
                node[source_mode + "_instances"]
                * node[source_mode + "_calls_per_instance"]
                * node[source_mode + "_attempts"]
                for node in package["nodes"]
            )
            dialogue = package["dialogue"]
            if dialogue["applicable"]:
                count += math.prod(
                    dialogue[key]
                    for key in (
                        "topics",
                        "sessions",
                        "rounds_per_topic",
                        "role_instances",
                    )
                )
            calls[mode] += count
            if any(
                node["call_class"] != "plan_author_review_allocation"
                for node in package["nodes"]
            ):
                calls["checkpointed_" + mode] += count
        for metric in ("sessions", "blocking_decisions", "active_minutes"):
            for mode in ("nominal", "worst_case"):
                attention[metric + "_" + mode] += package["human_attention"][metric][
                    mode
                ]
    return {
        "invocations": calls,
        "human_attention": attention,
        "human_profile": case["human_envelope_profile"],
    }


def checkpoint(case: dict[str, Any]) -> dict[str, int]:
    size = up(sum(case["components_bytes"].values()), 2**20) * 2**20
    available = case["publisher_available"]
    window = (
        max(
            up(case["window"]["total_points"], 10),
            up(case["window"]["publisher_minutes"], 5),
            up(case["window"]["new_db_bytes"], 2**25),
        )
        if available
        else 0
    )
    publications = window + sum(case["triggers"].values()) if available else 0
    return {
        "checkpoint_bytes": size,
        "publications": publications,
        "phase_pack_bytes": size * publications,
        "window_publications": window,
        "batches": up(publications, 12),
    }


def reference(case: dict[str, Any]) -> dict[str, Any]:
    if case["kind"] == "packages":
        return packages(case)
    if case["kind"] == "checkpoint":
        return checkpoint(case)
    if case["kind"] == "binary":
        return binary(case["definition"])
    raise ValueError("oracle kind")


def stress(inputs: dict[str, Any]) -> dict[str, Any]:
    stressed = inputs["worst_case_object_count"] * inputs["hard_per_object_bytes"]
    raw = inputs["non_binary_worst_bytes"] + stressed
    rounded = up(raw, 2**20) * 2**20
    pack = rounded * inputs["publications"]
    return {
        "assumed_mean_object_bytes": inputs["assumed_mean_object_bytes"],
        "nominal_expected_bytes": inputs["nominal_object_count"]
        * inputs["assumed_mean_object_bytes"],
        "forecast_worst_by_count_bytes": inputs["worst_case_object_count"]
        * inputs["assumed_mean_object_bytes"],
        "size_stressed_bytes": stressed,
        "unrounded_size_stressed_checkpoint_bytes": raw,
        "rounded_size_stressed_checkpoint_bytes": rounded,
        "size_stressed_phase_pack_bytes": pack,
        "phase_margin_bytes": 2**30 - pack,
        "checkpoint_result": "below_hard" if rounded < 100 * 2**20 else "above_hard",
        "phase_result": "above_hard"
        if pack >= 2**30
        else "above_warning"
        if pack >= 2**29
        else "below_warning",
        "publications": inputs["publications"],
        "credit": 0,
    }


def typed_digest(connection: Any, table_names: list[str]) -> str:
    """Independent small-fixture implementation; production must stream."""
    hasher = hashlib.sha256(b"pipeline-v2.sqlite-content-digest-v1\x00")

    def length(value: bytes) -> bytes:
        return struct.pack(">Q", len(value)) + value

    def cell(kind: str, value: Any) -> bytes:
        if kind == "null":
            tag, raw = b"N", b""
        elif kind == "integer":
            tag, raw = b"i", struct.pack(">q", value)
        elif kind == "real":
            if math.isnan(value):
                raise ValueError("NaN")
            tag, raw = b"r", struct.pack(">d", value)
        elif kind == "text":
            value.decode("utf-8", "strict")
            tag, raw = b"t", value
        elif kind == "blob":
            tag, raw = b"b", value
        else:
            raise ValueError(kind)
        return tag + length(raw)

    for table in sorted(table_names, key=lambda name: name.encode("utf-8")):
        quoted = '"' + table.replace('"', '""') + '"'
        columns = list(connection.execute("PRAGMA table_info(" + quoted + ")"))
        pk_positions = [
            columns.index(row)
            for row in sorted(
                (row for row in columns if row[5]), key=lambda row: row[5]
            )
        ]
        if not pk_positions:
            raise ValueError("missing PK")
        hasher.update(length(table.encode("utf-8")))
        for column in columns:
            hasher.update(length(column[1].encode("utf-8")))
        selections = []
        for column in columns:
            name = '"' + column[1].replace('"', '""') + '"'
            selections += [
                "typeof(" + name + ")",
                "CASE WHEN typeof("
                + name
                + ")='text' THEN CAST("
                + name
                + " AS BLOB) ELSE "
                + name
                + " END",
            ]
        rows = list(
            connection.execute("SELECT " + ",".join(selections) + " FROM " + quoted)
        )
        rows.sort(
            key=lambda row: b"".join(
                cell(row[2 * index], row[2 * index + 1]) for index in pk_positions
            )
        )
        for row in rows:
            hasher.update(b"R" + struct.pack(">Q", len(columns)))
            for index in range(len(columns)):
                hasher.update(cell(row[2 * index], row[2 * index + 1]))
        hasher.update(b"E" + struct.pack(">Q", len(rows)))
    return hasher.hexdigest()
