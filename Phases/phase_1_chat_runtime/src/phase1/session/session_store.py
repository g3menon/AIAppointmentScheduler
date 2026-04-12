from phase1.session.session_context import SessionContext
from phase8.session_ttl import SessionTimestamps


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._timestamps = SessionTimestamps()

    def get_or_create(self, session_id: str) -> SessionContext:
        existing = self._sessions.get(session_id)
        if existing:
            self._timestamps.touch(session_id)
            return existing
        created = SessionContext(session_id=session_id)
        self._sessions[session_id] = created
        self._timestamps.touch(session_id)
        return created

    def put(self, context: SessionContext) -> None:
        self._sessions[context.session_id] = context
        self._timestamps.touch(context.session_id)

    def purge_stale(self, ttl_seconds: int | None = None) -> list[str]:
        """Remove sessions idle longer than *ttl_seconds* and return their IDs."""
        stale = self._timestamps.stale_ids(ttl_seconds)
        for sid in stale:
            self._sessions.pop(sid, None)
            self._timestamps.remove(sid)
        return stale

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def clear(self) -> None:
        self._sessions.clear()
        self._timestamps.clear()
