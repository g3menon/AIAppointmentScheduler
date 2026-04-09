from dataclasses import dataclass, field

from .session_context import SessionContext


@dataclass
class AgentTurn:
    messages: list[str] = field(default_factory=list)
    side_effects: list[dict] = field(default_factory=list)


class Orchestrator:
    """Single text-in/text-out runtime contract used by chat and voice."""

    def handle(self, user_text: str, session: SessionContext) -> AgentTurn:
        # Placeholder implementation for phase scaffolding.
        # Business flow and policy gates are implemented phase-by-phase.
        session.turn_count += 1
        return AgentTurn(messages=[f"[stub] Received: {user_text}"])

