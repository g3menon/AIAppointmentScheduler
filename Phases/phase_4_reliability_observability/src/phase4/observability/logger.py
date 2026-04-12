from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REQUIRED_FIELDS = {
    "session_id",
    "stage",
    "intent",
    "booking_code",
    "error_type",
    "latency_ms",
}

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b\d{10}\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")


@dataclass(frozen=True)
class LoggedEvent:
    timestamp_utc: str
    event_name: str
    payload: dict[str, Any]


_EVENTS: list[LoggedEvent] = []


def _redact_text(text: str) -> str:
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", text)
    redacted = _PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _PAN.sub("[REDACTED_PAN]", redacted)
    redacted = _AADHAAR.sub("[REDACTED_AADHAAR]", redacted)
    return redacted


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def log_event(event_name: str, payload: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(payload.keys()))
    if missing:
        raise ValueError(f"Missing required log fields: {', '.join(missing)}")

    safe_payload = _redact_value(payload)
    _EVENTS.append(
        LoggedEvent(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            event_name=event_name,
            payload=safe_payload,
        )
    )


def get_logged_events() -> list[LoggedEvent]:
    return list(_EVENTS)


def clear_logged_events() -> None:
    _EVENTS.clear()
