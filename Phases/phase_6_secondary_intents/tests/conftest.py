import pytest


@pytest.fixture(autouse=True)
def _reset_phase1_chat_routes() -> None:
    from src.integrations.google_mcp.mcp_tool_dispatch import _IDEMPOTENT_RESULTS

    import phase1.api.chat.routes as chat_routes

    chat_routes.store.clear()
    chat_routes.set_orchestrator_for_tests(None)
    _IDEMPOTENT_RESULTS.clear()
    yield
