from .models import TimeSlot


class MockCalendarService:
    def find_two_slots(self, preferred_date_ist: str | None = None) -> list[TimeSlot]:
        slots = [
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
        ]
        return slots[:2]
