from .models import TimeSlot

_ALL_SLOTS = [
    TimeSlot(
        start_utc="2026-04-10T09:30:00Z",
        end_utc="2026-04-10T10:00:00Z",
        label_ist="Friday, 10 April 2026, 3:00 PM IST",
    ),
    TimeSlot(
        start_utc="2026-04-10T11:00:00Z",
        end_utc="2026-04-10T11:30:00Z",
        label_ist="Friday, 10 April 2026, 4:30 PM IST",
    ),
    TimeSlot(
        start_utc="2026-04-11T05:30:00Z",
        end_utc="2026-04-11T06:00:00Z",
        label_ist="Saturday, 11 April 2026, 11:00 AM IST",
    ),
    TimeSlot(
        start_utc="2026-04-11T09:30:00Z",
        end_utc="2026-04-11T10:00:00Z",
        label_ist="Saturday, 11 April 2026, 3:00 PM IST",
    ),
    TimeSlot(
        start_utc="2026-04-14T04:00:00Z",
        end_utc="2026-04-14T04:30:00Z",
        label_ist="Monday, 14 April 2026, 9:30 AM IST",
    ),
    TimeSlot(
        start_utc="2026-04-14T07:00:00Z",
        end_utc="2026-04-14T07:30:00Z",
        label_ist="Monday, 14 April 2026, 12:30 PM IST",
    ),
]


class MockCalendarService:
    """Returns up to two available slots, excluding any that already have holds."""

    def __init__(self) -> None:
        self._booked_utc: set[str] = set()

    def mark_booked(self, start_utc: str) -> None:
        self._booked_utc.add(start_utc)

    def release(self, start_utc: str) -> None:
        self._booked_utc.discard(start_utc)

    def find_two_slots(self, preferred_date_ist: str | None = None) -> list[TimeSlot]:
        available = [s for s in _ALL_SLOTS if s.start_utc not in self._booked_utc]
        return available[:2]
