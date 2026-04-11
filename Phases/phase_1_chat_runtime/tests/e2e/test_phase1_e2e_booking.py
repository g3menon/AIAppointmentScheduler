"""E2E test — one full booking chat transcript.

Under pytest, Google MCP calls are recorded in memory (no network).
In production, the same code path uses GoogleMcpClient.from_env().
"""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State


def test_full_booking_transcript() -> None:
    orch = Orchestrator()
    session = SessionContext(session_id="e2e-booking")

    t1 = orch.handle("hello", session)
    assert session.state == State.DISCLAIMER_AWAIT_ACK
    assert any("informational" in m for m in t1.messages), "Disclaimer must appear on greet"

    t2 = orch.handle("I understand", session)
    assert session.state == State.INTENT_ROUTING
    assert session.disclaimer_acknowledged is True

    t3 = orch.handle("I'd like to book an appointment", session)
    assert session.state == State.BOOK_TOPIC
    assert session.intent == "book_new"

    t4 = orch.handle("KYC", session)
    assert session.state == State.BOOK_TIME_PREFERENCE
    assert session.topic == "KYC/Onboarding"

    t5 = orch.handle("tomorrow afternoon", session)
    assert session.state == State.BOOK_OFFER_SLOTS
    assert len(session.offered_slots) == 2, "Exactly two slots must be offered"
    ist_slot_msgs = [m for m in t5.messages if "IST" in m]
    assert len(ist_slot_msgs) >= 2, "Both slots must show IST labels"

    t6 = orch.handle("1", session)
    assert session.state == State.BOOK_CONFIRM
    assert session.selected_slot is not None
    assert "IST" in session.selected_slot, "Selected slot must include IST"
    assert any("IST" in m for m in t6.messages), "Confirmation prompt must repeat IST"

    t7 = orch.handle("yes", session)
    assert session.state == State.CLOSE
    assert any("confirmed" in m.lower() for m in t7.messages)

    assert orch.mcp.write_attempts == 3
    assert session.booking_code is not None


def test_full_booking_transcript_with_reprompts() -> None:
    orch = Orchestrator()
    session = SessionContext(session_id="e2e-reprompt")

    orch.handle("hi", session)
    orch.handle("ok", session)
    orch.handle("book", session)

    t_bad_topic = orch.handle("crypto trading", session)
    assert session.state == State.BOOK_TOPIC
    assert any("not supported" in m.lower() for m in t_bad_topic.messages)

    orch.handle("withdrawals", session)
    assert session.state == State.BOOK_TIME_PREFERENCE

    orch.handle("next week", session)
    assert session.state == State.BOOK_OFFER_SLOTS

    t_bad_slot = orch.handle("three", session)
    assert session.state == State.BOOK_OFFER_SLOTS
    assert any("1 or 2" in m for m in t_bad_slot.messages)

    orch.handle("2", session)
    assert session.state == State.BOOK_CONFIRM

    orch.handle("no", session)
    assert session.state == State.BOOK_OFFER_SLOTS

    orch.handle("1", session)
    orch.handle("yes", session)
    assert session.state == State.CLOSE
    assert orch.mcp.write_attempts == 3
