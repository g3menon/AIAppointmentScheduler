from phase1.domain.models import TimeSlot
from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State
from src.domain.models import BookingAction


class EmptyCalendar:
    def find_two_slots(self, preferred_date_ist: str | None = None) -> list[TimeSlot]:
        return []


def _run(orch: Orchestrator, session: SessionContext, *messages: str) -> None:
    for msg in messages:
        orch.handle(msg, session)


def test_no_slot_path_uses_waitlist_domain_command() -> None:
    orch = Orchestrator(calendar=EmptyCalendar())
    session = SessionContext(session_id="phase2-waitlist")
    _run(orch, session, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon")
    assert session.state == State.CLOSE
    assert session.booking_code is not None
    assert orch.domain.last_command is not None
    assert orch.domain.last_command.action == BookingAction.WAITLIST
    assert orch.mcp.write_attempts == 0


def test_booking_confirmation_uses_domain_command() -> None:
    orch = Orchestrator()
    session = SessionContext(session_id="phase2-book")
    _run(orch, session, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes")
    assert session.state == State.CLOSE
    assert orch.domain.last_command is not None
    assert orch.domain.last_command.action == BookingAction.HOLD


def test_secondary_intents_delegate_to_domain() -> None:
    store = __import__("src.domain.booking_store", fromlist=["InMemoryBookingStore"]).InMemoryBookingStore()
    domain = __import__("src.domain.calendar_service", fromlist=["BookingDomainService"]).BookingDomainService(store=store)
    orch = Orchestrator(domain_service=domain)

    s_book = SessionContext(session_id="phase2-book-for-secondary")
    _run(orch, s_book, "hi", "ok", "book appointment", "KYC", "tomorrow afternoon", "1", "yes")
    code = s_book.booking_code
    assert code is not None

    s_reschedule = SessionContext(session_id="phase2-reschedule")
    _run(orch, s_reschedule, "hi", "ok", "reschedule my appointment", code, "1", "yes")
    assert s_reschedule.state == State.CLOSE
    assert orch.domain.last_command is not None
    assert orch.domain.last_command.action == BookingAction.RESCHEDULE

    s_book2 = SessionContext(session_id="phase2-book-for-cancel")
    _run(orch, s_book2, "hi", "ok", "book appointment", "SIP", "next week", "1", "yes")
    code2 = s_book2.booking_code
    assert code2 is not None

    s_cancel = SessionContext(session_id="phase2-cancel")
    _run(orch, s_cancel, "hi", "ok", "cancel booking", code2, "yes")
    assert s_cancel.state == State.CLOSE
    assert orch.domain.last_command is not None
    assert orch.domain.last_command.action == BookingAction.CANCEL
