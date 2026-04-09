from src.session.session_context import SessionContext
from src.session.state import State


def test_default_state_is_greet() -> None:
    session = SessionContext(session_id="s-1")
    assert session.state == State.GREET

