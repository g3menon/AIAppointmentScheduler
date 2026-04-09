from dataclasses import dataclass
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


@dataclass
class BookingRecord:
    code: str
    topic: str
    slot: TimeSlot
    created_at_utc: str
    status: str

