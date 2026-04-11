from src.session.session_context import SessionContext


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}

    def get_or_create(self, session_id: str) -> SessionContext:
        existing = self._sessions.get(session_id)
        if existing:
            return existing
        created = SessionContext(session_id=session_id)
        self._sessions[session_id] = created
        return created

    def put(self, context: SessionContext) -> None:
        self._sessions[context.session_id] = context
