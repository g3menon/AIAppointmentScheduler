from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable

from .booking_code_generator import BookingCodeGenerator
from .booking_store import InMemoryBookingStore
from .models import BookingAction, BookingCommand, BookingDecision, BookingRecord, TimeSlot

ALLOWED_TOPICS = {
    "KYC/Onboarding",
    "SIP/Mandates",
    "Statements/Tax Docs",
    "Withdrawals & Timelines",
    "Account Changes/Nominee",
}

_PHONE = re.compile(r"\b\d{10}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_ACCOUNT = re.compile(r"\b(?:\d[ -]?){12,16}\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_AADHAAR = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_DOB = re.compile(
    r"\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"
    r"|\b(?:\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b"
)
_PII_PATTERNS = (_PHONE, _EMAIL, _ACCOUNT, _PAN, _AADHAAR, _DOB)


class BookingNotFoundError(ValueError):
    """Raised when a booking code cannot be found in the store."""


def _contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PII_PATTERNS)


class DomainValidationError(ValueError):
    """Raised when a command request violates domain policy."""


class BookingDomainService:
    def __init__(
        self,
        store: InMemoryBookingStore | None = None,
        pii_detector: Callable[[str], bool] = _contains_pii,
    ) -> None:
        self.store = store or InMemoryBookingStore()
        self._pii_detector = pii_detector
        self.last_command: BookingCommand | None = None

    def create_booking_decision(
        self,
        *,
        topic: str,
        selected_slot: TimeSlot | None,
        time_preference: str,
    ) -> BookingDecision:
        self._validate_topic(topic)
        self._validate_text("time_preference", time_preference)

        if selected_slot is None:
            command = self._build_waitlist_command(topic=topic, time_preference=time_preference)
            return self._emit(
                BookingDecision(
                    command=command,
                    user_message=(
                        "No matching advisor slots are available right now. "
                        f"You have been added to the waitlist with code {command.booking_code}."
                    ),
                )
            )

        code = self._new_code()
        command = BookingCommand(
            action=BookingAction.HOLD,
            booking_code=code,
            topic=topic,
            slot=selected_slot,
            notes_entry=f"{topic} | {selected_slot.label_ist} | {code} | tentative_hold",
            email_draft_payload={
                "subject": f"Advisor pre-booking {code}",
                "body": (
                    f"Topic: {topic}\n"
                    f"Slot (IST label): {selected_slot.label_ist}\n"
                    f"Booking code: {code}\n"
                    "This is a draft only — approval required before send.\n"
                ),
            },
        )
        return self._emit(
            BookingDecision(
                command=command,
                user_message=(
                    f"Your slot is locked for {selected_slot.label_ist}. "
                    f"Booking code: {command.booking_code}."
                ),
            )
        )

    def save_confirmed_booking(
        self,
        *,
        code: str,
        topic: str,
        slot: TimeSlot,
        event_id: str = "",
        draft_id: str = "",
    ) -> BookingRecord:
        record = BookingRecord(
            code=code,
            topic=topic,
            slot=slot,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            status="tentative",
            event_id=event_id,
            draft_id=draft_id,
        )
        self.store.save(record)
        return record

    def lookup_booking(self, code: str) -> BookingRecord:
        self._validate_booking_code(code)
        record = self.store.get_by_code(code)
        if record is None:
            raise BookingNotFoundError(f"No booking found for code {code}")
        if record.status == "cancelled":
            raise BookingNotFoundError(f"Booking {code} has already been cancelled")
        return record

    def create_reschedule_decision(
        self,
        *,
        booking_code: str,
        new_slot: TimeSlot | None = None,
    ) -> BookingDecision:
        self._validate_booking_code(booking_code)
        record = self.store.get_by_code(booking_code)
        topic = record.topic if record else "General"
        if new_slot is not None:
            new_code = self._new_code()
            command = BookingCommand(
                action=BookingAction.RESCHEDULE,
                booking_code=new_code,
                topic=topic,
                slot=new_slot,
                notes_entry=f"{topic} | {new_slot.label_ist} | {new_code} | reschedule_from_{booking_code}",
                email_draft_payload={
                    "subject": f"Advisor reschedule {new_code} (was {booking_code})",
                    "body": (
                        f"Topic: {topic}\n"
                        f"New slot (IST): {new_slot.label_ist}\n"
                        f"New booking code: {new_code}\n"
                        f"Previous code: {booking_code}\n"
                        "This is a draft only — approval required before send.\n"
                    ),
                },
            )
            return self._emit(
                BookingDecision(
                    command=command,
                    user_message=(
                        f"Your appointment has been rescheduled to {new_slot.label_ist}. "
                        f"New booking code: {new_code}."
                    ),
                )
            )
        command = BookingCommand(
            action=BookingAction.RESCHEDULE,
            booking_code=booking_code,
            notes_entry=f"reschedule_requested | {booking_code}",
        )
        return self._emit(
            BookingDecision(
                command=command,
                user_message="Reschedule request captured. We will offer alternate slots next.",
            )
        )

    def create_cancel_decision(self, *, booking_code: str) -> BookingDecision:
        self._validate_booking_code(booking_code)
        record = self.store.get_by_code(booking_code)
        topic = record.topic if record else "General"
        slot_label = record.slot.label_ist if record and record.slot else "N/A"
        command = BookingCommand(
            action=BookingAction.CANCEL,
            booking_code=booking_code,
            topic=topic,
            notes_entry=f"{topic} | {slot_label} | {booking_code} | cancel_confirmed",
        )
        return self._emit(
            BookingDecision(
                command=command,
                user_message="Cancellation request captured.",
            )
        )

    def mark_cancelled(self, code: str) -> None:
        self.store.update_status(code, "cancelled")

    def _build_waitlist_command(self, *, topic: str, time_preference: str) -> BookingCommand:
        code = self._new_code()
        return BookingCommand(
            action=BookingAction.WAITLIST,
            booking_code=code,
            topic=topic,
            notes_entry=f"{topic} | {time_preference} | {code} | waitlist",
            email_draft_payload={
                "subject": f"Advisor waitlist request {code}",
                "body": (
                    f"Topic: {topic}\n"
                    f"Preferred time: {time_preference}\n"
                    f"Booking code: {code}\n"
                    "This is a draft only — approval required before send.\n"
                ),
            },
        )

    def _new_code(self) -> str:
        return BookingCodeGenerator(exists_fn=self.store.exists).generate()

    def _validate_topic(self, topic: str) -> None:
        if topic not in ALLOWED_TOPICS:
            raise DomainValidationError(f"Unsupported topic: {topic}")
        self._validate_text("topic", topic)

    def _validate_booking_code(self, code: str) -> None:
        if not code:
            raise DomainValidationError("Booking code is required")
        self._validate_text("booking_code", code)

    def _validate_text(self, field_name: str, value: str) -> None:
        if self._pii_detector(value):
            raise DomainValidationError(f"PII-like value detected in {field_name}")

    def _emit(self, decision: BookingDecision) -> BookingDecision:
        self.last_command = decision.command
        return decision
