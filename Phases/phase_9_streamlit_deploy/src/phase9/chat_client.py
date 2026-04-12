"""HTTP client for the Phase 5 chat API — no domain or MCP logic."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_API_BASE = "http://127.0.0.1:8000"


def api_base_url() -> str:
    return os.getenv("CHAT_API_BASE_URL", DEFAULT_API_BASE).rstrip("/")


@dataclass(frozen=True)
class ChatResponse:
    """Subset of POST /api/chat/message JSON used by the Streamlit UI."""

    messages: list[str]
    quick_replies: list[dict[str, Any]]
    intent_preview: list[dict[str, Any]]
    booking_summary: dict[str, Any] | None
    state: str
    session: dict[str, Any] | None

    @classmethod
    def from_api_json(cls, raw: dict[str, Any]) -> ChatResponse:
        return cls(
            messages=list(raw.get("messages") or []),
            quick_replies=list(raw.get("quick_replies") or []),
            intent_preview=list(raw.get("intent_preview") or []),
            booking_summary=raw.get("booking_summary"),
            state=str(raw.get("state") or ""),
            session=raw.get("session") if isinstance(raw.get("session"), dict) else None,
        )


def post_chat(
    session_id: str,
    text: str,
    *,
    base_url: str | None = None,
    timeout_sec: float = 30.0,
) -> ChatResponse:
    base = (base_url or api_base_url()).rstrip("/")
    payload = {"session_id": session_id, "text": text}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base}/api/chat/message",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Chat API HTTP {exc.code} at {base}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Chat API unreachable at {base}: {exc}") from exc

    if not isinstance(raw, dict):
        raise RuntimeError("Chat API returned non-object JSON")
    return ChatResponse.from_api_json(raw)


def fetch_health(
    *,
    base_url: str | None = None,
    timeout_sec: float = 5.0,
) -> tuple[bool, str]:
    """GET /api/health — returns (ok, detail)."""
    base = (base_url or api_base_url()).rstrip("/")
    req = urllib.request.Request(
        url=f"{base}/api/health",
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ok = resp.status == 200 and data.get("status") == "ok"
        return ok, json.dumps(data)
    except Exception as exc:  # noqa: BLE001 — surface any failure to UI
        return False, str(exc)
