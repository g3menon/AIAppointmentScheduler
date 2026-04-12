"""Integration tests — prepare intent subgraph (Phase 6).

Prepare intent uses static approved content; no booking artifacts are created.
Topic-specific guidance is provided when the user mentions a known topic.
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


def test_prepare_returns_generic_guidance() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-generic")
    turns = _run(orch, s, "hi", "ok", "what should I prepare")
    assert s.state == State.CLOSE
    all_msgs = [m for t in turns for m in t["messages"]]
    assert any("prepare" in m.lower() for m in all_msgs)
    assert orch.mcp.write_attempts == 0, "Prepare must not create any artifacts"


def test_prepare_returns_topic_specific_guidance_kyc() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-kyc")
    turns = _run(orch, s, "hi", "ok", "what should I prepare for KYC")
    assert s.state == State.CLOSE
    all_msgs = [m for t in turns for m in t["messages"]]
    assert any("kyc" in m.lower() or "onboarding" in m.lower() for m in all_msgs)


def test_prepare_returns_topic_specific_guidance_sip() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-sip")
    turns = _run(orch, s, "hi", "ok", "what should I prepare for SIP")
    assert s.state == State.CLOSE
    all_msgs = [m for t in turns for m in t["messages"]]
    assert any("sip" in m.lower() or "mandates" in m.lower() for m in all_msgs)


def test_prepare_returns_static_content_not_freeform() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-static")
    turns = _run(orch, s, "hi", "ok", "what should I prepare")
    prep_msgs = turns[-1]["messages"]
    assert len(prep_msgs) >= 1
    for m in prep_msgs:
        assert "prepare" in m.lower() or "questions" in m.lower() or "topic" in m.lower(), (
            "Guidance should come from approved static templates"
        )


def test_prepare_does_not_create_mcp_artifacts() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-no-mcp")
    _run(orch, s, "hi", "ok", "what should I prepare for Withdrawals")
    assert orch.mcp.write_attempts == 0


def test_prepare_no_pii_elicitation() -> None:
    orch = Orchestrator()
    s = SessionContext(session_id="prep-no-pii")
    turns = _run(orch, s, "hi", "ok", "what should I prepare")
    all_msgs = " ".join(m for t in turns for m in t["messages"])
    pii_requests = ["your phone", "your email", "your account number", "your pan", "your aadhaar"]
    for phrase in pii_requests:
        assert phrase not in all_msgs.lower(), f"Prepare guidance must not elicit PII: '{phrase}'"
