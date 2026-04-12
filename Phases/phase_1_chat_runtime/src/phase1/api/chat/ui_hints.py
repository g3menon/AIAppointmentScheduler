"""UI hints for Phase 5 Web Chat (quick replies, previews, booking summary).

Presentation-only: does not change orchestration; values must match what
``Orchestrator.handle`` expects from user text."""

from __future__ import annotations

from typing import Any

from phase1.domain.models import Topic
from phase1.session.orchestrator import AgentTurn
from phase1.session.session_context import SessionContext
from phase1.session.state import State

INTENT_CHIPS: list[tuple[str, str]] = [
    ("Book a new appointment", "book appointment"),
    ("Reschedule", "reschedule my appointment"),
    ("Cancel", "cancel my booking"),
    ("What to prepare", "what should I prepare"),
    ("Check availability", "check availability"),
]

TOPIC_CHIPS: list[tuple[str, str]] = [
    ("KYC / Onboarding", Topic.KYC_ONBOARDING.value),
    ("SIP / Mandates", Topic.SIP_MANDATES.value),
    ("Statements / Tax Docs", Topic.STATEMENTS_TAX_DOCS.value),
    ("Withdrawals & Timelines", Topic.WITHDRAWALS_TIMELINES.value),
    ("Account Changes / Nominee", Topic.ACCOUNT_CHANGES_NOMINEE.value),
]

TIME_CHIPS: list[tuple[str, str]] = [
    ("Tomorrow morning", "tomorrow morning"),
    ("Tomorrow afternoon", "tomorrow afternoon"),
    ("Next week", "next week"),
]


def build_intent_preview(_session: SessionContext) -> list[dict[str, str]]:
    """Shown at session start so users see main actions before typing (after bootstrap)."""
    return [{"label": label, "value": value} for label, value in INTENT_CHIPS]


def build_quick_replies(session: SessionContext) -> list[dict[str, Any]]:
    """Actionable chips for the current state (single POST per click)."""
    st = session.state

    if st == State.DISCLAIMER_AWAIT_ACK:
        return [{"label": "OK — I understand", "value": "ok"}]

    if st == State.INTENT_ROUTING:
        return [{"label": label, "value": value} for label, value in INTENT_CHIPS]

    if st == State.BOOK_TOPIC:
        return [{"label": label, "value": value} for label, value in TOPIC_CHIPS]

    if st == State.BOOK_TIME_PREFERENCE:
        return [{"label": label, "value": value} for label, value in TIME_CHIPS]

    if st in (State.BOOK_OFFER_SLOTS, State.RESCHEDULE_OFFER_SLOTS) and len(session.offered_slots) >= 2:
        return [
            {"label": f"1 · {session.offered_slots[0]}", "value": "1"},
            {"label": f"2 · {session.offered_slots[1]}", "value": "2"},
        ]

    if st in (State.BOOK_CONFIRM, State.RESCHEDULE_CONFIRM):
        return [
            {"label": "Yes, confirm", "value": "yes"},
            {"label": "No, pick another slot", "value": "no"},
        ]

    if st == State.CANCEL_CONFIRM:
        return [
            {"label": "Yes, cancel", "value": "yes"},
            {"label": "No, keep booking", "value": "no"},
        ]

    if st == State.CLOSE:
        return [{"label": "New conversation", "value": "__new_session__", "action": "new_session"}]

    return []


def build_booking_summary(session: SessionContext, turn: AgentTurn) -> dict | None:
    """Structured completion payload for rich UI (copy event id, no-further-steps copy)."""
    if session.state != State.CLOSE:
        return None

    for fx in turn.side_effects:
        event_id = fx.get("calendar_event_id")
        if not event_id:
            continue
        slot_label = session.selected_slot or ""
        return {
            "kind": "booking_confirmed",
            "no_further_steps_in_chat": True,
            "detail":
                f"Appointment: {slot_label}. "
                "Review your Calendar event, Docs log line, "
                "and Gmail draft in Google — nothing else is required here."
                if slot_label else
                "You are done in this chat. Review your Calendar event, Docs log line, "
                "and Gmail draft in Google — nothing else is required here.",
            "booking_code": session.booking_code,
            "slot": slot_label,
            "calendar_event_id": str(event_id),
            "gmail_draft_id": str(fx.get("gmail_draft_id") or ""),
        }

    return None
