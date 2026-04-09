from src.api.chat.routes import post_message


def test_chat_endpoint_returns_messages() -> None:
    response = post_message(session_id="s-123", text="I want to book")
    assert "messages" in response
    assert isinstance(response["messages"], list)

