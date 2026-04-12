from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_FORBIDDEN_KEYS = {
    "raw_user_text",
    "user_text",
    "transcript",
    "raw_transcript",
    "email",
    "phone",
}


@dataclass(frozen=True)
class AuditRecord:
    timestamp_utc: str
    session_id: str
    status: dict[str, Any]


_AUDIT_RECORDS: list[AuditRecord] = []


def _sanitize_status(status: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in status.items() if k not in _FORBIDDEN_KEYS}


def record_artifact_status(session_id: str, status: dict[str, Any]) -> None:
    _AUDIT_RECORDS.append(
        AuditRecord(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            status=_sanitize_status(status),
        )
    )


def get_audit_records() -> list[AuditRecord]:
    return list(_AUDIT_RECORDS)


def clear_audit_records() -> None:
    _AUDIT_RECORDS.clear()
