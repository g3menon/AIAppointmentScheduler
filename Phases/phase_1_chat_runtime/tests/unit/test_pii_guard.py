"""Unit tests — PII guard per Architecture.md §11.10 denylist."""

from phase1.session.pii_guard import contains_pii


# ── positive detections ──────────────────────────────────────────────


def test_detects_email() -> None:
    assert contains_pii("Email me at user@example.com")


def test_detects_phone() -> None:
    assert contains_pii("Call me at 9876543210")


def test_detects_account_number() -> None:
    assert contains_pii("account 1234 5678 1234")


def test_detects_pan() -> None:
    assert contains_pii("My PAN is ABCDE1234F")


def test_detects_aadhaar() -> None:
    assert contains_pii("Aadhaar 1234 5678 9012")


def test_detects_dob_slash() -> None:
    assert contains_pii("born on 15/06/1990")


def test_detects_dob_dash() -> None:
    assert contains_pii("DOB is 1990-06-15")


# ── safe text (no false positives) ───────────────────────────────────


def test_allows_booking_request() -> None:
    assert not contains_pii("I want to book a KYC session tomorrow")


def test_allows_slot_selection() -> None:
    assert not contains_pii("I'll take slot 1")


def test_allows_topic_name() -> None:
    assert not contains_pii("SIP mandates discussion")
