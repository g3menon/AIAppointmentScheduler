"""Unit tests — Phase 9 HTTP client (no Streamlit)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from phase9.chat_client import ChatResponse, fetch_health, post_chat


def test_chat_response_from_api_json_parity_fields() -> None:
    raw = {
        "messages": ["Hello", "How can I help?"],
        "quick_replies": [{"label": "OK", "value": "ok"}],
        "intent_preview": [{"label": "Book", "value": "book"}],
        "booking_summary": None,
        "state": "DISCLAIMER_AWAIT_ACK",
        "session": {"session_id": "s1", "state": "DISCLAIMER_AWAIT_ACK"},
    }
    r = ChatResponse.from_api_json(raw)
    assert r.messages == ["Hello", "How can I help?"]
    assert r.quick_replies[0]["label"] == "OK"
    assert r.intent_preview[0]["value"] == "book"
    assert r.booking_summary is None
    assert r.state == "DISCLAIMER_AWAIT_ACK"
    assert r.session is not None
    assert r.session["session_id"] == "s1"


def test_chat_response_missing_session() -> None:
    r = ChatResponse.from_api_json({"messages": ["a"], "state": "GREET"})
    assert r.session is None


def test_post_chat_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "messages": ["m1"],
        "quick_replies": [],
        "intent_preview": [],
        "booking_summary": None,
        "state": "CLOSE",
        "session": {"session_id": "x"},
    }
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")

    with patch("phase9.chat_client.urllib.request.urlopen", return_value=mock_resp):
        out = post_chat("sid", "hello", base_url="http://test", timeout_sec=5.0)

    assert out.messages == ["m1"]
    assert out.state == "CLOSE"


def test_post_chat_urlerror() -> None:
    import urllib.error

    with patch(
        "phase9.chat_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("boom"),
    ):
        with pytest.raises(RuntimeError, match="unreachable"):
            post_chat("s", "hi", base_url="http://missing.local")


def test_fetch_health_ok() -> None:
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"status":"ok"}'

    with patch("phase9.chat_client.urllib.request.urlopen", return_value=mock_resp):
        ok, detail = fetch_health(base_url="http://h", timeout_sec=1.0)

    assert ok is True
    assert "ok" in detail
