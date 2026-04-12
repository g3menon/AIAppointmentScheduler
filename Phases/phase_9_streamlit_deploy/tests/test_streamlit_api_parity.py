"""Parity checks — FastAPI JSON matches ``ChatResponse`` expectations."""

from __future__ import annotations

from fastapi.testclient import TestClient

from phase9.chat_client import ChatResponse
from src.api.http.chat_app import app


def test_hello_roundtrip_matches_chat_response_shape() -> None:
    client = TestClient(app)
    res = client.post("/api/chat/message", json={"session_id": "p9-parity", "text": "hello"})
    assert res.status_code == 200
    data = res.json()
    parsed = ChatResponse.from_api_json(data)
    assert parsed.messages
    assert isinstance(parsed.quick_replies, list)
    assert isinstance(parsed.intent_preview, list)
    assert parsed.state
    assert "session" in data


def test_smoke_booking_flow_messages_and_state() -> None:
    """New session → disclaimer → book → topic → time → slot → confirm → close."""
    client = TestClient(app)
    sid = "p9-smoke-book"

    def post(text: str) -> ChatResponse:
        r = client.post("/api/chat/message", json={"session_id": sid, "text": text})
        assert r.status_code == 200
        return ChatResponse.from_api_json(r.json())

    post("hello")
    post("ok")
    post("book appointment")
    post("KYC")
    r5 = post("tomorrow afternoon")
    assert any("IST" in m for m in r5.messages)
    post("1")
    r7 = post("yes")
    assert any("confirmed" in m.lower() for m in r7.messages)
    assert r7.state == "CLOSE"


def test_smoke_reschedule_and_cancel_paths() -> None:
    client = TestClient(app)

    r = client.post(
        "/api/chat/message",
        json={"session_id": "p9-r", "text": "hello"},
    )
    assert r.status_code == 200
    client.post("/api/chat/message", json={"session_id": "p9-r", "text": "ok"})
    r2 = client.post(
        "/api/chat/message",
        json={"session_id": "p9-r", "text": "reschedule my appointment"},
    )
    data2 = r2.json()
    assert data2.get("state")

    client.post("/api/chat/message", json={"session_id": "p9-c", "text": "hello"})
    client.post("/api/chat/message", json={"session_id": "p9-c", "text": "ok"})
    r3 = client.post(
        "/api/chat/message",
        json={"session_id": "p9-c", "text": "cancel my booking"},
    )
    assert r3.status_code == 200
    assert r3.json().get("state")


def test_degraded_mode_message_shape_from_partial_mcp_failure() -> None:
    """Orchestrator returns safe fallback text; Streamlit client only needs messages + state."""
    from phase1.api.chat.routes import set_orchestrator_for_tests
    from phase1.session.orchestrator import Orchestrator
    from phase1.session.session_context import SessionContext
    from phase1.session.state import State
    from phase4.observability.audit import clear_audit_records
    from src.integrations.google_mcp.settings import GoogleMcpSettings

    class DocsFail:
        def __init__(self) -> None:
            self.write_attempts = 0
            self.settings = GoogleMcpSettings(
                calendar_id="primary",
                prebooking_doc_id="doc-1",
                advisor_email_to="a@example.com",
                idempotency_namespace="p9",
                auth_mode="oauth",
            )

        def create_calendar_hold(self, *a, **k):
            self.write_attempts += 1
            return "ev"

        def delete_calendar_hold(self, *a, **k):
            self.write_attempts += 1
            return "x"

        def append_prebooking_log(self, *a, **k):
            self.write_attempts += 1
            raise RuntimeError("docs down")

        def create_gmail_draft(self, *a, **k):
            self.write_attempts += 1
            return "d"

    clear_audit_records()
    orch = Orchestrator(mcp_client=DocsFail())
    set_orchestrator_for_tests(orch)
    try:
        client = TestClient(app)
        sid = "p9-degraded"
        for text in ("hello", "ok", "book appointment", "KYC", "tomorrow", "1", "yes"):
            res = client.post("/api/chat/message", json={"session_id": sid, "text": text})
            assert res.status_code == 200
        data = res.json()
        cr = ChatResponse.from_api_json(data)
        assert cr.state == State.CLOSE.value or cr.state == "CLOSE"
        assert any(
            "could not complete" in m.lower() or "try again" in m.lower()
            for m in cr.messages
        )
    finally:
        set_orchestrator_for_tests(None)
