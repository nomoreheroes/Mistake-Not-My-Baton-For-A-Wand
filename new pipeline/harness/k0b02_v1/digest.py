from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
from dataclasses import dataclass
from typing import Any

from .canonical import ContractError, json_bytes, require, sha256


HEADER = b"pipeline-v2.sqlite-content-digest-v1\x00"


def u64(value: int) -> bytes:
    require(type(value) is int and 0 <= value < 2**64, "digest:u64")
    return struct.pack(">Q", value)


def name_frame(value: str) -> bytes:
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ContractError("digest:name_UTF8") from exc
    return u64(len(raw)) + raw


def cell_frame(storage: str, value: Any) -> bytes:
    if storage == "null":
        require(value is None, "digest:NULL_type")
        tag, raw = b"N", b""
    elif storage == "integer":
        require(type(value) is int and -(2**63) <= value < 2**63, "digest:INTEGER_type")
        tag, raw = b"i", struct.pack(">q", value)
    elif storage == "real":
        require(
            type(value) is float and not math.isnan(value), "digest:REAL_NaN_or_type"
        )
        tag, raw = b"r", struct.pack(">d", value)
    elif storage == "text":
        require(type(value) is bytes, "digest:TEXT_raw_bytes_required")
        try:
            value.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise ContractError("digest:invalid_UTF8") from exc
        tag, raw = b"t", value
    elif storage == "blob":
        require(type(value) is bytes, "digest:BLOB_type")
        tag, raw = b"b", value
    else:
        raise ContractError("digest:unsupported_storage")
    return tag + u64(len(raw)) + raw


def primary_key_frame(*values: Any) -> bytes:
    result = bytearray()
    for value in values:
        if value is None:
            result.extend(cell_frame("null", None))
        elif type(value) is int:
            result.extend(cell_frame("integer", value))
        elif type(value) is float:
            result.extend(cell_frame("real", value))
        elif type(value) is bytes:
            result.extend(cell_frame("blob", value))
        elif type(value) is str:
            result.extend(cell_frame("text", value.encode("utf-8", "strict")))
        else:
            raise ContractError("digest:unsupported_PK_type")
    return bytes(result)


def identifier(name: str) -> str:
    require(
        isinstance(name, str) and name and "\x00" not in name, "digest:SQL_identifier"
    )
    return '"' + name.replace('"', '""') + '"'


def schema_rows(connection: sqlite3.Connection) -> tuple[tuple[Any, ...], ...]:
    rows = tuple(
        connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY CAST(type AS BLOB),CAST(name AS BLOB)"
        )
    )
    return rows


def schema_fingerprint(connection: sqlite3.Connection) -> str:
    return sha256(json_bytes([list(row) for row in schema_rows(connection)]))


@dataclass(frozen=True)
class HistoricalTable:
    name: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    migration_version_ceiling: int | None = None


def historical_manifest(connection: sqlite3.Connection) -> tuple[HistoricalTable, ...]:
    tables = [
        r[0]
        for r in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY CAST(name AS BLOB)"
        )
    ]
    manifest = []
    for table in tables:
        info = list(connection.execute("PRAGMA table_info(" + identifier(table) + ")"))
        columns = tuple(row[1] for row in sorted(info, key=lambda row: row[0]))
        pk = tuple(
            row[1]
            for row in sorted((row for row in info if row[5]), key=lambda row: row[5])
        )
        require(bool(pk), "digest:missing_declared_PK:" + table)
        manifest.append(
            HistoricalTable(
                table, columns, pk, 3 if table == "schema_migrations" else None
            )
        )
    return tuple(manifest)


