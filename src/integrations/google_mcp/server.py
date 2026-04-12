from __future__ import annotations

from fastmcp import FastMCP

from src.integrations.google_mcp.client import GoogleMcpClient
from src.integrations.google_mcp.mcp_tool_dispatch import dispatch_mcp_tool

mcp = FastMCP("advisor-booking")

_client: GoogleMcpClient | None = None


def _get_client() -> GoogleMcpClient:
    global _client
    if _client is None:
        _client = GoogleMcpClient.from_env()
    return _client


def set_client_for_tests(client: GoogleMcpClient | None) -> None:
    global _client
    _client = client


@mcp.tool()
def calendar_create_hold(
    title: str,
    start_utc: str,
    end_utc: str,
    calendar_id: str,
    idempotency_key: str,
) -> str:
    return str(
        dispatch_mcp_tool(
            _get_client(),
            "calendar_create_hold",
            {
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "calendar_id": calendar_id,
                "idempotency_key": idempotency_key,
            },
        )
        or ""
    )


@mcp.tool()
def docs_append_prebooking(doc_id: str, line: str, idempotency_key: str) -> str:
    return str(
        dispatch_mcp_tool(
            _get_client(),
            "docs_append_prebooking",
            {"doc_id": doc_id, "line": line, "idempotency_key": idempotency_key},
        )
        or ""
    )


@mcp.tool()
def gmail_create_draft(to: str, subject: str, body_markdown: str) -> str:
    return str(
        dispatch_mcp_tool(
            _get_client(),
            "gmail_create_draft",
            {"to": to, "subject": subject, "body_markdown": body_markdown},
        )
        or ""
    )
