"""Test-only MCP stand-in: records calls without Google (used when PYTEST_CURRENT_TEST is set)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.integrations.google_mcp.settings import GoogleMcpSettings, load_google_mcp_settings


@dataclass
class RecordingGoogleMcpClient:
    """Not a Google fake service — in-memory recorder for automated tests."""

    write_attempts: int = 0
    calendar_holds: list[dict] = field(default_factory=list)
    calendar_deletes: list[dict] = field(default_factory=list)
    doc_appends: list[dict] = field(default_factory=list)
    gmail_drafts: list[dict] = field(default_factory=list)
    settings: GoogleMcpSettings = field(default_factory=load_google_mcp_settings)

    def create_calendar_hold(
        self,
        title: str,
        start_utc: str,
        end_utc: str,
        calendar_id: str,
        idempotency_key: str,
    ) -> str:
        self.write_attempts += 1
        payload = {
            "title": title,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "calendar_id": calendar_id,
            "idempotency_key": idempotency_key,
        }
        self.calendar_holds.append(payload)
        return f"rec_event_{len(self.calendar_holds)}"

    def delete_calendar_hold(self, event_id: str, calendar_id: str) -> str:
        self.write_attempts += 1
        self.calendar_deletes.append({"event_id": event_id, "calendar_id": calendar_id})
        return event_id

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str:
        self.write_attempts += 1
        self.doc_appends.append({"doc_id": doc_id, "line": line, "idempotency_key": idempotency_key})
        return "rec_doc_ok"

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str:
        self.write_attempts += 1
        self.gmail_drafts.append({"to": to, "subject": subject, "body_markdown": body_markdown})
        return f"rec_draft_{len(self.gmail_drafts)}"
