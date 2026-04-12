from phase1.api.chat.ui_hints import (
    build_booking_summary,
    build_intent_preview,
    build_quick_replies,
)
from phase1.session.orchestrator import Orchestrator
from phase1.session.session_store import InMemorySessionStore
from phase1.session.state import State

_orchestrator: Orchestrator | None = None
store = InMemorySessionStore()


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def set_orchestrator_for_tests(orch: Orchestrator | None) -> None:
    """Reset chat orchestrator (used by tests that need a custom MCP client)."""
    global _orchestrator
    _orchestrator = orch


class _OrchestratorProxy:
    """Lazy `routes.orchestrator` so importing the module does not touch Google APIs."""

    def __getattr__(self, name: str):
        return getattr(get_orchestrator(), name)


orchestrator = _OrchestratorProxy()


def post_message(session_id: str, text: str) -> dict:
    session = store.get_or_create(session_id)
    turn = get_orchestrator().handle(text, session)
    store.put(session)
    payload: dict = {
        "messages": turn.messages,
        "state": session.state.value,
        "session": session.to_public_dict(),
        "quick_replies": build_quick_replies(session),
        "booking_summary": build_booking_summary(session, turn),
    }
    if session.state == State.DISCLAIMER_AWAIT_ACK:
        payload["intent_preview"] = build_intent_preview(session)
    else:
        payload["intent_preview"] = []
    return payload
