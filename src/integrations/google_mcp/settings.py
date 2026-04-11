"""Environment-driven settings for Google Calendar / Docs / Gmail MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleMcpSettings:
    calendar_id: str
    prebooking_doc_id: str
    advisor_email_to: str
    idempotency_namespace: str
    auth_mode: str  # oauth | service_account


def load_google_mcp_settings() -> GoogleMcpSettings:
    return GoogleMcpSettings(
        calendar_id=os.environ.get("GOOGLE_CALENDAR_ID", "primary"),
        prebooking_doc_id=os.environ.get("GOOGLE_PREBOOKING_DOC_ID", ""),
        advisor_email_to=os.environ.get("ADVISOR_EMAIL_TO", ""),
        idempotency_namespace=os.environ.get("IDEMPOTENCY_NAMESPACE", "booking"),
        auth_mode=os.environ.get("GOOGLE_AUTH_MODE", "oauth").strip().lower(),
    )
