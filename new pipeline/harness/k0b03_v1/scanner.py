from __future__ import annotations

import base64
import binascii
import math
import re
from collections import Counter
from typing import Any, Iterable

from canonical import canonical_sha256
from contract import ContractError, validate_detector_profile, validate_scan_request


TOKEN = r"[A-Za-z0-9_./+=-]"
HSPACE = " \t"


def _label_pattern(label: str) -> str:
    return r"[-_]".join(re.escape(part) for part in label.split("_"))


def _byte_prefix(text: str) -> list[int]:
    result = [0]
    total = 0
    for char in text:
        total += len(char.encode("utf-8"))
        result.append(total)
    return result


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _class_count(value: str) -> int:
    return sum(
        (
            any(char.isascii() and char.islower() for char in value),
            any(char.isascii() and char.isupper() for char in value),
            any(char.isascii() and char.isdigit() for char in value),
            any(char.isascii() and not char.isalnum() for char in value),
        )
    )


def _candidate(category: str, start: int, end: int, representation: str = "raw") -> dict[str, Any]:
    return {"category": category, "start": start, "end": end, "representation": representation}


def _raw_candidates(text: str, profile: dict[str, Any], include_base64: bool = True) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for match in re.finditer(r"-----BEGIN (?:(?:RSA|EC|OPENSSH) )?PRIVATE KEY-----", text, re.ASCII):
        found.append(_candidate("private_key", match.start(), match.end()))

    labels = "|".join(_label_pattern(x) for x in profile["labelled_secret"]["labels"])
    labelled = re.compile(rf"(?i)(?:{labels})[ \t]*[:=][ \t]*['\"]?({TOKEN}{{8,4096}})")
    for match in labelled.finditer(text):
        found.append(_candidate("labelled_secret", match.start(1), match.end(1)))

    for spec in profile["provider_tokens"]:
        prefix = re.escape(spec["prefix"])
        minimum = spec["suffix_minimum"]
        maximum = spec["suffix_maximum"]
        alphabet = spec.get("suffix_alphabet")
        if alphabet == "uppercase_alphanumeric":
            suffix = rf"[A-Z0-9]{{{minimum},{maximum}}}"
        elif alphabet == "ascii_alphanumeric_underscore_hyphen":
            suffix = rf"[A-Za-z0-9_-]{{{minimum},{maximum}}}"
        else:
            suffix = rf"{TOKEN}{{{minimum},{maximum}}}"
        pattern = re.compile(rf"(?<![A-Za-z0-9_-]){prefix}{suffix}(?![A-Za-z0-9_-])")
        for match in pattern.finditer(text):
            found.append(_candidate("provider_token", match.start(), match.end()))

    jwt = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{2,8192}={0,2})\.([A-Za-z0-9_-]{2,8192}={0,2})\.([A-Za-z0-9_-]{0,8192}={0,2})(?![A-Za-z0-9_.=-])")
    for match in jwt.finditer(text):
        if match.end() - match.start() <= profile["jwt"]["maximum_total_length"]:
            found.append(_candidate("jwt", match.start(), match.end()))

    authorization = re.compile(r"(?i)\bAuthorization[ \t]*:[ \t]*Bearer[ \t]+([^\s]{8,16384})")
    authorization_spans: list[tuple[int, int]] = []
    for match in authorization.finditer(text):
        authorization_spans.append((match.start(), match.end()))
        found.append(_candidate("authorization_bearer", match.start(1), match.end(1)))
    standalone = re.compile(r"(?i)\bBearer[ \t]+([^\s]{8,16384})")
    for match in standalone.finditer(text):
        if not any(start <= match.start() and match.end() <= end for start, end in authorization_spans):
            found.append(_candidate("standalone_bearer", match.start(1), match.end(1)))

    if include_base64:
        encoded = re.compile(r"(?<![A-Za-z0-9_/-])(?:[A-Za-z0-9+/]{4}){6,4096}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?(?![A-Za-z0-9_/-])|(?<![A-Za-z0-9_/-])[A-Za-z0-9_-]{24,16384}={0,2}(?![A-Za-z0-9_/-])")
        for match in encoded.finditer(text):
            value = match.group(0)
            if _strict_decode(value) is not None:
                found.append(_candidate("base64", match.start(), match.end()))

    entropy_pattern = re.compile(rf"(?<![A-Za-z0-9_./+=-])({TOKEN}{{24,4096}})(?![A-Za-z0-9_./+=-])")
    for match in entropy_pattern.finditer(text):
        value = match.group(1)
        if re.fullmatch(r"[0-9A-Fa-f]+", value) and len(value) in profile["high_entropy"]["exclude_unlabelled_pure_hex_lengths"]:
            continue
        if _class_count(value) >= profile["high_entropy"]["required_character_classes"] and _entropy(value) >= profile["high_entropy"]["shannon_bits_per_character_minimum"]:
            found.append(_candidate("high_entropy", match.start(1), match.end(1)))
    return found


