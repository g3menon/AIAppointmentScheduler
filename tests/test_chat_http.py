"""Smoke tests for Phase 5 HTTP chat bridge."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.http.chat_app import app


def test_api_health() -> None:
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_api_chat_message_returns_assistant_text() -> None:
    client = TestClient(app)
    res = client.post("/api/chat/message", json={"session_id": "http-smoke", "text": "hello"})
    assert res.status_code == 200
    data = res.json()
    assert "messages" in data and isinstance(data["messages"], list)
    assert len(data["messages"]) >= 1
    assert data.get("state")
    assert "session" in data and isinstance(data["session"], dict)
