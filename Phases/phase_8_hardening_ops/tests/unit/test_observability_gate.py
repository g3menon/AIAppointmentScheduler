"""Unit tests for the observability compliance gate."""

import pytest

from phase8.observability_gate import (
    PIILeakError,
    assert_audit_keys_clean,
    assert_payload_pii_free,
    scan_for_pii,
)


class TestScanForPII:
    def test_detects_email(self) -> None:
        assert "email" in scan_for_pii("contact me at user@example.com")

    def test_detects_phone(self) -> None:
        assert "phone" in scan_for_pii("call 9876543210 now")

    def test_detects_pan(self) -> None:
        assert "pan" in scan_for_pii("my PAN is ABCDE1234F")

    def test_detects_aadhaar(self) -> None:
        assert "aadhaar" in scan_for_pii("aadhaar 1234 5678 9012")

    def test_clean_text_returns_empty(self) -> None:
        assert scan_for_pii("book a new appointment") == []

    def test_redacted_text_is_clean(self) -> None:
        assert scan_for_pii("[REDACTED_EMAIL] and [REDACTED_PHONE]") == []


class TestAssertPayloadPIIFree:
    def test_passes_on_clean_payload(self) -> None:
        assert_payload_pii_free({
            "session_id": "s1",
            "stage": "book_confirm",
            "intent": "book_new",
            "booking_code": "AB-C123",
            "error_type": "none",
            "latency_ms": 10,
        })

    def test_raises_on_pii_in_nested_dict(self) -> None:
        with pytest.raises(PIILeakError, match="email"):
            assert_payload_pii_free({
                "details": {"user_email": "john@example.com"},
            })

    def test_raises_on_pii_in_list(self) -> None:
        with pytest.raises(PIILeakError, match="phone"):
            assert_payload_pii_free({
                "notes": ["call 9876543210"],
            })


class TestAssertAuditKeysClean:
    def test_passes_on_safe_keys(self) -> None:
        assert_audit_keys_clean({
            "calendar_status": "success",
            "docs_status": "failed",
            "booking_code": "AB-123",
        })

    def test_raises_on_raw_user_text(self) -> None:
        with pytest.raises(PIILeakError, match="raw_user_text"):
            assert_audit_keys_clean({
                "calendar_status": "success",
                "raw_user_text": "my email is john@example.com",
            })

    def test_raises_on_transcript(self) -> None:
        with pytest.raises(PIILeakError, match="transcript"):
            assert_audit_keys_clean({
                "transcript": "secret convo",
            })
