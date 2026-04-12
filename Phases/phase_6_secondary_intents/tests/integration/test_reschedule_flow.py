"""Integration tests — full reschedule subgraph (Phase 6).

Reschedule validates booking code against the store, offers two new slots,
confirms the new slot, then executes MCP (delete old hold, create new hold,
append docs, create draft).
"""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from src.domain.booking_store import InMemoryBookingStore
from src.domain.calendar_service import BookingDomainService
from src.domain.models import BookingRecord, TimeSlot


def _run(orch: Orchestrator, session: SessionContext, *messages: str) -> list[dict]:
    turns = []
    for msg in messages:
        turn = orch.handle(msg, session)
        turns.append({"messages": turn.messages, "state": session.state.value})
    return turns


def _make_orch_with_booking() -> tuple[Orchestrator, str]:
    """Create an orchestrator and run a full booking to get a stored record."""
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="setup-book")
    _run(orch, s, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes")
    assert s.booking_code is not None
    return orch, s.booking_code


def test_reschedule_validates_code_then_offers_slots() -> None:
    orch, code = _make_orch_with_booking()
    s = SessionContext(session_id="resched-offer")
    turns = _run(orch, s, "hi", "ok", "reschedule my appointment", code)
    assert s.state == State.RESCHEDULE_OFFER_SLOTS
    slot_msgs = [m for t in turns for m in t["messages"] if "IST" in m]
    assert len(slot_msgs) >= 2, "Must offer two new IST slots"


def test_reschedule_full_flow_creates_new_mcp_trio() -> None:
    orch, code = _make_orch_with_booking()
    initial_writes = orch.mcp.write_attempts
    s = SessionContext(session_id="resched-full")
    _run(orch, s, "hi", "ok", "reschedule my appointment", code, "1", "yes")
    assert s.state == State.CLOSE
    assert s.booking_code is not None
    assert s.booking_code != code, "Reschedule must generate a new booking code"
    new_writes = orch.mcp.write_attempts - initial_writes
    assert new_writes >= 4, (
        f"Reschedule should delete old hold + create hold + append doc + draft = 4+ MCP writes, got {new_writes}"
    )


def test_reschedule_unknown_code_returns_not_found() -> None:
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="resched-unknown")
    turns = _run(orch, s, "hi", "ok", "reschedule my appointment", "ZZ-X999")
    assert s.state == State.RESCHEDULE_COLLECT_CODE
    assert any("could not find" in m.lower() for t in turns for m in t["messages"])


def test_reschedule_no_confirm_stays_in_offer() -> None:
    orch, code = _make_orch_with_booking()
    s = SessionContext(session_id="resched-no")
    _run(orch, s, "hi", "ok", "reschedule my appointment", code, "1", "no")
    assert s.state == State.RESCHEDULE_OFFER_SLOTS, "Saying no should return to slot offers"


def test_reschedule_marks_old_booking_cancelled() -> None:
    orch, code = _make_orch_with_booking()
    old_record = orch.domain.store.get_by_code(code)
    assert old_record is not None
    assert old_record.status == "tentative"

    s = SessionContext(session_id="resched-cancel-old")
    _run(orch, s, "hi", "ok", "reschedule my appointment", code, "1", "yes")
    old_record = orch.domain.store.get_by_code(code)
    assert old_record is not None
    assert old_record.status == "cancelled", "Old booking should be marked cancelled"


def test_reschedule_no_pii_in_booking_code() -> None:
    store = InMemoryBookingStore()
    domain = BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)
    s = SessionContext(session_id="resched-pii")
    turns = _run(orch, s, "hi", "ok", "reschedule my appointment", "9876543210")
    assert any("personal identifiers" in m.lower() or "cannot process" in m.lower()
               for t in turns for m in t["messages"])
