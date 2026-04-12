from __future__ import annotations

import re
from dataclasses import dataclass

_CALENDAR_TITLE = re.compile(r"^Advisor Q&A - .+ - [A-Z]{2}-[A-Z]\d{3}$")


class McpContractError(ValueError):
    """Raised when MCP payloads do not meet contract requirements."""


class McpTransientError(RuntimeError):
    """Raised for retryable MCP failures."""


@dataclass(frozen=True)
class CalendarHoldRequest:
    title: str
    start_utc: str
    end_utc: str
    calendar_id: str
    idempotency_key: str

    def validate(self) -> None:
        if not _CALENDAR_TITLE.match(self.title):
            raise McpContractError("Calendar title must follow: Advisor Q&A - {Topic} - {Code}")
        if not self.start_utc.endswith("Z") or not self.end_utc.endswith("Z"):
            raise McpContractError("Calendar start/end must be UTC RFC3339 values")
        if not self.idempotency_key.strip():
            raise McpContractError("Calendar idempotency_key is required")


@dataclass(frozen=True)
class CalendarDeleteRequest:
    event_id: str
    calendar_id: str

    def validate(self) -> None:
        if not self.event_id.strip():
            raise McpContractError("Calendar event_id is required for delete")
        if not self.calendar_id.strip():
            raise McpContractError("Calendar calendar_id is required for delete")


@dataclass(frozen=True)
class DocsAppendRequest:
    doc_id: str
    line: str
    idempotency_key: str

    def validate(self) -> None:
        if not self.doc_id.strip():
            raise McpContractError("doc_id is required")
        if len([part for part in self.line.split("|") if part.strip()]) < 4:
            raise McpContractError("Docs pre-booking line must include topic, slot, code, action")
        if not self.idempotency_key.strip():
            raise McpContractError("Docs idempotency_key is required")


@dataclass(frozen=True)
class GmailDraftRequest:
    to: str
    subject: str
    body_markdown: str

    def validate(self) -> None:
        if not self.to.strip() or "@" not in self.to:
            raise McpContractError("Gmail draft recipient must be an email address")
        if not self.subject.strip():
            raise McpContractError("Gmail draft subject is required")


def is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, McpTransientError):
        return True
    return isinstance(exc, (TimeoutError, ConnectionError))
