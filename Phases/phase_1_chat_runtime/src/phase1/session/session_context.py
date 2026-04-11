from dataclasses import dataclass, field
from typing import Optional

from phase1.domain.models import TimeSlot

from .state import State


@dataclass
class SessionContext:
    session_id: str
    state: State = State.GREET
    disclaimer_acknowledged: bool = False
    intent: Optional[str] = None
    topic: Optional[str] = None
    time_preference: Optional[str] = None
    pending_booking_code: Optional[str] = None
    booking_code: Optional[str] = None
    last_mcp_error: Optional[str] = None
    turn_count: int = 0
    advice_redirect_count: int = 0
    offered_slots: list[str] = field(default_factory=list)
    offered_slot_choices: list[TimeSlot] = field(default_factory=list)
    selected_slot: Optional[str] = None
    selected_timeslot: Optional[TimeSlot] = None
