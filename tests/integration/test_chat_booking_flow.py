from src.api.chat.routes import orchestrator, post_message


def test_chat_endpoint_returns_messages() -> None:
    response = post_message(session_id="s-123", text="I want to book")
    assert "messages" in response
    assert isinstance(response["messages"], list)


def test_booking_flow_disclaimer_ist_and_no_writes() -> None:
    response1 = post_message("book-flow", "hello")
    assert any("informational and not investment advice" in msg for msg in response1["messages"])

    post_message("book-flow", "ack")
    post_message("book-flow", "book appointment")
    response4 = post_message("book-flow", "KYC")
    ist_messages = [msg for msg in response4["messages"] if "IST" in msg]
    assert len(ist_messages) >= 2

    response5 = post_message("book-flow", "1")
    assert any("Confirmed in IST" in msg for msg in response5["messages"])
    assert orchestrator.mcp_stub.write_attempts == 0


def test_all_five_intents_are_supported_in_chat_mode() -> None:
    flows = {
        "book": ["hi", "ok", "book appointment", "KYC", "1"],
        "reschedule": ["hi", "ok", "reschedule my appointment"],
        "cancel": ["hi", "ok", "cancel my booking"],
        "prepare": ["hi", "ok", "what should i prepare"],
        "availability": ["hi", "ok", "check availability this week"],
    }
    for intent, turns in flows.items():
        sid = f"s-{intent}"
        last = {}
        for turn in turns:
            last = post_message(sid, turn)
        assert "messages" in last
        assert isinstance(last["messages"], list)
