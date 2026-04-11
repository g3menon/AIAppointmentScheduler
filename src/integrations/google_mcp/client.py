"""Real Google Calendar, Docs, and Gmail (draft-only) client for MCP-style calls."""

from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import build

from src.integrations.google_mcp.credentials_loader import load_credentials
from src.integrations.google_mcp.settings import GoogleMcpSettings, load_google_mcp_settings


def _find_repo_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        from pathlib import Path

        for parent in Path(__file__).resolve().parents:
            env_path = parent / ".env"
            if env_path.is_file():
                load_dotenv(env_path)
                return
    except ImportError:
        pass


class GoogleMcpClient:
    """Implements the three Description.md artifacts: hold, doc append, Gmail draft (never send)."""

    def __init__(self, settings: GoogleMcpSettings | None = None) -> None:
        _find_repo_dotenv()
        self.settings = settings or load_google_mcp_settings()
        self.write_attempts = 0
        creds = load_credentials()
        self._calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
        self._docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        self._gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @classmethod
    def from_env(cls) -> GoogleMcpClient:
        return cls()

    def create_calendar_hold(
        self,
        title: str,
        start_utc: str,
        end_utc: str,
        calendar_id: str,
        idempotency_key: str,
    ) -> str:
        self.write_attempts += 1
        body: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start_utc, "timeZone": "UTC"},
            "end": {"dateTime": end_utc, "timeZone": "UTC"},
            "extendedProperties": {"private": {"idempotency_key": idempotency_key}},
        }
        event = (
            self._calendar.events()
            .insert(calendarId=calendar_id, body=body, sendUpdates="none")
            .execute()
        )
        return str(event.get("id", ""))

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str:
        self.write_attempts += 1
        doc = self._docs.documents().get(documentId=doc_id).execute()
        body = doc.get("body", {})
        content = body.get("content", [])
        end_index = 1
        if content:
            end_index = max(1, int(content[-1].get("endIndex", 2)) - 1)

        requests = [
            {
                "insertText": {
                    "location": {"index": end_index},
                    "text": line.rstrip() + "\n",
                }
            }
        ]
        _ = idempotency_key  # reserved for future dedupe / audit
        result = (
            self._docs.documents()
            .batchUpdate(documentId=doc_id, body={"requests": requests})
            .execute()
        )
        replies = result.get("replies") or []
        return str(replies[0] if replies else "ok")

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str:
        self.write_attempts += 1
        msg = MIMEText(body_markdown, _subtype="plain", _charset="utf-8")
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        draft = (
            self._gmail.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )
        return str((draft.get("id") or draft.get("draft", {}).get("id") or ""))


def validate_mcp_prerequisites(settings: GoogleMcpSettings) -> None:
    if not settings.prebooking_doc_id.strip():
        raise ValueError("GOOGLE_PREBOOKING_DOC_ID is required for Docs append")
    if not settings.advisor_email_to.strip():
        raise ValueError("ADVISOR_EMAIL_TO is required for Gmail draft")
