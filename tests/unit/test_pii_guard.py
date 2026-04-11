from src.session.pii_guard import contains_pii


def test_pii_guard_detects_email_phone_and_account_patterns() -> None:
    assert contains_pii("Email me at user@example.com")
    assert contains_pii("Call me at 9876543210")
    assert contains_pii("account 1234 5678 1234")


def test_pii_guard_allows_non_sensitive_text() -> None:
    assert not contains_pii("I want to book a KYC session tomorrow")
