"""Observability compliance gate — verifies no PII leaks into log/audit outputs.

Used by Phase 8 tests as a post-hoc check on logged events and audit records.
Can also be called as a CI gate step.
"""

from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b\d{10}\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")

_PII_PATTERNS = [
    ("email", _EMAIL),
    ("phone", _PHONE),
    ("pan", _PAN),
    ("aadhaar", _AADHAAR),
]

_FORBIDDEN_AUDIT_KEYS = {
    "raw_user_text",
    "user_text",
    "transcript",
    "raw_transcript",
    "email",
    "phone",
}


class PIILeakError(AssertionError):
    """Raised when PII is detected in observability outputs."""


def scan_for_pii(text: str) -> list[str]:
    """Return list of PII types found in *text*, empty if clean."""
    return [name for name, pat in _PII_PATTERNS if pat.search(text)]


def assert_payload_pii_free(payload: dict[str, Any], context: str = "") -> None:
    """Raise PIILeakError if any value in *payload* contains raw PII."""
    for key, value in payload.items():
        text = _flatten_to_text(value)
        found = scan_for_pii(text)
        if found:
            raise PIILeakError(
                f"PII detected in {context}payload[{key!r}]: "
                f"types={found}"
            )


def assert_audit_keys_clean(status: dict[str, Any]) -> None:
    """Raise PIILeakError if audit record contains forbidden raw-text keys."""
    forbidden_present = set(status.keys()) & _FORBIDDEN_AUDIT_KEYS
    if forbidden_present:
        raise PIILeakError(
            f"Forbidden keys in audit record: {sorted(forbidden_present)}"
        )


def _flatten_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_to_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_to_text(v) for v in value)
    return str(value)
