from src.session.orchestrator import Orchestrator
from src.session.session_context import SessionContext
from src.session.state import State


def test_phase1_booking_state_progression() -> None:
    orchestrator = Orchestrator()
    session = SessionContext(session_id="s-1")

    turn1 = orchestrator.handle("hello", session)
    assert session.state == State.DISCLAIMER_AWAIT_ACK
    assert any("informational and not investment advice" in msg for msg in turn1.messages)

    orchestrator.handle("ok", session)
    assert session.state == State.INTENT_ROUTING

    orchestrator.handle("book appointment", session)
    assert session.state == State.BOOK_OFFER_SLOTS

    turn4 = orchestrator.handle("KYC", session)
    assert session.state == State.BOOK_CONFIRM
    assert len([m for m in turn4.messages if "IST" in m]) >= 2

    turn5 = orchestrator.handle("1", session)
    assert session.state == State.CLOSE
    assert any("Confirmed in IST" in msg for msg in turn5.messages)


def test_pii_input_is_blocked() -> None:
    orchestrator = Orchestrator()
    session = SessionContext(session_id="s-2")

    turn = orchestrator.handle("my email is test@example.com", session)
    assert any("cannot process personal identifiers" in msg for msg in turn.messages)
    assert session.state == State.GREET


def test_default_state_is_greet() -> None:
    session = SessionContext(session_id="s-1")
    assert session.state == State.GREET
