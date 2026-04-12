from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from phase4.observability.audit import clear_audit_records, get_audit_records
from phase4.observability.logger import clear_logged_events, get_logged_events
from src.integrations.google_mcp.settings import GoogleMcpSettings


class DocsFailingMcpClient:
    def __init__(self) -> None:
        self.write_attempts = 0
        self.settings = GoogleMcpSettings(
            calendar_id="primary",
            prebooking_doc_id="doc-1",
            advisor_email_to="advisor@example.com",
            idempotency_namespace="booking",
            auth_mode="oauth",
        )

    def create_calendar_hold(
        self,
        title: str,
        start_utc: str,
        end_utc: str,
        calendar_id: str,
        idempotency_key: str,
    ) -> str:
        self.write_attempts += 1
        return "event-ok"

    def append_prebooking_log(self, doc_id: str, line: str, idempotency_key: str) -> str:
        self.write_attempts += 1
        raise RuntimeError("docs service unavailable")

    def create_gmail_draft(self, to: str, subject: str, body_markdown: str) -> str:
        self.write_attempts += 1
        return "draft-should-not-happen"


def _run(orch: Orchestrator, session: SessionContext, *messages: str):
    turn = None
    for msg in messages:
        turn = orch.handle(msg, session)
    return turn


def test_partial_failure_triggers_safe_fallback_and_audit() -> None:
    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=DocsFailingMcpClient())
    session = SessionContext(session_id="phase4-partial")

    turn = _run(orch, session, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes")
    assert turn is not None
    assert session.state == State.CLOSE
    assert session.booking_code is None
    assert any("could not complete" in msg.lower() or "try again" in msg.lower() for msg in turn.messages)

    records = get_audit_records()
    assert records, "expected partial failure audit record"
    status = records[-1].status
    assert status["calendar_status"] == "success"
    assert status["docs_status"] == "failed"
    assert status["gmail_status"] == "skipped"

    logs = get_logged_events()
    assert logs
    assert any(e.payload["error_type"] == "integration" for e in logs)
