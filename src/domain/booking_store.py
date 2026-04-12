from .models import BookingRecord


class InMemoryBookingStore:
    def __init__(self) -> None:
        self._records: dict[str, BookingRecord] = {}

    def save(self, record: BookingRecord) -> None:
        self._records[record.code] = record

    def get_by_code(self, code: str) -> BookingRecord | None:
        return self._records.get(code)

    def exists(self, code: str) -> bool:
        return code in self._records

    def update_status(self, code: str, status: str) -> None:
        record = self._records.get(code)
        if record:
            record.status = status

