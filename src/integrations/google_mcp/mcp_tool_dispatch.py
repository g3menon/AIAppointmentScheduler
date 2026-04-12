"""Single dispatch for MCP tool names → GoogleMcpClient (shared by FastMCP server and LLM tool-calling)."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol

from src.integrations.google_mcp.backing_services import (
    CalendarDeleteRequest,
    CalendarHoldRequest,
    DocsAppendRequest,
    GmailDraftRequest,
    is_transient_error,
)


class McpOperations(Protocol):
    settings: Any
    write_attempts: int

    def create_calendar_hold(
        self, title: str, start_utc: str, end_utc: str, calendar_id: str, idempotency_key: str
    ) -> str: ...

    def delete_calendar_hold(self, event_id: str, calendar_id: str) -> str: ...

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str: ...

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str: ...


_IDEMPOTENT_RESULTS: dict[str, str | None] = {}


def _idempotency_key(name: str, args: dict) -> str:
    if "idempotency_key" in args and str(args["idempotency_key"]).strip():
        return f"{name}:{args['idempotency_key']}"
    if name == "gmail_create_draft":
        raw = f"{args.get('to','')}|{args.get('subject','')}|{args.get('body_markdown','')}"
        return f"{name}:hash:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
    return ""


def _with_retry(call):
    max_attempts = 3
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            return call()
        except Exception as exc:  # pragma: no cover - trivial pass-through on last attempt
            last_exc = exc
            if not is_transient_error(exc):
                raise
    assert last_exc is not None
    raise last_exc


def dispatch_mcp_tool(client: McpOperations, name: str, args: dict) -> str | None:
    cache_key = _idempotency_key(name, args)
    if cache_key and cache_key in _IDEMPOTENT_RESULTS:
        return _IDEMPOTENT_RESULTS[cache_key]

    if name == "calendar_delete_hold":
        req = CalendarDeleteRequest(
            event_id=str(args["event_id"]),
            calendar_id=str(args["calendar_id"]),
        )
        req.validate()
        result = _with_retry(lambda: client.delete_calendar_hold(req.event_id, req.calendar_id))
        return result
    if name == "calendar_create_hold":
        req = CalendarHoldRequest(
            title=str(args["title"]),
            start_utc=str(args["start_utc"]),
            end_utc=str(args["end_utc"]),
            calendar_id=str(args["calendar_id"]),
            idempotency_key=str(args["idempotency_key"]),
        )
        req.validate()
        result = _with_retry(
            lambda: client.create_calendar_hold(
                req.title,
                req.start_utc,
                req.end_utc,
                req.calendar_id,
                req.idempotency_key,
            )
        )
        if cache_key:
            _IDEMPOTENT_RESULTS[cache_key] = result
        return result
    if name == "docs_append_prebooking":
        req = DocsAppendRequest(
            doc_id=str(args["doc_id"]),
            line=str(args["line"]),
            idempotency_key=str(args["idempotency_key"]),
        )
        req.validate()
        result = _with_retry(lambda: client.append_prebooking_log(req.doc_id, req.line, req.idempotency_key))
        if cache_key:
            _IDEMPOTENT_RESULTS[cache_key] = result
        return result
    if name == "gmail_create_draft":
        req = GmailDraftRequest(
            to=str(args["to"]),
            subject=str(args["subject"]),
            body_markdown=str(args["body_markdown"]),
        )
        req.validate()
        result = _with_retry(lambda: client.create_gmail_draft(req.to, req.subject, req.body_markdown))
        if cache_key:
            _IDEMPOTENT_RESULTS[cache_key] = result
        return result
    raise ValueError(f"Unknown MCP tool: {name}")
