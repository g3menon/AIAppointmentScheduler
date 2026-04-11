import pytest


@pytest.fixture(autouse=True)
def _reset_phase1_chat_routes() -> None:
    import phase1.api.chat.routes as chat_routes

    chat_routes.store.clear()
    chat_routes.set_orchestrator_for_tests(None)
    yield