def content_digest(
    connection: sqlite3.Connection,
    manifest: tuple[HistoricalTable, ...],
    *,
    batch_rows: int = 512,
    source_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    require(type(batch_rows) is int and 0 < batch_rows <= 512, "digest:batch_bound")
    require(
        isinstance(manifest, tuple)
        and len({t.name for t in manifest}) == len(manifest),
        "digest:manifest",
    )
    require(
        [t.name.encode("utf-8") for t in manifest]
        == sorted(t.name.encode("utf-8") for t in manifest),
        "digest:table_order",
    )
    connection.create_function("__k0b01_key", -1, primary_key_frame, deterministic=True)
    aggregate = hashlib.sha256(HEADER)
    summaries: list[dict[str, Any]] = []
    maximum_batch = 0
    for table in manifest:
        require(
            table.columns
            and table.primary_key
            and set(table.primary_key) <= set(table.columns),
            "digest:manifest_PK",
        )
        source_name = (source_names or {}).get(table.name, table.name)
        info = list(
            connection.execute("PRAGMA table_info(" + identifier(source_name) + ")")
        )
        require(
            tuple(row[1] for row in sorted(info, key=lambda row: row[0]))
            == table.columns,
            "digest:column_projection",
        )
        live_pk = tuple(
            row[1]
            for row in sorted((row for row in info if row[5]), key=lambda row: row[5])
        )
        require(live_pk == table.primary_key, "digest:PK_projection")
        prefix = name_frame(table.name) + b"".join(name_frame(c) for c in table.columns)
        aggregate.update(prefix)
        per_table = hashlib.sha256(HEADER + prefix)
        pk_columns = ",".join(identifier(c) for c in table.primary_key)
        key_sql = "__k0b01_key(" + pk_columns + ")"
        selections = [key_sql]
        for column in table.columns:
            quoted = identifier(column)
            selections.extend(
                [
                    "typeof(" + quoted + ")",
                    "CASE WHEN typeof("
                    + quoted
                    + ")='text' THEN CAST("
                    + quoted
                    + " AS BLOB) ELSE "
                    + quoted
                    + " END",
                ]
            )
        query = "SELECT " + ",".join(selections) + " FROM " + identifier(source_name)
        if table.migration_version_ceiling is not None:
            require(
                table.name == "schema_migrations"
                and table.migration_version_ceiling == 3,
                "digest:exclusion_manifest",
            )
            query += " WHERE version<=3"
        query += " ORDER BY " + key_sql
        row_count = 0
        previous: bytes | None = None
        row_digests: dict[str, str] = {}
        try:
            cursor = connection.execute(query)
            while True:
                batch = cursor.fetchmany(batch_rows)
                maximum_batch = max(maximum_batch, len(batch))
                if not batch:
                    break
                for row in batch:
                    key = row[0]
                    require(
                        type(key) is bytes and (previous is None or previous < key),
                        "digest:duplicate_or_unordered_PK",
                    )
                    previous = key
                    header = b"R" + u64(len(table.columns))
                    aggregate.update(header)
                    per_table.update(header)
                    per_row = hashlib.sha256(header)
                    for index in range(len(table.columns)):
                        frame = cell_frame(row[1 + index * 2], row[2 + index * 2])
                        aggregate.update(frame)
                        per_table.update(frame)
                        per_row.update(frame)
                    row_digests[key.hex()] = per_row.hexdigest()
                    row_count += 1
            suffix = b"E" + u64(row_count)
            aggregate.update(suffix)
            per_table.update(suffix)
        except (sqlite3.Error, UnicodeError) as exc:
            raise ContractError("digest:SQL_or_UTF8") from exc
        summaries.append(
            {
                "table": table.name,
                "rows": row_count,
                "sha256": per_table.hexdigest(),
                "row_digests_by_typed_PK": row_digests,
            }
        )
    return {
        "profile": "pipeline-v2.sqlite-content-digest-v1",
        "sha256": aggregate.hexdigest(),
        "tables": summaries,
        "maximum_batch_rows_observed": maximum_batch,
    }


def equal_historical(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["sha256"] == right["sha256"] and left["tables"] == right["tables"]
