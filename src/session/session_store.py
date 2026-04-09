from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .session_context import SessionContext


@dataclass
class SessionEnvelope:
    context: SessionContext
    updated_at_utc: datetime


class InMemorySessionStore:
    def __init__(self, ttl_minutes: int = 30) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, SessionEnvelope] = {}

    def get(self, session_id: str) -> SessionContext | None:
        envelope = self._sessions.get(session_id)
        if not envelope:
            return None
        if datetime.now(timezone.utc) - envelope.updated_at_utc > self._ttl:
            self._sessions.pop(session_id, None)
            return None
        return envelope.context

    def put(self, context: SessionContext) -> None:
        self._sessions[context.session_id] = SessionEnvelope(
            context=context,
            updated_at_utc=datetime.now(timezone.utc),
        )

