"""Integration tests — availability intent subgraph (Phase 6).

Availability shows available slots without creating any booking artifacts
unless the user explicitly transitions to the booking path.
"""

from phase1.domain.models import TimeSlot
from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State


class EmptyCalendar:
    def find_two_slots(self, preferred_date_ist: str | None = None) -> list[TimeSlot]:
        return []


def _run(orch: Orchestrator, session: SessionContext, *messages: str) -> list[dict]:
    turns = []
    for msg in messages:
        turn = orch.handle(msg, session)
        turns.append({"messages": turn.messages, "state": session.state.value})
    return turns


def test_availability_shows_slots_without_artifacts() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="avail-slots")
    turns = _run(orch, s, "hi", "ok", "check availability this week")
    assert s.state == State.CLOSE
    avail_msgs = turns[-1]["messages"]
    assert any("IST" in m for m in avail_msgs), "Availability should show IST-labeled slots"
    assert orch.mcp.write_attempts == 0, "Availability must not create any artifacts"


def test_availability_no_slots_message() -> None:
    orch = Orchestrator(calendar=EmptyCalendar())
    s = SessionContext(session_id="avail-empty")
    turns = _run(orch, s, "hi", "ok", "check availability")
    assert s.state == State.CLOSE
    avail_msgs = turns[-1]["messages"]
    assert any("no" in m.lower() and "available" in m.lower() for m in avail_msgs)
    assert orch.mcp.write_attempts == 0


def test_availability_informational_only() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="avail-info")
    turns = _run(orch, s, "hi", "ok", "check availability")
    all_msgs = [m for t in turns for m in t["messages"]]
    assert any("informational" in m.lower() or "book" in m.lower() for m in all_msgs), (
        "Availability response should note that slots are informational or suggest booking"
    )


def test_availability_does_not_persist_session_booking() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="avail-no-booking")
    _run(orch, s, "hi", "ok", "check availability this week")
    assert s.booking_code is None
    assert s.selected_slot is None


def test_availability_no_pii_in_response() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="avail-no-pii")
    turns = _run(orch, s, "hi", "ok", "check availability")
    avail_msgs = turns[-1]["messages"]
    avail_text = " ".join(avail_msgs).lower()
    assert "your phone" not in avail_text
    assert "your email" not in avail_text
    assert "your account" not in avail_text
    assert "your pan" not in avail_text
    assert "your aadhaar" not in avail_text
