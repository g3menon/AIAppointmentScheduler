"""Unit tests — state machine transitions per Architecture.md §9 Phase 1."""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State


def _fresh(session_id: str = "s-unit") -> tuple[Orchestrator, SessionContext]:
    return Orchestrator(), SessionContext(session_id=session_id)


# ── happy-path booking: GREET → … → CLOSE ───────────────────────────


def test_greet_transitions_to_disclaimer() -> None:
    orch, s = _fresh()
    turn = orch.handle("hello", s)
    assert s.state == State.DISCLAIMER_AWAIT_ACK
    assert any("informational" in m for m in turn.messages)


def test_disclaimer_ack_transitions_to_intent_routing() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    assert s.state == State.INTENT_ROUTING
    assert s.disclaimer_acknowledged is True


def test_booking_intent_transitions_to_book_topic() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    orch.handle("book appointment", s)
    assert s.state == State.BOOK_TOPIC


def test_topic_accepted_transitions_to_time_preference() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    orch.handle("book appointment", s)
    orch.handle("KYC", s)
    assert s.state == State.BOOK_TIME_PREFERENCE
    assert s.topic == "KYC/Onboarding"


def test_time_preference_transitions_to_slot_offer() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    orch.handle("book appointment", s)
    orch.handle("KYC", s)
    turn = orch.handle("tomorrow afternoon", s)
    assert s.state == State.BOOK_OFFER_SLOTS
    assert s.time_preference == "tomorrow afternoon"
    assert len(s.offered_slots) == 2
    ist_messages = [m for m in turn.messages if "IST" in m]
    assert len(ist_messages) >= 2


def test_slot_selection_transitions_to_confirm() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment", "KYC", "tomorrow"]:
        orch.handle(msg, s)
    orch.handle("1", s)
    assert s.state == State.BOOK_CONFIRM
    assert s.selected_slot is not None
    assert "IST" in s.selected_slot


def test_confirm_yes_transitions_to_close() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment", "KYC", "tomorrow", "1"]:
        orch.handle(msg, s)
    turn = orch.handle("yes", s)
    assert s.state == State.CLOSE
    assert any("confirmed" in m.lower() for m in turn.messages)


def test_confirm_no_returns_to_slot_offer() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment", "KYC", "tomorrow", "1"]:
        orch.handle(msg, s)
    orch.handle("no", s)
    assert s.state == State.BOOK_OFFER_SLOTS


# ── unsupported topic re-prompt ──────────────────────────────────────


def test_unsupported_topic_stays_in_book_topic() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment"]:
        orch.handle(msg, s)
    turn = orch.handle("portfolio rebalancing", s)
    assert s.state == State.BOOK_TOPIC
    assert any("not supported" in m.lower() for m in turn.messages)


# ── invalid slot choice re-prompt ────────────────────────────────────


def test_invalid_slot_choice_reprompts() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment", "KYC", "tomorrow"]:
        orch.handle(msg, s)
    turn = orch.handle("maybe", s)
    assert s.state == State.BOOK_OFFER_SLOTS
    assert any("1 or 2" in m for m in turn.messages)


# ── PII gate ─────────────────────────────────────────────────────────


def test_pii_blocked_at_any_state() -> None:
    orch, s = _fresh()
    turn = orch.handle("my email is test@example.com", s)
    assert any("cannot process personal identifiers" in m.lower() for m in turn.messages)
    assert s.state == State.GREET  # state unchanged


# ── investment advice refusal ────────────────────────────────────────


def test_investment_advice_refused() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    turn = orch.handle("give me investment advice", s)
    assert any("unable to provide investment advice" in m.lower() for m in turn.messages)
    assert s.advice_redirect_count == 1


# ── unknown intent re-prompt ─────────────────────────────────────────


def test_unknown_intent_reprompts() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    turn = orch.handle("what is the weather", s)
    assert s.state == State.INTENT_ROUTING
    assert any("didn't quite catch" in m.lower() for m in turn.messages)


# ── reschedule intent (Phase 1 stub) ────────────────────────────────


def test_reschedule_collects_code() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    orch.handle("reschedule my appointment", s)
    assert s.state == State.RESCHEDULE_COLLECT_CODE
    turn = orch.handle("AB-C123", s)
    assert s.pending_booking_code == "AB-C123"
    assert any("could not find" in m.lower() for m in turn.messages)


# ── cancel intent ────────────────────────────────────────────────────


def test_cancel_collects_code() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    orch.handle("cancel my booking", s)
    assert s.state == State.CANCEL_COLLECT_CODE
    turn = orch.handle("AB-C123", s)
    assert s.pending_booking_code == "AB-C123"
    assert any("could not find" in m.lower() for m in turn.messages)


# ── prepare intent ───────────────────────────────────────────────────


def test_prepare_intent_gives_guidance() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    turn = orch.handle("what should I prepare", s)
    assert s.state == State.CLOSE
    assert any("prepare" in m.lower() for m in turn.messages)


# ── availability intent ──────────────────────────────────────────────


def test_availability_intent_responds() -> None:
    orch, s = _fresh()
    orch.handle("hi", s)
    orch.handle("ok", s)
    turn = orch.handle("check availability", s)
    assert s.state == State.CLOSE
    assert any("slot" in m.lower() or "available" in m.lower() for m in turn.messages)


# ── closed session ───────────────────────────────────────────────────


def test_closed_session_returns_complete_message() -> None:
    orch, s = _fresh()
    for msg in ["hi", "ok", "book appointment", "KYC", "tomorrow", "1", "yes"]:
        orch.handle(msg, s)
    assert s.state == State.CLOSE
    turn = orch.handle("hello again", s)
    assert any("complete" in m.lower() for m in turn.messages)
