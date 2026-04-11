"""Conversation orchestrator — Architecture.md §11.5 turn execution model."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from phase1.domain.calendar_service import MockCalendarService
from phase1.domain.models import Intent
from phase1.session import prompt_templates as T
from phase1.session.pii_guard import contains_pii
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from phase1.session.topic_catalog import resolve_topic
from src.domain.booking_code_generator import BookingCodeGenerator
from src.integrations.google_mcp.client import GoogleMcpClient, validate_mcp_prerequisites


def _default_mcp_client():
    """Production uses real Google MCP; pytest sets PYTEST_CURRENT_TEST — use in-memory recorder."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        from phase1.integrations.mcp.recording_client import RecordingGoogleMcpClient

        return RecordingGoogleMcpClient()
    return GoogleMcpClient.from_env()


@dataclass
class AgentTurn:
    messages: list[str] = field(default_factory=list)
    side_effects: list[dict] = field(default_factory=list)


class Orchestrator:
    """Single text-in/text-out runtime contract: handle(user_text, session) -> AgentTurn."""

    def __init__(self, mcp_client=None, calendar: MockCalendarService | None = None) -> None:
        self.calendar = calendar or MockCalendarService()
        self._mcp = mcp_client

    @property
    def mcp(self):
        if self._mcp is None:
            self._mcp = _default_mcp_client()
        return self._mcp

    def handle(self, user_text: str, session: SessionContext) -> AgentTurn:
        text = (user_text or "").strip()
        lower = text.lower()
        session.turn_count += 1

        if contains_pii(text):
            return AgentTurn(messages=[T.PII_REJECTION])

        if "investment advice" in lower:
            session.advice_redirect_count += 1
            return AgentTurn(messages=[T.INVESTMENT_ADVICE_REFUSAL])

        handler = _STATE_HANDLERS.get(session.state, _handle_closed)
        return handler(self, text, lower, session)

    @staticmethod
    def _detect_intent(text: str) -> Intent:
        if "reschedule" in text:
            return Intent.RESCHEDULE
        if "cancel" in text:
            return Intent.CANCEL
        if "prepare" in text:
            return Intent.WHAT_TO_PREPARE
        if "availability" in text or "available" in text:
            return Intent.CHECK_AVAILABILITY
        if "book" in text or "appointment" in text:
            return Intent.BOOK_NEW
        return Intent.UNKNOWN

    @staticmethod
    def _parse_slot_choice(text: str) -> int | None:
        if "1" in text:
            return 0
        if "2" in text:
            return 1
        return None


