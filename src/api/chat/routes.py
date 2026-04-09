from dataclasses import asdict

from src.session.orchestrator import Orchestrator
from src.session.session_context import SessionContext


orchestrator = Orchestrator()


def post_message(session_id: str, text: str) -> dict:
    session = SessionContext(session_id=session_id)
    turn = orchestrator.handle(text, session)
    return {"messages": turn.messages, "state": session.state.value, "session": asdict(session)}