def _strict_decode(value: str) -> bytes | None:
    padded = value + "=" * ((4 - len(value) % 4) % 4)
    if len(padded) % 4:
        return None
    try:
        if "-" in value or "_" in value:
            return base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
        return base64.b64decode(padded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        return None


def _physical_lines(text: str) -> list[tuple[int, int, int]]:
    lines: list[tuple[int, int, int]] = []
    start = 0
    for match in re.finditer(r"\r\n|\r|\n", text):
        lines.append((start, match.start(), match.end()))
        start = match.end()
    lines.append((start, len(text), len(text)))
    return lines


def _split_candidates(text: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    lines = _physical_lines(text)
    result: list[dict[str, Any]] = []
    for width in range(2, profile["split_line"]["adjacent_lines_maximum"] + 1):
        for index in range(0, len(lines) - width + 1):
            window = lines[index:index + width]
            pieces: list[str] = []
            spans: list[tuple[int, int]] = []
            boundaries: list[int] = []
            joined_length = 0
            for offset, (line_start, line_end, _) in enumerate(window):
                raw = text[line_start:line_end]
                left = len(raw) - len(raw.lstrip(HSPACE)) if offset else 0
                right = len(raw.rstrip(HSPACE))
                if offset == width - 1:
                    right = len(raw)
                piece = raw[left:right]
                if not piece:
                    continue
                pieces.append(piece)
                spans.append((line_start + left, line_start + right))
                joined_length += len(piece)
                if offset < width - 1:
                    boundaries.append(joined_length)
            joined = "".join(pieces)
            if not joined or len(joined) > profile["split_line"]["combined_characters_maximum"]:
                continue
            for item in _raw_candidates(joined, profile):
                if item["category"] not in {"labelled_secret", "jwt", "authorization_bearer", "standalone_bearer", "provider_token", "high_entropy", "base64"}:
                    continue
                if not any(item["start"] < boundary < item["end"] for boundary in boundaries):
                    continue
                result.append({"category": item["category"], "representation": "split_line", "char_spans": spans, "length": item["end"] - item["start"]})
    return result


def _deduplicate(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    exact: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        key = (item["detector_category"], item["representation_kind"], tuple(tuple(x) for x in item["original_byte_spans"]))
        exact[key] = item
    ordered = sorted(exact.values(), key=lambda x: (x["original_byte_spans"][0][0], x["precedence"], -x["match_length"], x["detector_category"]))
    retained: list[dict[str, Any]] = []
    for item in ordered:
        spans = item["original_byte_spans"]
        first_start, first_end = spans[0]
        overlap_index = None
        for index, prior in enumerate(retained):
            if prior["detector_category"] != item["detector_category"] or prior["representation_kind"] != item["representation_kind"]:
                continue
            prior_start, prior_end = prior["original_byte_spans"][0]
            if first_start < prior_end and prior_start < first_end:
                overlap_index = index
                break
        if overlap_index is None:
            retained.append(item)
        else:
            prior = retained[overlap_index]
            prior_start = prior["original_byte_spans"][0][0]
            if first_start < prior_start or (first_start == prior_start and item["match_length"] > prior["match_length"]):
                retained[overlap_index] = item
    return sorted(retained, key=lambda x: (x["original_byte_spans"][0][0], x["precedence"], -x["match_length"], x["detector_category"]))


def scan_bytes(data: bytes, source_id: str, safe_source_binding: str, caller_byte_cap: int, profile: dict[str, Any]) -> dict[str, Any]:
    validate_detector_profile(profile)
    profile_hash = canonical_sha256(profile)
    cap = min(caller_byte_cap, profile["input"]["maximum_bytes"])
    if caller_byte_cap < 1 or len(data) > cap:
        return _result(profile, profile_hash, [], blocked=True, overflow=False)
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return _result(profile, profile_hash, [], blocked=True, overflow=False)
    prefixes = _byte_prefix(text)
    precedence = {name: index for index, name in enumerate(profile["precedence"])}
    raw_items = _raw_candidates(text, profile)
    findings: list[dict[str, Any]] = []
    for item in raw_items:
        spans = [[prefixes[item["start"]], prefixes[item["end"]]]]
        findings.append(_finding(item["category"], item["representation"], spans, item["end"] - item["start"], source_id, safe_source_binding, profile_hash, precedence))
        if item["category"] == "base64":
            decoded = _strict_decode(text[item["start"]:item["end"]])
            if decoded is not None and len(decoded) <= profile["base64"]["decoded_bytes_maximum"]:
                try:
                    decoded_text = decoded.decode("utf-8", "strict")
                except UnicodeDecodeError:
                    decoded_text = ""
                if decoded_text:
                    for nested in _raw_candidates(decoded_text, profile, include_base64=False):
                        if nested["category"] in {"labelled_secret", "jwt", "authorization_bearer", "standalone_bearer", "provider_token", "high_entropy"}:
                            findings.append(_finding(nested["category"], "base64_decoded", spans, nested["end"] - nested["start"], source_id, safe_source_binding, profile_hash, precedence))
    for item in _split_candidates(text, profile):
        byte_spans = [[prefixes[start], prefixes[end]] for start, end in item["char_spans"]]
        findings.append(_finding(item["category"], item["representation"], byte_spans, item["length"], source_id, safe_source_binding, profile_hash, precedence))
    findings = _deduplicate(findings)
    overflow = len(findings) > profile["input"]["maximum_findings"]
    findings = findings[:profile["input"]["maximum_findings"]]
    for index, finding in enumerate(findings, 1):
        finding["finding_id"] = f"F{index:04d}"
        finding.pop("precedence", None)
    return _result(profile, profile_hash, findings, blocked=bool(findings) or overflow, overflow=overflow)


def _finding(category: str, representation: str, spans: list[list[int]], length: int, source_id: str, safe_binding: str, profile_hash: str, precedence: dict[str, int]) -> dict[str, Any]:
    precedence_name = category
    if category == "private_key":
        precedence_name = "private_key"
    elif category == "provider_token":
        precedence_name = "provider_token"
    elif category == "authorization_bearer":
        precedence_name = "authorization_bearer"
    elif category == "standalone_bearer":
        precedence_name = "standalone_bearer"
    return {
        "finding_id": "pending",
        "detector_category": category,
        "detector_version": "1.0.0",
        "source_id": source_id,
        "original_byte_spans": spans,
        "match_length": length,
        "scanner_profile_hash": profile_hash,
        "safe_source_binding": safe_binding,
        "representation_kind": representation,
        "blocking_disposition": "block_run_and_enqueue_human",
        "precedence": precedence.get(precedence_name, precedence.get("split_line", 99)),
    }


def _result(profile: dict[str, Any], profile_hash: str, findings: list[dict[str, Any]], blocked: bool, overflow: bool) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "result": "blocked" if blocked else "no_shape_finding_observed",
        "authorized": False,
        "findings": findings,
        "overflow": overflow,
        "profile_sha256": profile_hash,
        "hygiene_statement": profile["mandatory_hygiene_statement"],
    }


def scan_request(request: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    validate_scan_request(request)
    validate_detector_profile(profile)
    expected = canonical_sha256(profile)
    if request["profile_sha256"] != expected:
        raise ContractError("stale detector profile pin")
    combined: list[dict[str, Any]] = []
    overflow = False
    for field in request["fields"]:
        result = scan_bytes(field["text_utf8"].encode("utf-8"), field["source_id"], field["safe_source_binding"], request["caller_byte_cap"], profile)
        combined.extend(result["findings"])
        overflow = overflow or result["overflow"]
    combined = combined[:profile["input"]["maximum_findings"]]
    for index, finding in enumerate(combined, 1):
        finding["finding_id"] = f"F{index:04d}"
    return _result(profile, expected, combined, bool(combined) or overflow, overflow)
