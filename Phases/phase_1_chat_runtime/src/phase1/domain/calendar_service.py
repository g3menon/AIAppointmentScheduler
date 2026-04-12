from datetime import date, datetime, timedelta, timezone

from .models import TimeSlot

_IST_OFFSET = timedelta(hours=5, minutes=30)
_IST = timezone(_IST_OFFSET)

_SLOT_OFFSETS: list[tuple[int, int, int]] = [
    (1, 10, 0),
    (1, 15, 0),
    (2, 9, 30),
    (2, 14, 0),
    (3, 11, 0),
    (3, 16, 0),
]


def _generate_slots(today: date | None = None) -> list[TimeSlot]:
    """Build mock slots starting from *today* + offset days, always in the future."""
    base = today or date.today()
    slots: list[TimeSlot] = []
    for day_offset, hour_ist, minute_ist in _SLOT_OFFSETS:
        d = base + timedelta(days=day_offset)
        ist_dt = datetime(d.year, d.month, d.day, hour_ist, minute_ist, tzinfo=_IST)
        utc_dt = ist_dt.astimezone(timezone.utc)
        end_utc = utc_dt + timedelta(minutes=30)
        raw = ist_dt.strftime("%A, %d %B %Y, %I:%M %p IST")
        parts = raw.split(", ")
        if len(parts) >= 2:
            parts[1] = parts[1].lstrip("0")
        label = ", ".join(parts)
        label = label.replace(", 0", ", ").replace(" 0", " ")
        if ", " in label:
            time_part = label.rsplit(", ", 1)[-1]
            if time_part.startswith("0"):
                label = label.rsplit(", ", 1)[0] + ", " + time_part.lstrip("0")
        slots.append(TimeSlot(
            start_utc=utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_utc=end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            label_ist=label,
        ))
    return slots


class MockCalendarService:
    """Returns up to two available slots, excluding any that already have holds."""

    def __init__(self, today: date | None = None) -> None:
        self._booked_utc: set[str] = set()
        self._today = today

    def mark_booked(self, start_utc: str) -> None:
        self._booked_utc.add(start_utc)

    def release(self, start_utc: str) -> None:
        self._booked_utc.discard(start_utc)

    def find_two_slots(self, preferred_date_ist: str | None = None) -> list[TimeSlot]:
        all_slots = _generate_slots(self._today)
        available = [s for s in all_slots if s.start_utc not in self._booked_utc]
        return available[:2]
