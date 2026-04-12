from src.domain.calendar_service import BookingDomainService, DomainValidationError
from src.domain.models import BookingAction, TimeSlot


def _slot() -> TimeSlot:
    return TimeSlot(
        start_utc="2026-04-10T09:30:00Z",
        end_utc="2026-04-10T10:00:00Z",
        label_ist="Friday, 10 April 2026, 3:00 PM IST",
    )


def test_hold_command_for_valid_topic_and_slot() -> None:
    service = BookingDomainService()
    decision = service.create_booking_decision(
        topic="KYC/Onboarding",
        selected_slot=_slot(),
        time_preference="tomorrow afternoon",
    )
    assert decision.command.action == BookingAction.HOLD
    assert decision.command.slot is not None
    assert decision.command.topic == "KYC/Onboarding"
    assert decision.command.booking_code


def test_waitlist_command_when_no_slot() -> None:
    service = BookingDomainService()
    decision = service.create_booking_decision(
        topic="SIP/Mandates",
        selected_slot=None,
        time_preference="next week morning",
    )
    assert decision.command.action == BookingAction.WAITLIST
    assert "waitlist" in decision.user_message.lower()
    assert decision.command.slot is None


def test_domain_rejects_pii_payloads() -> None:
    service = BookingDomainService()
    try:
        service.create_booking_decision(
            topic="KYC/Onboarding",
            selected_slot=_slot(),
            time_preference="my email is a@b.com",
        )
        raise AssertionError("Expected DomainValidationError for PII payload")
    except DomainValidationError as exc:
        assert "pii" in str(exc).lower()


def test_domain_rejects_unsupported_topic() -> None:
    service = BookingDomainService()
    try:
        service.create_booking_decision(
            topic="Portfolio rebalancing",
            selected_slot=_slot(),
            time_preference="tomorrow",
        )
        raise AssertionError("Expected DomainValidationError for unsupported topic")
    except DomainValidationError as exc:
        assert "unsupported topic" in str(exc).lower()
