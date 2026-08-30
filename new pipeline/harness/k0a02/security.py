"""Finite fail-closed secret/PII screening for the fixture-only F00 slice."""

from __future__ import annotations

import re


class SensitiveDataError(RuntimeError):
    """Untrusted text contains data that F00 is not authorized to handle."""


_PATTERNS = (
    (
        "labelled_secret",
        re.compile(
            r"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret|"
            r"authorization|private[_-]?key|client[_-]?secret|aws[_-]?access[_-]?key[_-]?id)"
            r"[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{8,}"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "email_address",
        re.compile(r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9.-])"),
    ),
    ("us_ssn", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
)
_PAYMENT_CARD_RE = re.compile(r"(?<![A-Za-z0-9])(?:\d[ -]?){12,18}\d(?![A-Za-z0-9])")


def _luhn_valid(candidate: str) -> bool:
    digits = [int(value) for value in candidate if value.isdigit()]
    parity = len(digits) % 2
    total = 0
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def scan_untrusted_text(value: str, *, label: str) -> None:
    """Reject the small explicit family of secret/PII forms governed for F00."""

    if not isinstance(value, str):
        raise SensitiveDataError(f"{label} is not text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SensitiveDataError(f"{label} is not strict UTF-8 text") from exc
    for category, pattern in _PATTERNS:
        if pattern.search(value) is not None:
            raise SensitiveDataError(
                f"{label} contains prohibited secret/PII pattern ({category})"
            )
    if any(_luhn_valid(match.group(0)) for match in _PAYMENT_CARD_RE.finditer(value)):
        raise SensitiveDataError(f"{label} contains prohibited secret/PII pattern (payment_card)")
