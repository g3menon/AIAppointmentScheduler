"""Single dispatch for MCP tool names → GoogleMcpClient (shared by FastMCP server and LLM tool-calling)."""

from __future__ import annotations

from typing import Any, Protocol


class McpOperations(Protocol):
    settings: Any
    write_attempts: int

    def create_calendar_hold(
        self, title: str, start_utc: str, end_utc: str, calendar_id: str, idempotency_key: str
    ) -> str: ...

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str: ...

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str: ...


def dispatch_mcp_tool(client: McpOperations, name: str, args: dict) -> str | None:
    if name == "calendar_create_hold":
        return client.create_calendar_hold(
            str(args["title"]),
            str(args["start_utc"]),
            str(args["end_utc"]),
            str(args["calendar_id"]),
            str(args["idempotency_key"]),
        )
    if name == "docs_append_prebooking":
        return client.append_prebooking_log(
            str(args["doc_id"]),
            str(args["line"]),
            str(args["idempotency_key"]),
        )
    if name == "gmail_create_draft":
        return client.create_gmail_draft(
            str(args["to"]),
            str(args["subject"]),
            str(args["body_markdown"]),
        )
    raise ValueError(f"Unknown MCP tool: {name}")
