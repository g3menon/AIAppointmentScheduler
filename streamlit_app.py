from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from uuid import uuid4

import streamlit as st


DEFAULT_API_BASE = "http://127.0.0.1:8000"


@dataclass
class ChatResponse:
    messages: list[str]
    quick_replies: list[dict]
    intent_preview: list[dict]
    booking_summary: dict | None
    state: str


def _api_base() -> str:
    return os.getenv("CHAT_API_BASE_URL", DEFAULT_API_BASE).rstrip("/")


def _new_session_id() -> str:
    return f"st-{uuid4().hex[:8]}"


def _post_chat(session_id: str, text: str) -> ChatResponse:
    payload = {"session_id": session_id, "text": text}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{_api_base()}/api/chat/message",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Chat API unreachable at {_api_base()}: {exc}") from exc

    return ChatResponse(
        messages=list(raw.get("messages") or []),
        quick_replies=list(raw.get("quick_replies") or []),
        intent_preview=list(raw.get("intent_preview") or []),
        booking_summary=raw.get("booking_summary"),
        state=str(raw.get("state") or ""),
    )


def _ensure_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = _new_session_id()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "quick_replies" not in st.session_state:
        st.session_state.quick_replies = []
    if "intent_preview" not in st.session_state:
        st.session_state.intent_preview = []


def _reset_chat() -> None:
    st.session_state.session_id = _new_session_id()
    st.session_state.messages = []
    st.session_state.quick_replies = []
    st.session_state.intent_preview = []


def _append(role: str, text: str) -> None:
    st.session_state.messages.append({"role": role, "text": text})


def _send_user_text(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    _append("user", text)
    try:
        resp = _post_chat(st.session_state.session_id, text)
    except Exception as exc:  # noqa: BLE001
        _append("assistant", f"Error: {exc}")
        return

    for msg in resp.messages:
        _append("assistant", msg)

    st.session_state.quick_replies = resp.quick_replies
    st.session_state.intent_preview = resp.intent_preview

    if resp.booking_summary and resp.booking_summary.get("kind") == "booking_confirmed":
        slot = resp.booking_summary.get("slot", "")
        code = resp.booking_summary.get("booking_code", "")
        _append(
            "assistant",
            f"Booking complete. Slot: {slot or 'N/A'} | Code: {code or 'N/A'}",
        )


def _render_messages() -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["text"])


def _render_actions() -> None:
    if st.session_state.intent_preview:
        st.markdown("### Quick Start")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.intent_preview):
            if cols[i % 2].button(item.get("label", "Option"), key=f"intent-{i}"):
                _send_user_text(item.get("value", ""))
                st.rerun()

    if st.session_state.quick_replies:
        st.markdown("### Next Step")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.quick_replies):
            label = item.get("label", "Option")
            action = item.get("action")
            if cols[i % 2].button(label, key=f"reply-{i}"):
                if action == "new_session":
                    _reset_chat()
                else:
                    _send_user_text(item.get("value", ""))
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="AI Appointment Scheduler", page_icon="📅", layout="centered")
    _ensure_state()

    st.title("AI Appointment Scheduler")
    st.caption(f"Session: `{st.session_state.session_id}`")
    st.caption(f"API: `{_api_base()}`")

    if st.button("New Conversation"):
        _reset_chat()
        st.rerun()

    if not st.session_state.messages:
        _send_user_text("hello")

    _render_messages()
    _render_actions()

    user_text = st.chat_input("Type your message")
    if user_text:
        _send_user_text(user_text)
        st.rerun()


if __name__ == "__main__":
    main()