def _handle_greet(_orch: Orchestrator, _text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.state = State.DISCLAIMER_AWAIT_ACK
    return AgentTurn(messages=[T.GREETING, T.DISCLAIMER])


def _handle_disclaimer(_orch: Orchestrator, _text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.disclaimer_acknowledged = True
    session.state = State.INTENT_ROUTING
    return AgentTurn(messages=[T.INTENT_PROMPT])


def _handle_intent_routing(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    detected = orch._detect_intent(lower)
    session.intent = detected.value

    if detected == Intent.WHAT_TO_PREPARE:
        session.state = State.PREPARE_TOPIC_OR_GENERIC
        return AgentTurn(messages=[T.PREPARE_GUIDANCE])

    if detected == Intent.CHECK_AVAILABILITY:
        session.state = State.AVAILABILITY_QUERY
        return AgentTurn(messages=[T.AVAILABILITY_RESPONSE])

    if detected == Intent.RESCHEDULE:
        session.state = State.RESCHEDULE_COLLECT_CODE
        return AgentTurn(messages=[T.RESCHEDULE_COLLECT_CODE])

    if detected == Intent.CANCEL:
        session.state = State.CANCEL_COLLECT_CODE
        return AgentTurn(messages=[T.CANCEL_COLLECT_CODE])

    if detected == Intent.BOOK_NEW:
        session.state = State.BOOK_TOPIC
        return AgentTurn(messages=[T.TOPIC_PROMPT])

    return AgentTurn(messages=[T.UNKNOWN_INTENT])


def _handle_book_topic(orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    topic = resolve_topic(text)
    if topic is None:
        return AgentTurn(messages=[T.TOPIC_UNSUPPORTED])

    session.topic = topic.value
    session.state = State.BOOK_TIME_PREFERENCE
    return AgentTurn(messages=[T.TIME_PREFERENCE_PROMPT])


def _handle_book_time_preference(orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.time_preference = text
    slots = orch.calendar.find_two_slots()
    session.offered_slot_choices = slots
    session.offered_slots = [slot.label_ist for slot in slots]
    session.state = State.BOOK_OFFER_SLOTS
    return AgentTurn(
        messages=[
            T.SLOT_OFFER_HEADER,
            f"1) {session.offered_slots[0]}",
            f"2) {session.offered_slots[1]}",
            T.SLOT_CONFIRM_PROMPT,
        ]
    )


def _handle_book_offer_slots(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    selection = orch._parse_slot_choice(lower)
    if selection is None:
        return AgentTurn(messages=[T.SLOT_INVALID_CHOICE])

    chosen = session.offered_slot_choices[selection]
    session.selected_timeslot = chosen
    session.selected_slot = chosen.label_ist
    session.state = State.BOOK_CONFIRM
    return AgentTurn(messages=[T.slot_confirmation_message(session.selected_slot)])


def _execute_confirmed_booking(orch: Orchestrator, session: SessionContext) -> AgentTurn:
    slot = session.selected_timeslot
    topic = session.topic
    if slot is None or topic is None:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.mcp_booking_failed_message()])

    if isinstance(orch.mcp, GoogleMcpClient):
        validate_mcp_prerequisites(orch.mcp.settings)

    code = BookingCodeGenerator(exists_fn=lambda _: False).generate()
    session.booking_code = code
    ns = orch.mcp.settings.idempotency_namespace
    cal_id = orch.mcp.settings.calendar_id
    title = f"Advisor Q&A - {topic} - {code}"

    try:
        event_id = orch.mcp.create_calendar_hold(
            title,
            slot.start_utc,
            slot.end_utc,
            cal_id,
            f"{ns}:{code}:calendar",
        )
        log_line = f"{topic} | {slot.label_ist} | {code} | tentative_hold"
        orch.mcp.append_prebooking_log(
            orch.mcp.settings.prebooking_doc_id,
            log_line,
            f"{ns}:{code}:doc",
        )
        subject = f"Advisor pre-booking {code}"
        body = (
            f"Topic: {topic}\n"
            f"Slot (IST label): {slot.label_ist}\n"
            f"Booking code: {code}\n"
            "This is a draft only — approval required before send.\n"
        )
        draft_id = orch.mcp.create_gmail_draft(orch.mcp.settings.advisor_email_to, subject, body)
    except Exception:
        session.booking_code = None
        session.state = State.CLOSE
        return AgentTurn(messages=[T.mcp_booking_failed_message()])

    session.state = State.CLOSE
    return AgentTurn(
        messages=[T.booking_confirmed_message(session.selected_slot or slot.label_ist, code, event_id, draft_id)],
        side_effects=[{"calendar_event_id": event_id, "gmail_draft_id": draft_id}],
    )


def _handle_book_confirm(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    if "yes" in lower or "confirm" in lower or "y" == lower:
        return _execute_confirmed_booking(orch, session)

    if "no" in lower or "n" == lower:
        session.state = State.BOOK_OFFER_SLOTS
        return AgentTurn(
            messages=[
                T.SLOT_OFFER_HEADER,
                f"1) {session.offered_slots[0]}",
                f"2) {session.offered_slots[1]}",
                T.SLOT_CONFIRM_PROMPT,
            ]
        )

    return AgentTurn(messages=["Please reply with yes or no to confirm your selected slot."])


def _handle_reschedule_collect_code(_orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.pending_booking_code = text.strip().upper()
    session.state = State.CLOSE
    return AgentTurn(messages=[T.RESCHEDULE_PHASE1_STUB])


def _handle_cancel_collect_code(_orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.pending_booking_code = text.strip().upper()
    session.state = State.CANCEL_CONFIRM
    return AgentTurn(messages=[T.CANCEL_CONFIRM_PROMPT.format(code=text.strip().upper())])


def _handle_cancel_confirm(_orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    session.state = State.CLOSE
    if "yes" in lower or "y" == lower:
        return AgentTurn(messages=[T.CANCEL_PHASE1_STUB])
    return AgentTurn(messages=["Cancellation aborted. Your booking remains active."])


def _handle_prepare(_orch: Orchestrator, _text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.state = State.CLOSE
    return AgentTurn(messages=[T.SESSION_COMPLETE])


def _handle_availability(_orch: Orchestrator, _text: str, _lower: str, session: SessionContext) -> AgentTurn:
    session.state = State.CLOSE
    return AgentTurn(messages=[T.SESSION_COMPLETE])


def _handle_closed(_orch: Orchestrator, _text: str, _lower: str, _session: SessionContext) -> AgentTurn:
    return AgentTurn(messages=[T.SESSION_COMPLETE])


_STATE_HANDLERS = {
    State.GREET: _handle_greet,
    State.DISCLAIMER_AWAIT_ACK: _handle_disclaimer,
    State.INTENT_ROUTING: _handle_intent_routing,
    State.BOOK_TOPIC: _handle_book_topic,
    State.BOOK_TIME_PREFERENCE: _handle_book_time_preference,
    State.BOOK_OFFER_SLOTS: _handle_book_offer_slots,
    State.BOOK_CONFIRM: _handle_book_confirm,
    State.RESCHEDULE_COLLECT_CODE: _handle_reschedule_collect_code,
    State.RESCHEDULE_OFFER_SLOTS: _handle_closed,
    State.CANCEL_COLLECT_CODE: _handle_cancel_collect_code,
    State.CANCEL_CONFIRM: _handle_cancel_confirm,
    State.PREPARE_TOPIC_OR_GENERIC: _handle_prepare,
    State.AVAILABILITY_QUERY: _handle_availability,
    State.CLOSE: _handle_closed,
    State.BOOK_EXECUTE_MCP: _handle_closed,
    State.ERROR_RECOVER: _handle_closed,
}
