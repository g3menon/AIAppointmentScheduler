"""Integration tests — PII audit gate.

Validates that after a full booking flow (including MCP execution),
no raw PII appears in:
1. Logged events (orchestrator turn logs)
2. Audit records (artifact status records)
3. Messages returned to the user (should not echo PII back)

Also validates that the existing redaction and sanitization pipelines
are actively working end-to-end.
"""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from phase4.observability.audit import clear_audit_records, get_audit_records
from phase4.observability.logger import clear_logged_events, get_logged_events
from phase8.observability_gate import (
    assert_audit_keys_clean,
    assert_payload_pii_free,
    scan_for_pii,
)


def _run(orch: Orchestrator, session: SessionContext, *messages: str):
    turns = []
    for msg in messages:
        turn = orch.handle(msg, session)
        turns.append(turn)
    return turns


def test_booking_flow_logs_are_pii_free() -> None:
    """Full booking flow: all logged events must have redacted payloads."""
    clear_logged_events()
    clear_audit_records()

    orch = Orchestrator()
    session = SessionContext(session_id="pii-gate-book")

    _run(
        orch, session,
        "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes",
    )

    logs = get_logged_events()
    assert logs, "Expected logged events after booking flow"

    for event in logs:
        assert_payload_pii_free(
            event.payload,
            context=f"log event '{event.event_name}': ",
        )


def test_pii_in_user_text_is_redacted_in_logs() -> None:
    """If a user accidentally sends PII, logs must redact it."""
    clear_logged_events()
    orch = Orchestrator()
    session = SessionContext(session_id="pii-gate-redact")

    _run(orch, session, "hi")

    _run(orch, session, "my email is john@example.com and my phone is 9876543210")

    logs = get_logged_events()
    for event in logs:
        for key, value in event.payload.items():
            if isinstance(value, str):
                assert "john@example.com" not in value, (
                    f"Raw email found in log payload[{key!r}]"
                )
                assert "9876543210" not in value, (
                    f"Raw phone found in log payload[{key!r}]"
                )


def test_audit_records_exclude_raw_user_text() -> None:
    """Audit records must not contain forbidden raw-text keys."""
    clear_audit_records()

    from phase4.observability.audit import record_artifact_status

    record_artifact_status("pii-gate-audit", {
        "calendar_status": "success",
        "docs_status": "success",
        "gmail_status": "success",
        "booking_code": "AB-123",
        "raw_user_text": "my email is john@example.com",
        "transcript": "secret conversation",
        "email": "john@example.com",
    })

    records = get_audit_records()
    assert records
    for record in records:
        assert_audit_keys_clean(record.status)
        assert_payload_pii_free(
            record.status,
            context=f"audit record session={record.session_id}: ",
        )


def test_partial_failure_audit_is_pii_free() -> None:
    """Even on MCP failure, audit records must be PII-safe."""
    from src.integrations.google_mcp.settings import GoogleMcpSettings

    class FailingClient:
        def __init__(self):
            self.write_attempts = 0
            self.settings = GoogleMcpSettings(
                calendar_id="primary",
                prebooking_doc_id="doc-1",
                advisor_email_to="advisor@example.com",
                idempotency_namespace="test",
                auth_mode="oauth",
            )

        def create_calendar_hold(self, title, start_utc, end_utc, calendar_id, idempotency_key):
            self.write_attempts += 1
            return "event-ok"

        def delete_calendar_hold(self, event_id, calendar_id):
            self.write_attempts += 1
            return event_id

        def append_prebooking_log(self, doc_id, line, idempotency_key):
            self.write_attempts += 1
            raise RuntimeError("docs unavailable")

        def create_gmail_draft(self, to, subject, body_markdown):
            self.write_attempts += 1
            return "draft-ok"

    clear_audit_records()
    clear_logged_events()
    orch = Orchestrator(mcp_client=FailingClient())
    session = SessionContext(session_id="pii-gate-fail")

    _run(
        orch, session,
        "hi", "ok", "book appointment", "KYC", "tomorrow", "1", "yes",
    )

    records = get_audit_records()
    assert records, "Expected audit record on partial failure"
    for record in records:
        assert_audit_keys_clean(record.status)
        for key, value in record.status.items():
            if isinstance(value, str):
                pii_found = scan_for_pii(value)
                assert not pii_found, (
                    f"PII {pii_found} found in audit status[{key!r}]"
                )


def test_pii_rejection_does_not_leak_pii_to_user() -> None:
    """When PII is detected in user input, the response must not echo it back."""
    orch = Orchestrator()
    session = SessionContext(session_id="pii-gate-echo")

    _run(orch, session, "hi")

    turns = _run(orch, session, "my PAN is ABCDE1234F")

    for turn in turns:
        for msg in turn.messages:
            assert "ABCDE1234F" not in msg, "PII echoed back to user"


def test_log_event_requires_all_fields() -> None:
    """Verify that incomplete log payloads are rejected."""
    from phase4.observability.logger import log_event

    try:
        log_event("incomplete", {"session_id": "s1"})
        raise AssertionError("Expected ValueError for missing fields")
    except ValueError as exc:
        assert "Missing required log fields" in str(exc)


def test_booking_flow_no_pii_in_messages() -> None:
    """User-facing messages during a normal booking must not contain PII patterns."""
    orch = Orchestrator()
    session = SessionContext(session_id="pii-gate-msgs")

    turns = _run(
        orch, session,
        "hi", "ok", "book appointment", "KYC", "tomorrow", "1", "yes",
    )

    for turn in turns:
        for msg in turn.messages:
            pii_found = scan_for_pii(msg)
            assert not pii_found, (
                f"PII {pii_found} found in user-facing message: {msg[:100]}"
            )
