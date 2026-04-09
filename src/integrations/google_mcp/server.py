from fastmcp import FastMCP

mcp = FastMCP("advisor-booking")


@mcp.tool()
def calendar_create_hold(
    title: str,
    start_utc: str,
    end_utc: str,
    calendar_id: str,
    idempotency_key: str,
) -> str:
    return "stub_event_id"


@mcp.tool()
def calendar_delete_hold(event_id: str, calendar_id: str) -> None:
    return None


@mcp.tool()
def docs_append_prebooking(doc_id: str, line: str, idempotency_key: str) -> None:
    return None


@mcp.tool()
def gmail_create_draft(to: str, subject: str, body_markdown: str) -> str:
    return "stub_draft_id"

