"""Conversation orchestrator — Architecture.md §11.5 turn execution model."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

from phase1.domain.calendar_service import MockCalendarService
from phase1.domain.models import Intent
from phase1.session import prompt_templates as T
from phase1.session.pii_guard import contains_pii
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from phase1.session.topic_catalog import resolve_topic
from src.domain.calendar_service import (
    BookingDomainService,
    BookingNotFoundError,
    DomainValidationError,
)
from src.integrations.google_mcp.booking_mcp_executor import (
    BookingMcpBundle,
    BookingMcpExecutionError,
    run_booking_mcp_triplet,
)
from src.integrations.google_mcp.client import GoogleMcpClient
from src.integrations.google_mcp.mcp_tool_dispatch import dispatch_mcp_tool
from src.observability.audit import record_artifact_status
from src.observability.logger import log_event
from src.session.orchestrator import build_recovery_plan


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

    def __init__(
        self,
        mcp_client=None,
        calendar: MockCalendarService | None = None,
        domain_service: BookingDomainService | None = None,
    ) -> None:
        self.calendar = calendar or MockCalendarService()
        self._mcp = mcp_client
        self.domain = domain_service or BookingDomainService()

    @property
    def mcp(self):
        if self._mcp is None:
            self._mcp = _default_mcp_client()
        return self._mcp

    def handle(self, user_text: str, session: SessionContext) -> AgentTurn:
        start = time.perf_counter()
        text = (user_text or "").strip()
        lower = text.lower()
        session.turn_count += 1

        error_type = "none"
        if contains_pii(text):
            turn = AgentTurn(messages=[T.PII_REJECTION])
            self._log_turn(session, error_type, start)
            return turn

        if "investment advice" in lower:
            session.advice_redirect_count += 1
            turn = AgentTurn(messages=[T.INVESTMENT_ADVICE_REFUSAL])
            self._log_turn(session, error_type, start)
            return turn

        handler = _STATE_HANDLERS.get(session.state, _handle_closed)
        turn = handler(self, text, lower, session)
        if session.last_mcp_error:
            error_type = session.last_mcp_error
        self._log_turn(session, error_type, start)
        return turn

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
        if re.fullmatch(r"\s*(?:option\s*)?1\s*\)?\s*", text):
            return 0
        if re.fullmatch(r"\s*(?:option\s*)?2\s*\)?\s*", text):
            return 1
        return None

    @staticmethod
    def _log_turn(session: SessionContext, error_type: str, start: float) -> None:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_event(
            "orchestrator_turn",
            {
                "session_id": session.session_id,
                "stage": session.state.value,
                "intent": session.intent or "unknown",
                "booking_code": session.booking_code or "",
                "error_type": error_type,
                "latency_ms": latency_ms,
            },
        )


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
        for topic_key, guidance in T.PREPARE_TOPIC_GUIDANCE.items():
            parts = topic_key.lower().replace("/", " ").split()
            if any(p in lower for p in parts if len(p) > 2):
                session.state = State.CLOSE
                return AgentTurn(messages=[guidance])
        session.state = State.CLOSE
        return AgentTurn(messages=[T.PREPARE_GUIDANCE])

    if detected == Intent.CHECK_AVAILABILITY:
        slots = orch.calendar.find_two_slots()
        slot_labels = [s.label_ist for s in slots]
        session.state = State.CLOSE
        return AgentTurn(messages=[T.availability_slots_message(slot_labels)])

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
    if not slots:
        if session.topic is None:
            session.state = State.CLOSE
            return AgentTurn(messages=[T.mcp_booking_failed_message()])
        decision = orch.domain.create_booking_decision(
            topic=session.topic,
            selected_slot=None,
            time_preference=text,
        )
        session.booking_code = decision.command.booking_code
        session.state = State.CLOSE
        return AgentTurn(messages=[decision.user_message])

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
    normalized = _text.strip().lower()
    selection = None
    for idx, offered in enumerate(session.offered_slots):
        if normalized == offered.lower():
            selection = idx
            break
    if selection is None:
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
    if topic is None:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.mcp_booking_failed_message()])

    try:
        decision = orch.domain.create_booking_decision(
            topic=topic,
            selected_slot=slot,
            time_preference=session.time_preference or "unspecified",
        )
    except DomainValidationError:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.PII_REJECTION])

    command = decision.command
    code = command.booking_code
    session.booking_code = code
    if command.action.value == "waitlist":
        session.state = State.CLOSE
        return AgentTurn(messages=[decision.user_message])
    if command.slot is None:
        session.booking_code = None
        session.state = State.CLOSE
        return AgentTurn(messages=[T.mcp_booking_failed_message()])

    ns = orch.mcp.settings.idempotency_namespace
    cal_id = orch.mcp.settings.calendar_id
    doc_id = orch.mcp.settings.prebooking_doc_id or "pytest-prebooking-doc"
    gmail_to = orch.mcp.settings.advisor_email_to or "advisor@example.com"
    title = f"Advisor Q&A - {topic} - {code}"
    log_line = command.notes_entry
    subject = command.email_draft_payload.get("subject", f"Advisor pre-booking {code}")
    body = command.email_draft_payload.get("body", "")
    bundle = BookingMcpBundle(
        calendar_title=title,
        start_utc=command.slot.start_utc,
        end_utc=command.slot.end_utc,
        calendar_id=cal_id,
        calendar_idempotency_key=f"{ns}:{code}:calendar",
        doc_id=doc_id,
        doc_line=log_line,
        doc_idempotency_key=f"{ns}:{code}:doc",
        gmail_to=gmail_to,
        gmail_subject=subject,
        gmail_body=body,
    )

    try:
        mcp_result = run_booking_mcp_triplet(orch.mcp, bundle)
        event_id = mcp_result.event_id
        draft_id = mcp_result.draft_id
    except BookingMcpExecutionError as exc:
        session.last_mcp_error = "integration"
        record_artifact_status(
            session.session_id,
            {
                "booking_code": code,
                "calendar_status": exc.artifact_status.get("calendar", "unknown"),
                "docs_status": exc.artifact_status.get("docs", "unknown"),
                "gmail_status": exc.artifact_status.get("gmail", "unknown"),
                "failure_stage": exc.stage,
            },
        )
        session.booking_code = None
        session.state = State.CLOSE
        return AgentTurn(messages=[build_recovery_plan(exc).fallback_message])
    except Exception as exc:
        session.last_mcp_error = "system"
        session.booking_code = None
        session.state = State.CLOSE
        return AgentTurn(messages=[build_recovery_plan(exc).fallback_message])

    orch.domain.save_confirmed_booking(
        code=code,
        topic=topic,
        slot=command.slot,
        event_id=event_id,
        draft_id=draft_id,
    )

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


def _handle_reschedule_collect_code(orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    code = text.strip().upper()
    session.pending_booking_code = code
    try:
        orch.domain.lookup_booking(code)
    except DomainValidationError:
        return AgentTurn(messages=[T.PII_REJECTION])
    except BookingNotFoundError:
        return AgentTurn(messages=[T.RESCHEDULE_NOT_FOUND])

    slots = orch.calendar.find_two_slots()
    if not slots:
        session.state = State.CLOSE
        return AgentTurn(messages=[
            "No alternative slots are available right now for rescheduling. "
            "Please try again later."
        ])

    session.offered_slot_choices = slots
    session.offered_slots = [s.label_ist for s in slots]
    session.state = State.RESCHEDULE_OFFER_SLOTS
    return AgentTurn(
        messages=[
            T.RESCHEDULE_OFFER_HEADER,
            f"1) {session.offered_slots[0]}",
            f"2) {session.offered_slots[1]}",
            T.RESCHEDULE_SLOT_CONFIRM_PROMPT,
        ]
    )


def _handle_reschedule_offer_slots(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    normalized = _text.strip().lower()
    selection = None
    for idx, offered in enumerate(session.offered_slots):
        if normalized == offered.lower():
            selection = idx
            break
    if selection is None:
        selection = orch._parse_slot_choice(lower)
    if selection is None:
        return AgentTurn(messages=[T.SLOT_INVALID_CHOICE])

    chosen = session.offered_slot_choices[selection]
    session.selected_timeslot = chosen
    session.selected_slot = chosen.label_ist
    session.state = State.RESCHEDULE_CONFIRM
    return AgentTurn(
        messages=[T.reschedule_confirmation_message(session.pending_booking_code or "", session.selected_slot)]
    )


def _handle_reschedule_confirm(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    if "no" in lower or "n" == lower:
        session.state = State.RESCHEDULE_OFFER_SLOTS
        return AgentTurn(
            messages=[
                T.RESCHEDULE_OFFER_HEADER,
                f"1) {session.offered_slots[0]}",
                f"2) {session.offered_slots[1]}",
                T.RESCHEDULE_SLOT_CONFIRM_PROMPT,
            ]
        )

    if "yes" not in lower and "confirm" not in lower and lower != "y":
        return AgentTurn(messages=["Please reply with yes or no to confirm rescheduling."])

    return _execute_reschedule(orch, session)


def _execute_reschedule(orch: Orchestrator, session: SessionContext) -> AgentTurn:
    old_code = session.pending_booking_code or ""
    new_slot = session.selected_timeslot
    if new_slot is None:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.mcp_booking_failed_message()])

    old_record = orch.domain.store.get_by_code(old_code)
    old_event_id = old_record.event_id if old_record else ""
    cal_id = orch.mcp.settings.calendar_id

    try:
        decision = orch.domain.create_reschedule_decision(
            booking_code=old_code,
            new_slot=new_slot,
        )
    except DomainValidationError:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.PII_REJECTION])

    command = decision.command
    new_code = command.booking_code
    topic = command.topic or "General"

    if old_event_id:
        try:
            dispatch_mcp_tool(orch.mcp, "calendar_delete_hold", {
                "event_id": old_event_id,
                "calendar_id": cal_id,
            })
        except Exception:
            pass

    ns = orch.mcp.settings.idempotency_namespace
    doc_id = orch.mcp.settings.prebooking_doc_id or "pytest-prebooking-doc"
    gmail_to = orch.mcp.settings.advisor_email_to or "advisor@example.com"
    title = f"Advisor Q&A - {topic} - {new_code}"
    bundle = BookingMcpBundle(
        calendar_title=title,
        start_utc=new_slot.start_utc,
        end_utc=new_slot.end_utc,
        calendar_id=cal_id,
        calendar_idempotency_key=f"{ns}:{new_code}:calendar",
        doc_id=doc_id,
        doc_line=command.notes_entry,
        doc_idempotency_key=f"{ns}:{new_code}:doc",
        gmail_to=gmail_to,
        gmail_subject=command.email_draft_payload.get("subject", f"Advisor reschedule {new_code}"),
        gmail_body=command.email_draft_payload.get("body", ""),
    )

    try:
        mcp_result = run_booking_mcp_triplet(orch.mcp, bundle)
    except (BookingMcpExecutionError, Exception) as exc:
        session.last_mcp_error = "integration"
        session.state = State.CLOSE
        return AgentTurn(messages=[build_recovery_plan(exc).fallback_message])

    if old_record:
        orch.domain.mark_cancelled(old_code)

    orch.domain.save_confirmed_booking(
        code=new_code,
        topic=topic,
        slot=new_slot,
        event_id=mcp_result.event_id,
        draft_id=mcp_result.draft_id,
    )

    session.booking_code = new_code
    session.state = State.CLOSE
    return AgentTurn(
        messages=[T.reschedule_confirmed_message(new_slot.label_ist, new_code)],
        side_effects=[{"calendar_event_id": mcp_result.event_id, "gmail_draft_id": mcp_result.draft_id}],
    )


def _handle_cancel_collect_code(orch: Orchestrator, text: str, _lower: str, session: SessionContext) -> AgentTurn:
    code = text.strip().upper()
    session.pending_booking_code = code
    try:
        orch.domain.lookup_booking(code)
    except DomainValidationError:
        return AgentTurn(messages=[T.PII_REJECTION])
    except BookingNotFoundError:
        return AgentTurn(messages=[T.CANCEL_NOT_FOUND])

    session.state = State.CANCEL_CONFIRM
    return AgentTurn(messages=[T.CANCEL_CONFIRM_PROMPT.format(code=code)])


def _handle_cancel_confirm(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    if "no" in lower or "n" == lower:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.CANCEL_ABORTED])

    if "yes" not in lower and "confirm" not in lower and lower != "y":
        return AgentTurn(messages=["Please reply with yes or no to confirm cancellation."])

    return _execute_cancel(orch, session)


def _execute_cancel(orch: Orchestrator, session: SessionContext) -> AgentTurn:
    code = session.pending_booking_code or ""
    record = orch.domain.store.get_by_code(code)
    cal_id = orch.mcp.settings.calendar_id
    ns = orch.mcp.settings.idempotency_namespace
    doc_id = orch.mcp.settings.prebooking_doc_id or "pytest-prebooking-doc"

    if record and record.event_id:
        try:
            dispatch_mcp_tool(orch.mcp, "calendar_delete_hold", {
                "event_id": record.event_id,
                "calendar_id": cal_id,
            })
        except Exception:
            pass

    try:
        decision = orch.domain.create_cancel_decision(booking_code=code)
    except DomainValidationError:
        session.state = State.CLOSE
        return AgentTurn(messages=[T.PII_REJECTION])

    try:
        dispatch_mcp_tool(orch.mcp, "docs_append_prebooking", {
            "doc_id": doc_id,
            "line": decision.command.notes_entry,
            "idempotency_key": f"{ns}:{code}:cancel_doc",
        })
    except Exception:
        pass

    orch.domain.mark_cancelled(code)
    session.booking_code = code
    session.state = State.CLOSE
    return AgentTurn(messages=[T.cancel_confirmed_message(code)])


def _handle_prepare(orch: Orchestrator, _text: str, lower: str, session: SessionContext) -> AgentTurn:
    for topic_key, guidance in T.PREPARE_TOPIC_GUIDANCE.items():
        if topic_key.lower().split("/")[0] in lower or topic_key.lower().split("/")[-1] in lower:
            session.state = State.CLOSE
            return AgentTurn(messages=[guidance])

    session.state = State.CLOSE
    return AgentTurn(messages=[T.PREPARE_GUIDANCE])


def _handle_availability(orch: Orchestrator, _text: str, _lower: str, session: SessionContext) -> AgentTurn:
    slots = orch.calendar.find_two_slots()
    slot_labels = [s.label_ist for s in slots]
    session.state = State.CLOSE
    return AgentTurn(messages=[T.availability_slots_message(slot_labels)])


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
    State.RESCHEDULE_OFFER_SLOTS: _handle_reschedule_offer_slots,
    State.RESCHEDULE_CONFIRM: _handle_reschedule_confirm,
    State.CANCEL_COLLECT_CODE: _handle_cancel_collect_code,
    State.CANCEL_CONFIRM: _handle_cancel_confirm,
    State.PREPARE_TOPIC_OR_GENERIC: _handle_prepare,
    State.AVAILABILITY_QUERY: _handle_availability,
    State.CLOSE: _handle_closed,
    State.BOOK_EXECUTE_MCP: _handle_closed,
    State.ERROR_RECOVER: _handle_closed,
}
