"""Integration tests — chat handler → orchestrator for all 5 intents.

After booking confirmation, the orchestrator performs the Google MCP trio
(Calendar hold, Docs append, Gmail draft). Under pytest, an in-memory recorder
stands in for Google API calls.
"""

from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State


def _run(orch: Orchestrator, session: SessionContext, *messages: str) -> list[dict]:
    turns = []
    for msg in messages:
        turn = orch.handle(msg, session)
        turns.append({"messages": turn.messages, "state": session.state.value})
    return turns


def test_booking_flow_disclaimer_ist_and_mcp_trio() -> None:
    from phase1.api.chat.routes import orchestrator, post_message

    r1 = post_message("int-book", "hello")
    assert any("informational" in m for m in r1["messages"])

    post_message("int-book", "ok")
    post_message("int-book", "book appointment")
    post_message("int-book", "KYC")
    r5 = post_message("int-book", "tomorrow afternoon")
    ist_msgs = [m for m in r5["messages"] if "IST" in m]
    assert len(ist_msgs) >= 2, "Slots must include IST labels"

    post_message("int-book", "1")
    r7 = post_message("int-book", "yes")
    assert any("confirmed" in m.lower() for m in r7["messages"])
    assert orchestrator.mcp.write_attempts == 3


def test_book_intent_reaches_close() -> None:
    orch, s = Orchestrator(), SessionContext(session_id="int-book2")
    _run(orch, s, "hi", "ok", "book appointment", "SIP", "next Monday", "1", "yes")
    assert s.state == State.CLOSE
    assert orch.mcp.write_attempts == 3


def test_reschedule_intent_reaches_close() -> None:
    orch, s = Orchestrator(), SessionContext(session_id="int-resched")
    _run(orch, s, "hi", "ok", "reschedule my appointment", "AB-X789")
    assert s.state == State.CLOSE
    assert s.pending_booking_code == "AB-X789"
    assert orch.mcp.write_attempts == 0


def test_cancel_intent_reaches_close() -> None:
    orch, s = Orchestrator(), SessionContext(session_id="int-cancel")
    _run(orch, s, "hi", "ok", "cancel my booking", "AB-X789", "yes")
    assert s.state == State.CLOSE
    assert orch.mcp.write_attempts == 0


def test_prepare_intent_reaches_terminal() -> None:
    orch, s = Orchestrator(), SessionContext(session_id="int-prep")
    turns = _run(orch, s, "hi", "ok", "what should I prepare")
    assert s.state == State.PREPARE_TOPIC_OR_GENERIC
    assert any("prepare" in m.lower() for msgs in turns for m in msgs["messages"])
    assert orch.mcp.write_attempts == 0


def test_availability_intent_reaches_terminal() -> None:
    orch, s = Orchestrator(), SessionContext(session_id="int-avail")
    turns = _run(orch, s, "hi", "ok", "check availability this week")
    assert s.state == State.AVAILABILITY_QUERY
    assert any("availability" in m.lower() for msgs in turns for m in msgs["messages"])
    assert orch.mcp.write_attempts == 0


def test_mcp_write_counts_by_intent() -> None:
    scenarios = {
        "book": (["hi", "ok", "book appointment", "KYC", "tomorrow", "1", "yes"], 3),
        "reschedule": (["hi", "ok", "reschedule my appointment", "AB-X789"], 0),
        "cancel": (["hi", "ok", "cancel my booking", "AB-X789", "yes"], 0),
        "prepare": (["hi", "ok", "what should I prepare"], 0),
        "availability": (["hi", "ok", "check availability"], 0),
    }
    for intent, (msgs, expected_writes) in scenarios.items():
        orch = Orchestrator()
        s = SessionContext(session_id=f"mcp-{intent}")
        _run(orch, s, *msgs)
        assert orch.mcp.write_attempts == expected_writes, f"unexpected MCP writes for {intent}"
