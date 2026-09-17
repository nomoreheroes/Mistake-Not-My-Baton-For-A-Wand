from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.tokens import AliasToken, AnchorToken


class ContractError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_value(value: Any) -> None:
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        require(math.isfinite(value), "canonical:nonfinite")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ContractError("canonical:UTF8") from exc
        return
    if isinstance(value, list):
        for item in value:
            canonical_value(item)
        return
    require(isinstance(value, dict), "canonical:type")
    for key, item in value.items():
        require(isinstance(key, str), "canonical:key")
        canonical_value(key)
        canonical_value(item)


def json_bytes(value: Any) -> bytes:
    canonical_value(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "JSON:duplicate_key")
        result[key] = value
    return result


def text_bytes(raw: bytes) -> str:
    require(not raw.startswith(b"\xef\xbb\xbf"), "text:BOM")
    require(b"\r" not in raw, "text:CR")
    require(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), "text:final_LF")
    try:
        return raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ContractError("text:UTF8") from exc


def load_json(raw: bytes) -> Any:
    try:
        result = json.loads(
            text_bytes(raw),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ContractError("JSON:nonfinite")
            ),
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("JSON:invalid") from exc
    canonical_value(result)
    return result


def load_yaml(raw: bytes, *, historical: bool = False) -> dict[str, Any]:
    parser = YAML(typ="safe", pure=True)
    parser.allow_duplicate_keys = False
    try:
        text = raw.decode("utf-8", "strict") if historical else text_bytes(raw)
    except UnicodeError as exc:
        raise ContractError("YAML:UTF8") from exc
    try:
        require(
            not any(
                isinstance(token, (AliasToken, AnchorToken))
                for token in parser.scan(text)
            ),
            "YAML:aliases",
        )
        value = parser.load(text)
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError("YAML:invalid") from exc
    require(isinstance(value, dict), "YAML:object")
    return value


def yaml_bytes(value: dict[str, Any]) -> bytes:
    def quote(item: Any) -> Any:
        if isinstance(item, str) and re.fullmatch("[0-9a-f]{64}", item):
            return DoubleQuotedScalarString(item)
        if isinstance(item, dict):
            return {key: quote(item[key]) for key in sorted(item)}
        if isinstance(item, list):
            return [quote(part) for part in item]
        return item

    parser = YAML()
    parser.default_flow_style = False
    parser.width = 2147483647
    parser.indent(mapping=2, sequence=4, offset=2)
    parser.representer.ignore_aliases = lambda *_: True
    output = StringIO()
    parser.dump(quote(value), output)
    raw = (
        "\n".join(line.rstrip() for line in output.getvalue().splitlines()) + "\n"
    ).encode("utf-8")
    require(load_yaml(raw) == value, "YAML:lossless_roundtrip")
    return raw


def no_reparse(path: Path) -> None:
    for current in (path, *path.parents):
        try:
            info = current.lstat()
        except OSError as exc:
            raise ContractError("path:missing") from exc
        require(
            not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & 0x400,
            "path:reparse",
        )


def repository_file(root: Path, relative: str, allowed: set[str]) -> Path:
    require(relative in allowed, "path:not_authorized")
    part = PurePosixPath(relative)
    require(
        not part.is_absolute()
        and str(part) == relative
        and ".." not in part.parts
        and "\\" not in relative
        and not re.match("^[A-Za-z]:", relative),
        "path:escape",
    )
    candidate = root.joinpath(*part.parts)
    no_reparse(candidate)
    require(
        candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()),
        "path:identity",
    )
    return candidate


def verify_pin(path: Path, pin: dict[str, Any]) -> bytes:
    raw = path.read_bytes()
    require(type(pin.get("bytes")) is int and len(raw) == pin["bytes"], "pin:length")
    require(
        isinstance(pin.get("sha256"), str)
        and re.fullmatch("[0-9a-f]{64}", pin["sha256"]) is not None
        and sha256(raw) == pin["sha256"],
        "pin:SHA256",
    )
    return raw
