# Phase 1 - Chat Runtime Skeleton + Compliance

Implement and run these at the **repo root** (see `src/`, `tests/`). This folder only tracks scope.

## Required implementation files
- `src/api/chat/routes.py`
- `src/session/orchestrator.py`
- `src/session/state.py`
- `src/session/session_store.py`
- `src/domain/calendar_service.py`
- `src/session/pii_guard.py`
- `src/session/topic_catalog.py`
- `src/integrations/mcp/stub_client.py`

## Required tests
- `tests/unit/test_phase1_state_machine.py`
- `tests/integration/test_chat_booking_flow.py`
- `tests/unit/test_pii_guard.py`
- `tests/unit/test_topic_catalog.py`

## Checklist
- [x] Disclaimer gate enforced
- [x] PII guard blocks sensitive text
- [x] Two mock slots offered in IST
- [x] No external Google writes

