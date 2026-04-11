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

    def to_public_dict(self) -> dict:
        """JSON-serializable view (HTTP UI, logs); keeps TimeSlot as plain dicts."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "disclaimer_acknowledged": self.disclaimer_acknowledged,
            "intent": self.intent,
            "topic": self.topic,
            "time_preference": self.time_preference,
            "pending_booking_code": self.pending_booking_code,
            "booking_code": self.booking_code,
            "last_mcp_error": self.last_mcp_error,
            "turn_count": self.turn_count,
            "advice_redirect_count": self.advice_redirect_count,
            "offered_slots": list(self.offered_slots),
            "offered_slot_choices": [
                {"start_utc": s.start_utc, "end_utc": s.end_utc, "label_ist": s.label_ist}
                for s in self.offered_slot_choices
            ],
            "selected_slot": self.selected_slot,
            "selected_timeslot": (
                {
                    "start_utc": self.selected_timeslot.start_utc,
                    "end_utc": self.selected_timeslot.end_utc,
                    "label_ist": self.selected_timeslot.label_ist,
                }
                if self.selected_timeslot
                else None
            ),
        }
