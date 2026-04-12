"""Integration tests — full cancel subgraph (Phase 6).

Cancel validates booking code, confirms, then deletes the calendar hold
and appends a cancellation note to the pre-booking log.
"""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from src.domain.booking_store import InMemoryBookingStore
from src.domain.calendar_service import BookingDomainService


def _run(orch: Orchestrator, session: SessionContext, *messages: str) -> list[dict]:
    turns = []
    for msg in messages:
        turn = orch.handle(msg, session)
        turns.append({"messages": turn.messages, "state": session.state.value})
    return turns


def _make_orch_with_booking() -> tuple[Orchestrator, str]:
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="setup-cancel")
    _run(orch, s, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes")
    assert s.booking_code is not None
    return orch, s.booking_code


def test_cancel_validates_code_then_confirms() -> None:
    orch, code = _make_orch_with_booking()
    s = SessionContext(session_id="cancel-confirm")
    turns = _run(orch, s, "hi", "ok", "cancel my booking", code)
    assert s.state == State.CANCEL_CONFIRM
    assert any(code in m for t in turns for m in t["messages"])


def test_cancel_full_flow_deletes_hold_and_appends_note() -> None:
    orch, code = _make_orch_with_booking()
    initial_writes = orch.mcp.write_attempts
    s = SessionContext(session_id="cancel-full")
    turns = _run(orch, s, "hi", "ok", "cancel my booking", code, "yes")
    assert s.state == State.CLOSE
    assert any("cancelled" in m.lower() for t in turns for m in t["messages"])

    new_writes = orch.mcp.write_attempts - initial_writes
    assert new_writes >= 2, (
        f"Cancel should delete hold + append doc = 2+ MCP writes, got {new_writes}"
    )

    record = orch.domain.store.get_by_code(code)
    assert record is not None
    assert record.status == "cancelled"


def test_cancel_unknown_code_returns_not_found() -> None:
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="cancel-unknown")
    turns = _run(orch, s, "hi", "ok", "cancel my booking", "ZZ-X999")
    assert s.state == State.CANCEL_COLLECT_CODE
    assert any("could not find" in m.lower() for t in turns for m in t["messages"])


def test_cancel_abort_keeps_booking_active() -> None:
    orch, code = _make_orch_with_booking()
    s = SessionContext(session_id="cancel-abort")
    _run(orch, s, "hi", "ok", "cancel my booking", code, "no")
    assert s.state == State.CLOSE
    record = orch.domain.store.get_by_code(code)
    assert record is not None
    assert record.status == "tentative", "Booking should remain tentative after abort"


def test_cancel_already_cancelled_returns_not_found() -> None:
    orch, code = _make_orch_with_booking()
    s1 = SessionContext(session_id="cancel-first")
    _run(orch, s1, "hi", "ok", "cancel my booking", code, "yes")

    s2 = SessionContext(session_id="cancel-second")
    turns = _run(orch, s2, "hi", "ok", "cancel my booking", code)
    assert any("could not find" in m.lower() or "already" in m.lower()
               for t in turns for m in t["messages"])


def test_cancel_no_pii_in_booking_code() -> None:
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="cancel-pii")
    turns = _run(orch, s, "hi", "ok", "cancel my booking", "9876543210")
    assert any("personal identifiers" in m.lower() or "cannot process" in m.lower()
               for t in turns for m in t["messages"])
