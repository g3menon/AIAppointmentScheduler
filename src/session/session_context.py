from dataclasses import dataclass, field
from typing import Optional

from .state import State


@dataclass
class SessionContext:
    session_id: str
    state: State = State.GREET
    disclaimer_acknowledged: bool = False
    intent: Optional[str] = None
    pending_booking_code: Optional[str] = None
    last_mcp_error: Optional[str] = None
    turn_count: int = 0
    advice_redirect_count: int = 0
    offered_slots: list[dict] = field(default_factory=list)
    selected_slot: Optional[dict] = None

