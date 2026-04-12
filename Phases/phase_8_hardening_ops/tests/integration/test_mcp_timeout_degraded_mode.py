"""Integration tests — MCP timeout and degraded mode behavior.

Validates that:
1. Timeout at each MCP stage produces user-safe fallback messages.
2. No booking success is ever claimed on failure.
3. Audit records correctly track per-service status.
4. Bounded retries do not loop infinitely.
"""

from phase1.session.orchestrator import AgentTurn, Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from phase4.observability.audit import clear_audit_records, get_audit_records
from phase4.observability.logger import clear_logged_events, get_logged_events
from src.integrations.google_mcp.settings import GoogleMcpSettings

_TEST_SETTINGS = GoogleMcpSettings(
    calendar_id="primary",
    prebooking_doc_id="doc-1",
    advisor_email_to="advisor@example.com",
    idempotency_namespace="test",
    auth_mode="oauth",
)


class CalendarTimeoutMcpClient:
    """Simulates a timeout at the Calendar stage."""

    def __init__(self) -> None:
        self.write_attempts = 0
        self.settings = _TEST_SETTINGS

    def create_calendar_hold(self, title, start_utc, end_utc, calendar_id, idempotency_key):
        self.write_attempts += 1
        raise TimeoutError("Calendar service timed out")

    def delete_calendar_hold(self, event_id, calendar_id):
        self.write_attempts += 1
        return event_id

    def append_prebooking_log(self, doc_id, line, idempotency_key):
        self.write_attempts += 1
        return "doc_ok"

    def create_gmail_draft(self, to, subject, body_markdown):
        self.write_attempts += 1
        return "draft_ok"


class DocsTimeoutMcpClient:
    """Simulates success at Calendar but timeout at Docs."""

    def __init__(self) -> None:
        self.write_attempts = 0
        self.settings = _TEST_SETTINGS

    def create_calendar_hold(self, title, start_utc, end_utc, calendar_id, idempotency_key):
        self.write_attempts += 1
        return "event-ok"

    def delete_calendar_hold(self, event_id, calendar_id):
        self.write_attempts += 1
        return event_id

    def append_prebooking_log(self, doc_id, line, idempotency_key):
        self.write_attempts += 1
        raise TimeoutError("Docs service timed out")

    def create_gmail_draft(self, to, subject, body_markdown):
        self.write_attempts += 1
        return "draft_ok"


class GmailTimeoutMcpClient:
    """Simulates success at Calendar+Docs but timeout at Gmail."""

    def __init__(self) -> None:
        self.write_attempts = 0
        self.settings = _TEST_SETTINGS

    def create_calendar_hold(self, title, start_utc, end_utc, calendar_id, idempotency_key):
        self.write_attempts += 1
        return "event-ok"

    def delete_calendar_hold(self, event_id, calendar_id):
        self.write_attempts += 1
        return event_id

    def append_prebooking_log(self, doc_id, line, idempotency_key):
        self.write_attempts += 1
        return "doc_ok"

    def create_gmail_draft(self, to, subject, body_markdown):
        self.write_attempts += 1
        raise TimeoutError("Gmail service timed out")


class FullOutageMcpClient:
    """Simulates complete MCP outage — all services throw."""

    def __init__(self) -> None:
        self.write_attempts = 0
        self.settings = _TEST_SETTINGS

    def create_calendar_hold(self, title, start_utc, end_utc, calendar_id, idempotency_key):
        self.write_attempts += 1
        raise ConnectionError("All services unreachable")

    def delete_calendar_hold(self, event_id, calendar_id):
        self.write_attempts += 1
        raise ConnectionError("All services unreachable")

    def append_prebooking_log(self, doc_id, line, idempotency_key):
        self.write_attempts += 1
        raise ConnectionError("All services unreachable")

    def create_gmail_draft(self, to, subject, body_markdown):
        self.write_attempts += 1
        raise ConnectionError("All services unreachable")


def _booking_flow(orch: Orchestrator, session: SessionContext) -> AgentTurn:
    """Drive a session through the full booking flow to the MCP execution point."""
    turn = None
    for msg in ("hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes"):
        turn = orch.handle(msg, session)
    assert turn is not None
    return turn


