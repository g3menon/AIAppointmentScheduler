"""Smoke tests for the Phase 5 HTTP chat API using FastAPI TestClient."""

from fastapi.testclient import TestClient

from phase5.http.chat_app import create_app

client = TestClient(create_app())


def test_health_returns_ok() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_message_returns_non_empty_messages() -> None:
    resp = client.post(
        "/api/chat/message",
        json={"session_id": "smoke-test", "text": "hello"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "messages" in body
    assert len(body["messages"]) > 0
    assert "state" in body
    assert "quick_replies" in body
    assert isinstance(body["quick_replies"], list)
    assert "intent_preview" in body
    assert "booking_summary" in body


def test_chat_message_default_session_id() -> None:
    resp = client.post("/api/chat/message", json={"text": "hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["session_id"] == "web-demo"


def test_chat_message_session_persists_across_turns() -> None:
    sid = "persist-test"
    r1 = client.post("/api/chat/message", json={"session_id": sid, "text": "hello"})
    assert r1.status_code == 200

    r2 = client.post("/api/chat/message", json={"session_id": sid, "text": "ok"})
    assert r2.status_code == 200
    assert r2.json()["session"]["session_id"] == sid
