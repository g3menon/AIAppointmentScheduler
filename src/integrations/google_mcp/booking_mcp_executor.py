"""Run the Description.md MCP trio via Gemini function-calling or direct Google client.

When ``GEMINI_API_KEY`` is set (and not under pytest), Gemini uses **automatic function calling**
with Python callables whose schemas match the FastMCP tools in ``server.py``. Each callable
executes the real Google operation using **orchestrator-supplied canonical arguments** (model
arguments are ignored) so artifacts stay policy-safe.

Otherwise: direct ``dispatch_mcp_tool`` (tests, or no API key). Set ``BOOKING_MCP_DRIVER=direct``
to force the direct path even with a Gemini key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.integrations.google_mcp.client import GoogleMcpClient, validate_mcp_prerequisites
from src.integrations.google_mcp.mcp_tool_dispatch import McpOperations, dispatch_mcp_tool


@dataclass(frozen=True)
class BookingMcpBundle:
    calendar_title: str
    start_utc: str
    end_utc: str
    calendar_id: str
    calendar_idempotency_key: str
    doc_id: str
    doc_line: str
    doc_idempotency_key: str
    gmail_to: str
    gmail_subject: str
    gmail_body: str


@dataclass(frozen=True)
class BookingMcpResult:
    event_id: str
    doc_reply: str
    draft_id: str


@dataclass(frozen=True)
class BookingMcpExecutionError(RuntimeError):
    stage: str
    artifact_status: dict[str, str]
    cause: str

    def __str__(self) -> str:
        return f"MCP execution failed at {self.stage}: {self.cause}"


def _use_llm_mcp_path() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if os.environ.get("BOOKING_MCP_DRIVER", "").strip().lower() == "direct":
        return False
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def run_booking_mcp_triplet(client: McpOperations, bundle: BookingMcpBundle) -> BookingMcpResult:
    if isinstance(client, GoogleMcpClient):
        validate_mcp_prerequisites(client.settings)

    if _use_llm_mcp_path():
        return _run_via_gemini_automatic_function_calling(client, bundle)
    return _run_direct(client, bundle)


def _run_direct(client: McpOperations, bundle: BookingMcpBundle) -> BookingMcpResult:
    status = {"calendar": "pending", "docs": "pending", "gmail": "pending"}
    event_id = ""
    doc_reply = ""
    draft_id = ""

    try:
        event_id = str(
            dispatch_mcp_tool(
                client,
                "calendar_create_hold",
                {
                    "title": bundle.calendar_title,
                    "start_utc": bundle.start_utc,
                    "end_utc": bundle.end_utc,
                    "calendar_id": bundle.calendar_id,
                    "idempotency_key": bundle.calendar_idempotency_key,
                },
            )
            or ""
        )
        status["calendar"] = "success"
    except Exception as exc:
        status["calendar"] = "failed"
        status["docs"] = "skipped"
        status["gmail"] = "skipped"
        raise BookingMcpExecutionError(stage="calendar", artifact_status=status, cause=str(exc))

    try:
        doc_reply = str(
            dispatch_mcp_tool(
                client,
                "docs_append_prebooking",
                {
                    "doc_id": bundle.doc_id,
                    "line": bundle.doc_line,
                    "idempotency_key": bundle.doc_idempotency_key,
                },
            )
            or ""
        )
        status["docs"] = "success"
    except Exception as exc:
        status["docs"] = "failed"
        status["gmail"] = "skipped"
        raise BookingMcpExecutionError(stage="docs", artifact_status=status, cause=str(exc))

    try:
        draft_id = str(
            dispatch_mcp_tool(
                client,
                "gmail_create_draft",
                {
                    "to": bundle.gmail_to,
                    "subject": bundle.gmail_subject,
                    "body_markdown": bundle.gmail_body,
                },
            )
            or ""
        )
        status["gmail"] = "success"
    except Exception as exc:
        status["gmail"] = "failed"
        raise BookingMcpExecutionError(stage="gmail", artifact_status=status, cause=str(exc))

    return BookingMcpResult(
        event_id=event_id,
        doc_reply=doc_reply,
        draft_id=draft_id,
    )


def _run_via_gemini_automatic_function_calling(client: McpOperations, bundle: BookingMcpBundle) -> BookingMcpResult:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool

    cal_args = {
        "title": bundle.calendar_title,
        "start_utc": bundle.start_utc,
        "end_utc": bundle.end_utc,
        "calendar_id": bundle.calendar_id,
        "idempotency_key": bundle.calendar_idempotency_key,
    }
    doc_args = {
        "doc_id": bundle.doc_id,
        "line": bundle.doc_line,
        "idempotency_key": bundle.doc_idempotency_key,
    }
    mail_args = {
        "to": bundle.gmail_to,
        "subject": bundle.gmail_subject,
        "body_markdown": bundle.gmail_body,
    }

    # Populated by AFC callables (canonical payloads only; model-supplied args are ignored).
    state: dict[str, str] = {}

    # Model may pass args; we always execute with orchestrator-built payloads (compliance).
    def calendar_create_hold(
        title: str = "",
        start_utc: str = "",
        end_utc: str = "",
        calendar_id: str = "",
        idempotency_key: str = "",
    ) -> str:
        _ = (title, start_utc, end_utc, calendar_id, idempotency_key)
        out = str(dispatch_mcp_tool(client, "calendar_create_hold", cal_args) or "")
        state["event_id"] = out
        return out

    def docs_append_prebooking(doc_id: str = "", line: str = "", idempotency_key: str = "") -> str:
        _ = (doc_id, line, idempotency_key)
        out = str(dispatch_mcp_tool(client, "docs_append_prebooking", doc_args) or "")
        state["doc_reply"] = out
        return out

    def gmail_create_draft(to: str = "", subject: str = "", body_markdown: str = "") -> str:
        _ = (to, subject, body_markdown)
        out = str(dispatch_mcp_tool(client, "gmail_create_draft", mail_args) or "")
        state["draft_id"] = out
        return out

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model_name = os.environ.get("NLU_MODEL", "gemini-2.0-flash")

    fds = [
        FunctionDeclaration.from_function(calendar_create_hold),
        FunctionDeclaration.from_function(docs_append_prebooking),
        FunctionDeclaration.from_function(gmail_create_draft),
    ]
    tool = Tool(function_declarations=fds)

    model = genai.GenerativeModel(
        model_name,
        tools=[tool],
        system_instruction=(
            "You complete advisor pre-bookings by calling Google MCP tools. "
            "After the user confirms, you MUST call these three tools in order: "
            "calendar_create_hold, docs_append_prebooking, gmail_create_draft. "
            "Use the parameter values given in the user message."
        ),
    )

    user_msg = (
        "Booking confirmed. Execute MCP tools with exactly these parameters:\n"
        f"calendar_create_hold: {cal_args}\n"
        f"docs_append_prebooking: {doc_args}\n"
        f"gmail_create_draft: {mail_args}"
    )

    chat = model.start_chat(enable_automatic_function_calling=True)
    chat.send_message(user_msg)

    if getattr(client, "write_attempts", 0) < 3:
        raise RuntimeError(
            "Gemini did not invoke all three MCP tools; enable function calling or check model/safety settings."
        )

    return BookingMcpResult(
        event_id=state.get("event_id", ""),
        doc_reply=state.get("doc_reply", ""),
        draft_id=state.get("draft_id", ""),
    )
