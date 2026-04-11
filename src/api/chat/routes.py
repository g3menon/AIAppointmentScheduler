from dataclasses import asdict

from src.session.orchestrator import Orchestrator
from src.session.session_store import InMemorySessionStore

orchestrator = Orchestrator()
store = InMemorySessionStore()


def post_message(session_id: str, text: str) -> dict:
    session = store.get_or_create(session_id)
    turn = orchestrator.handle(text, session)
    store.put(session)
    return {"messages": turn.messages, "state": session.state.value, "session": asdict(session)}
