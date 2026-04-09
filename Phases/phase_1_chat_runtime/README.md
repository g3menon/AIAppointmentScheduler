# Phase 1 - Chat Runtime Skeleton + Compliance

## Required implementation files
- `src/api/chat/routes.py`
- `src/session/orchestrator.py`
- `src/session/state.py`
- `src/session/session_store.py`
- `src/domain/calendar_service.py`

## Required tests
- `tests/unit/test_phase1_state_machine.py`
- `tests/integration/test_chat_booking_flow.py`

## Checklist
- [ ] Disclaimer gate enforced
- [ ] PII guard blocks sensitive text
- [ ] Two mock slots offered in IST
- [ ] No external Google writes

