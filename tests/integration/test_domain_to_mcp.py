from src.integrations.google_mcp.booking_mcp_executor import BookingMcpBundle, run_booking_mcp_triplet
from src.integrations.google_mcp.fakes import FakeGoogleMcpClient
from src.integrations.google_mcp.mcp_tool_dispatch import _IDEMPOTENT_RESULTS
from src.integrations.google_mcp.settings import GoogleMcpSettings


def _settings() -> GoogleMcpSettings:
    return GoogleMcpSettings(
        calendar_id="primary",
        prebooking_doc_id="doc-123",
        advisor_email_to="advisor@example.com",
        idempotency_namespace="booking",
        auth_mode="oauth",
    )


def _bundle(code: str) -> BookingMcpBundle:
    return BookingMcpBundle(
        calendar_title=f"Advisor Q&A - KYC/Onboarding - {code}",
        start_utc="2026-04-12T09:00:00Z",
        end_utc="2026-04-12T09:30:00Z",
        calendar_id="primary",
        calendar_idempotency_key=f"booking:{code}:calendar",
        doc_id="doc-123",
        doc_line=f"KYC/Onboarding | Friday, 12 April 2026, 2:30 PM IST | {code} | tentative_hold",
        doc_idempotency_key=f"booking:{code}:doc",
        gmail_to="advisor@example.com",
        gmail_subject=f"Advisor pre-booking {code}",
        gmail_body="Draft only - approval pending",
    )


def test_domain_bundle_maps_to_mcp_triplet() -> None:
    _IDEMPOTENT_RESULTS.clear()
    client = FakeGoogleMcpClient(settings=_settings())
    result = run_booking_mcp_triplet(client, _bundle("AB-C123"))
    assert result.event_id.startswith("fake_event_")
    assert result.doc_reply.startswith("fake_doc_reply_")
    assert result.draft_id.startswith("fake_draft_")
    assert len(client.calendar_holds) == 1
    assert len(client.doc_appends) == 1
    assert len(client.gmail_drafts) == 1


def test_retry_does_not_duplicate_artifacts() -> None:
    _IDEMPOTENT_RESULTS.clear()
    client = FakeGoogleMcpClient(settings=_settings(), fail_next_doc=1)
    bundle = _bundle("ZX-Q111")
    first = run_booking_mcp_triplet(client, bundle)
    attempts_after_first = client.write_attempts
    second = run_booking_mcp_triplet(client, bundle)
    assert first == second
    assert client.write_attempts == attempts_after_first
    assert len(client.calendar_holds) == 1
    assert len(client.doc_appends) == 1
    assert len(client.gmail_drafts) == 1