def test_calendar_timeout_produces_safe_fallback() -> None:
    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=CalendarTimeoutMcpClient())
    session = SessionContext(session_id="p8-cal-timeout")

    turn = _booking_flow(orch, session)

    assert session.state == State.CLOSE
    assert session.booking_code is None
    assert any(
        "could not complete" in m.lower() or "try again" in m.lower()
        for m in turn.messages
    ), f"Expected degraded message, got: {turn.messages}"
    assert not any("confirmed" in m.lower() for m in turn.messages)

    records = get_audit_records()
    assert records
    status = records[-1].status
    assert status["calendar_status"] == "failed"
    assert status["docs_status"] == "skipped"
    assert status["gmail_status"] == "skipped"


def test_docs_timeout_produces_safe_fallback() -> None:
    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=DocsTimeoutMcpClient())
    session = SessionContext(session_id="p8-docs-timeout")

    turn = _booking_flow(orch, session)

    assert session.state == State.CLOSE
    assert session.booking_code is None
    assert any(
        "could not complete" in m.lower() or "try again" in m.lower()
        for m in turn.messages
    )
    assert not any("confirmed" in m.lower() for m in turn.messages)

    records = get_audit_records()
    assert records
    status = records[-1].status
    assert status["calendar_status"] == "success"
    assert status["docs_status"] == "failed"
    assert status["gmail_status"] == "skipped"


def test_gmail_timeout_produces_safe_fallback() -> None:
    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=GmailTimeoutMcpClient())
    session = SessionContext(session_id="p8-gmail-timeout")

    turn = _booking_flow(orch, session)

    assert session.state == State.CLOSE
    assert session.booking_code is None
    assert any(
        "could not complete" in m.lower() or "try again" in m.lower()
        for m in turn.messages
    )

    records = get_audit_records()
    assert records
    status = records[-1].status
    assert status["calendar_status"] == "success"
    assert status["docs_status"] == "success"
    assert status["gmail_status"] == "failed"


def test_full_outage_produces_safe_fallback() -> None:
    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=FullOutageMcpClient())
    session = SessionContext(session_id="p8-full-outage")

    turn = _booking_flow(orch, session)

    assert session.state == State.CLOSE
    assert session.booking_code is None
    assert not any("confirmed" in m.lower() for m in turn.messages)


def test_degraded_mode_logs_error_type() -> None:
    clear_logged_events()
    orch = Orchestrator(mcp_client=CalendarTimeoutMcpClient())
    session = SessionContext(session_id="p8-log-check")

    _booking_flow(orch, session)

    logs = get_logged_events()
    assert logs
    error_events = [e for e in logs if e.payload.get("error_type") == "integration"]
    assert error_events, "Expected at least one log event with error_type='integration'"


def test_bounded_retries_do_not_loop() -> None:
    """Verify that the MCP client's write_attempts are bounded (max 3 retries per op)."""
    client = CalendarTimeoutMcpClient()
    orch = Orchestrator(mcp_client=client)
    session = SessionContext(session_id="p8-retry-bound")

    _booking_flow(orch, session)

    assert client.write_attempts <= 3, (
        f"Expected at most 3 attempts (bounded retry), got {client.write_attempts}"
    )


def test_turn_limit_closes_session() -> None:
    """Verify that exceeding MAX_TURN_COUNT closes the session gracefully."""
    from phase8.runtime_controls import MAX_TURN_COUNT

    orch = Orchestrator()
    session = SessionContext(session_id="p8-turn-limit")
    session.turn_count = MAX_TURN_COUNT

    turn = orch.handle("hello", session)

    assert session.state == State.CLOSE
    assert any("turn limit" in m.lower() or "new session" in m.lower() for m in turn.messages)


def test_oversized_request_rejected() -> None:
    """Verify that an oversized message is rejected without processing."""
    orch = Orchestrator()
    session = SessionContext(session_id="p8-oversize")

    turn = orch.handle("x" * 20_000, session)

    assert any("too long" in m.lower() for m in turn.messages)
    assert session.state == State.GREET  # state unchanged
