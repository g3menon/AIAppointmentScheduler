from __future__ import annotations

from fastmcp import FastMCP

from src.integrations.google_mcp.client import GoogleMcpClient

mcp = FastMCP("advisor-booking")

_client: GoogleMcpClient | None = None


def _get_client() -> GoogleMcpClient:
    global _client
    if _client is None:
        _client = GoogleMcpClient.from_env()
    return _client


@mcp.tool()
def calendar_create_hold(
    title: str,
    start_utc: str,
    end_utc: str,
    calendar_id: str,
    idempotency_key: str,
) -> str:
    return _get_client().create_calendar_hold(title, start_utc, end_utc, calendar_id, idempotency_key)


@mcp.tool()
def calendar_delete_hold(event_id: str, calendar_id: str) -> None:
    client = _get_client()
    client.write_attempts += 1
    client._calendar.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return None


@mcp.tool()
def docs_append_prebooking(doc_id: str, line: str, idempotency_key: str) -> str:
    return _get_client().append_prebooking_log(doc_id, line, idempotency_key)


@mcp.tool()
def gmail_create_draft(to: str, subject: str, body_markdown: str) -> str:
    return _get_client().create_gmail_draft(to, subject, body_markdown)
