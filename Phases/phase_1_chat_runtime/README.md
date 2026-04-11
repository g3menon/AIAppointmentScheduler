# Phase 1 - Chat Runtime Skeleton + Compliance

All Phase 1 **implementation and tests** live in **this folder**. The Python package name is **`phase1`** under `src/phase1/`.

## Layout

```
Phases/phase_1_chat_runtime/
  src/phase1/
    api/chat/routes.py
    session/          # orchestrator, state, session_store, prompts, pii_guard, topic_catalog
    domain/           # models (Intent, Topic, TimeSlot), MockCalendarService
    integrations/mcp/recording_client.py   # in-memory call recorder (pytest only)
  tests/
    unit/
    integration/
    e2e/
  pytest.ini
```

## Run tests

From **repo root** (recommended; uses root `pytest.ini`):

```bash
pytest Phases/phase_1_chat_runtime/tests
```

Or from **this directory**:

```bash
cd Phases/phase_1_chat_runtime
pytest
```

## Root integration

- `src/api/chat/routes.py` at the repo root **re-exports** `post_message`, `orchestrator`, `get_orchestrator`, `set_orchestrator_for_tests`, and `store` from `phase1.api.chat.routes`.
- **Real Google MCP** is implemented in `src/integrations/google_mcp/client.py` (`GoogleMcpClient`). The orchestrator calls it after booking confirmation; `pytest` substitutes `RecordingGoogleMcpClient` when `PYTEST_CURRENT_TEST` is set.

## Checklist

- [x] Disclaimer gate enforced (appears before any booking progression)
- [x] PII guard blocks sensitive text (email, phone, account, PAN, Aadhaar, DOB)
- [x] Investment-advice refusal with redirect
- [x] Topic whitelist with re-prompt on unsupported topic
- [x] Full state machine per Architecture §11.5
- [x] All 5 intents supported in chat
- [x] Two mock slots in IST; explicit yes/no confirmation
- [x] Real Google MCP trio on confirmed booking (Calendar hold, Docs append, Gmail draft); tests use in-memory recorder
