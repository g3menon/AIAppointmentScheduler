"""Shared domain shapes for later phases (Phase 2+)."""

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    BOOK_NEW = "book_new"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    WHAT_TO_PREPARE = "what_to_prepare"
    CHECK_AVAILABILITY = "check_availability"
    UNKNOWN = "unknown"


@dataclass
class TimeSlot:
    start_utc: str
    end_utc: str
    label_ist: str


class BookingAction(str, Enum):
    HOLD = "hold"
    WAITLIST = "waitlist"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"


@dataclass
class BookingCommand:
    action: BookingAction
    booking_code: str
    topic: str | None = None
    slot: TimeSlot | None = None
    notes_entry: str = ""
    email_draft_payload: dict[str, str] = field(default_factory=dict)


@dataclass
class BookingDecision:
    command: BookingCommand
    user_message: str
    offered_slots: list[TimeSlot] = field(default_factory=list)


@dataclass
class BookingRecord:
    code: str
    topic: str
    slot: TimeSlot
    created_at_utc: str
    status: str
    event_id: str = ""
    draft_id: str = ""
