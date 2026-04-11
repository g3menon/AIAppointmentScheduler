"""PII detection gate per Architecture.md §11.10."""

import re

_PHONE = re.compile(r"\b\d{10}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_ACCOUNT = re.compile(r"\b(?:\d[ -]?){12,16}\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_DOB = re.compile(
    r"\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"
    r"|\b(?:\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b"
)

_ALL_PATTERNS = [_PHONE, _EMAIL, _ACCOUNT, _PAN, _AADHAAR, _DOB]


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in _ALL_PATTERNS)
