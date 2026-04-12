"""Streamlit presentation layer — calls backend API only."""

from __future__ import annotations

import os
from uuid import uuid4

import streamlit as st

from phase9.chat_client import ChatResponse, api_base_url, fetch_health, post_chat


def _apply_streamlit_secrets_to_env() -> None:
    """Streamlit Cloud exposes `st.secrets`; mirror CHAT_API_BASE_URL into the process env."""
    try:
        sec = st.secrets
        if "CHAT_API_BASE_URL" in sec:
            os.environ.setdefault("CHAT_API_BASE_URL", str(sec["CHAT_API_BASE_URL"]))
    except Exception:
        pass


def _new_session_id() -> str:
    return f"st-{uuid4().hex[:8]}"


def _ensure_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = _new_session_id()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "quick_replies" not in st.session_state:
        st.session_state.quick_replies = []
    if "intent_preview" not in st.session_state:
        st.session_state.intent_preview = []
    if "last_booking_summary" not in st.session_state:
        st.session_state.last_booking_summary = None


def _reset_chat() -> None:
    st.session_state.session_id = _new_session_id()
    st.session_state.messages = []
    st.session_state.quick_replies = []
    st.session_state.intent_preview = []
    st.session_state.last_booking_summary = None


def _append(role: str, text: str) -> None:
    st.session_state.messages.append({"role": role, "text": text})


def _render_booking_summary_card(summary: dict) -> None:
    if not summary or summary.get("kind") != "booking_confirmed":
        return
    with st.expander("Booking summary", expanded=True):
        st.markdown(summary.get("detail") or "")
        if summary.get("booking_code"):
            st.caption(f"Booking code: `{summary['booking_code']}`")
        if summary.get("slot"):
            st.caption(f"Slot: {summary['slot']}")
        cols = st.columns(2)
        if summary.get("calendar_event_id"):
            cols[0].code(str(summary["calendar_event_id"]), language=None)
            cols[0].caption("Calendar event id")
        if summary.get("gmail_draft_id"):
            cols[1].code(str(summary["gmail_draft_id"]), language=None)
            cols[1].caption("Gmail draft id")


def _apply_assistant_turn(resp: ChatResponse) -> None:
    for msg in resp.messages:
        _append("assistant", msg)

    st.session_state.quick_replies = resp.quick_replies
    st.session_state.intent_preview = resp.intent_preview
    st.session_state.last_booking_summary = resp.booking_summary


def send_user_text(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    _append("user", text)
    try:
        resp = post_chat(st.session_state.session_id, text)
    except Exception as exc:  # noqa: BLE001
        _append("assistant", f"Error: {exc}")
        return

    _apply_assistant_turn(resp)


def _render_messages() -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["text"])


def _render_actions() -> None:
    if st.session_state.intent_preview:
        st.markdown("### Quick start")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.intent_preview):
            label = item.get("label", "Option")
            if cols[i % 2].button(label, key=f"intent-{i}"):
                send_user_text(item.get("value", ""))
                st.rerun()

    if st.session_state.quick_replies:
        st.markdown("### Next step")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.quick_replies):
            label = item.get("label", "Option")
            action = item.get("action")
            if cols[i % 2].button(label, key=f"reply-{i}"):
                if action == "new_session":
                    _reset_chat()
                else:
                    send_user_text(item.get("value", ""))
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="AI Appointment Scheduler",
        page_icon="📅",
        layout="centered",
    )
    _apply_streamlit_secrets_to_env()
    _ensure_state()

    st.title("AI Appointment Scheduler")
    st.caption(f"Session: `{st.session_state.session_id}`")
    st.caption(f"API: `{api_base_url()}`")

    with st.sidebar:
        st.subheader("Backend status")
        ok, detail = fetch_health()
        if ok:
            st.success("API health: OK")
        else:
            st.warning("API health: unreachable or error")
        st.caption(detail[:500] + ("…" if len(detail) > 500 else ""))

    if st.button("New conversation"):
        _reset_chat()
        st.rerun()

    if not st.session_state.messages:
        send_user_text("hello")

    _render_messages()

    summary = st.session_state.get("last_booking_summary")
    if summary and summary.get("kind") == "booking_confirmed":
        _render_booking_summary_card(summary)

    _render_actions()

    user_text = st.chat_input("Type your message")
    if user_text:
        send_user_text(user_text)
        st.rerun()
