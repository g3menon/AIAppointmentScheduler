from __future__ import annotations

from dataclasses import dataclass, field

from src.integrations.google_mcp.backing_services import McpTransientError
from src.integrations.google_mcp.settings import GoogleMcpSettings


@dataclass
class FakeGoogleMcpClient:
    """CI-safe in-memory fake with optional transient failures."""

    settings: GoogleMcpSettings
    write_attempts: int = 0
    calendar_holds: list[dict] = field(default_factory=list)
    doc_appends: list[dict] = field(default_factory=list)
    gmail_drafts: list[dict] = field(default_factory=list)
    fail_next_calendar: int = 0
    fail_next_doc: int = 0
    fail_next_gmail: int = 0

    def create_calendar_hold(
        self,
        title: str,
        start_utc: str,
        end_utc: str,
        calendar_id: str,
        idempotency_key: str,
    ) -> str:
        self.write_attempts += 1
        if self.fail_next_calendar > 0:
            self.fail_next_calendar -= 1
            raise McpTransientError("transient calendar write failure")
        event_id = f"fake_event_{len(self.calendar_holds) + 1}"
        self.calendar_holds.append(
            {
                "event_id": event_id,
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "calendar_id": calendar_id,
                "idempotency_key": idempotency_key,
            }
        )
        return event_id

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str:
        self.write_attempts += 1
        if self.fail_next_doc > 0:
            self.fail_next_doc -= 1
            raise McpTransientError("transient docs append failure")
        reply = f"fake_doc_reply_{len(self.doc_appends) + 1}"
        self.doc_appends.append({"reply": reply, "doc_id": doc_id, "line": line, "idempotency_key": idempotency_key})
        return reply

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str:
        self.write_attempts += 1
        if self.fail_next_gmail > 0:
            self.fail_next_gmail -= 1
            raise McpTransientError("transient gmail draft failure")
        draft_id = f"fake_draft_{len(self.gmail_drafts) + 1}"
        self.gmail_drafts.append({"draft_id": draft_id, "to": to, "subject": subject, "body_markdown": body_markdown})
        return draft_id

