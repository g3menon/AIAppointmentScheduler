from phase4.observability.audit import clear_audit_records, get_audit_records, record_artifact_status
from phase4.observability.logger import clear_logged_events, get_logged_events, log_event


def test_log_event_enforces_required_fields() -> None:
    clear_logged_events()
    try:
        log_event("turn", {"session_id": "s1"})
        raise AssertionError("Expected required field validation failure")
    except ValueError as exc:
        assert "Missing required log fields" in str(exc)


def test_log_event_redacts_sensitive_strings() -> None:
    clear_logged_events()
    log_event(
        "turn",
        {
            "session_id": "s1",
            "stage": "book_confirm",
            "intent": "book_new",
            "booking_code": "AB-C123",
            "error_type": "none",
            "latency_ms": 10,
            "note": "contact me at me@example.com or 9876543210",
        },
    )
    event = get_logged_events()[-1]
    note = str(event.payload["note"])
    assert "[REDACTED_EMAIL]" in note
    assert "[REDACTED_PHONE]" in note
    assert "me@example.com" not in note


def test_audit_strips_raw_user_fields() -> None:
    clear_audit_records()
    record_artifact_status(
        "s1",
        {
            "calendar_status": "success",
            "doc_status": "failed",
            "raw_user_text": "my email is me@example.com",
            "transcript": "secret",
        },
    )
    record = get_audit_records()[-1]
    assert "raw_user_text" not in record.status
    assert "transcript" not in record.status
    assert record.status["calendar_status"] == "success"
