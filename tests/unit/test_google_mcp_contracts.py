from src.integrations.google_mcp.backing_services import McpContractError
from src.integrations.google_mcp.fakes import FakeGoogleMcpClient
from src.integrations.google_mcp.mcp_tool_dispatch import _IDEMPOTENT_RESULTS, dispatch_mcp_tool
from src.integrations.google_mcp.settings import GoogleMcpSettings


def _settings() -> GoogleMcpSettings:
    return GoogleMcpSettings(
        calendar_id="primary",
        prebooking_doc_id="doc-123",
        advisor_email_to="advisor@example.com",
        idempotency_namespace="booking",
        auth_mode="oauth",
    )


def test_calendar_contract_enforces_title_format() -> None:
    _IDEMPOTENT_RESULTS.clear()
    client = FakeGoogleMcpClient(settings=_settings())
    try:
        dispatch_mcp_tool(
            client,
            "calendar_create_hold",
            {
                "title": "Bad title",
                "start_utc": "2026-04-12T09:00:00Z",
                "end_utc": "2026-04-12T09:30:00Z",
                "calendar_id": "primary",
                "idempotency_key": "booking:AB-C123:calendar",
            },
        )
        raise AssertionError("Expected contract validation error for invalid title")
    except McpContractError as exc:
        assert "Advisor Q&A" in str(exc)


def test_retry_and_idempotency_prevent_duplicate_side_effects() -> None:
    _IDEMPOTENT_RESULTS.clear()
    client = FakeGoogleMcpClient(settings=_settings(), fail_next_calendar=1)
    args = {
        "title": "Advisor Q&A - KYC/Onboarding - AB-C123",
        "start_utc": "2026-04-12T09:00:00Z",
        "end_utc": "2026-04-12T09:30:00Z",
        "calendar_id": "primary",
        "idempotency_key": "booking:AB-C123:calendar",
    }
    first = dispatch_mcp_tool(client, "calendar_create_hold", args)
    second = dispatch_mcp_tool(client, "calendar_create_hold", args)
    assert first == second
    assert len(client.calendar_holds) == 1
    assert client.write_attempts == 2  # one transient failure + one success


def test_gmail_is_draft_only_surface() -> None:
    _IDEMPOTENT_RESULTS.clear()
    client = FakeGoogleMcpClient(settings=_settings())
    draft_id = dispatch_mcp_tool(
        client,
        "gmail_create_draft",
        {
            "to": "advisor@example.com",
            "subject": "Advisor pre-booking AB-C123",
            "body_markdown": "Draft only",
        },
    )
    assert draft_id
    assert len(client.gmail_drafts) == 1
    assert not hasattr(client, "send_email")
