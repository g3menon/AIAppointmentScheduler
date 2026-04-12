"""Unit tests — Phase 5 Web UI hints (quick replies, booking summary)."""

from phase1.api.chat.ui_hints import build_booking_summary, build_quick_replies
from phase1.domain.models import TimeSlot
from phase1.session.orchestrator import AgentTurn
from phase1.session.session_context import SessionContext
from phase1.session.state import State


def test_quick_replies_disclaimer_shows_ok() -> None:
    s = SessionContext(session_id="t1", state=State.DISCLAIMER_AWAIT_ACK)
    qr = build_quick_replies(s)
    assert any(r["value"] == "ok" for r in qr)


def test_quick_replies_book_confirm_yes_no() -> None:
    s = SessionContext(session_id="t2", state=State.BOOK_CONFIRM)
    qr = build_quick_replies(s)
    values = {r["value"] for r in qr}
    assert "yes" in values and "no" in values


def test_booking_summary_extracts_calendar_id() -> None:
    s = SessionContext(session_id="t3", state=State.CLOSE, booking_code="AB-C123")
    turn = AgentTurn(
        messages=["done"],
        side_effects=[{"calendar_event_id": "evt-1", "gmail_draft_id": "dr-9"}],
    )
    summary = build_booking_summary(s, turn)
    assert summary is not None
    assert summary["calendar_event_id"] == "evt-1"
    assert summary["no_further_steps_in_chat"] is True


def test_quick_replies_slots_use_numeric_choice() -> None:
    s = SessionContext(
        session_id="t4",
        state=State.BOOK_OFFER_SLOTS,
        offered_slots=["Slot A", "Slot B"],
        offered_slot_choices=[
            TimeSlot("2026-04-10T09:30:00Z", "2026-04-10T10:00:00Z", "Slot A"),
            TimeSlot("2026-04-10T11:00:00Z", "2026-04-10T11:30:00Z", "Slot B"),
        ],
    )
    qr = build_quick_replies(s)
    assert {r["value"] for r in qr} == {"1", "2"}
