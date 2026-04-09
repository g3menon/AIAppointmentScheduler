# Phase 6 - Secondary Intents

## Required implementation files
- `src/session/orchestrator.py`
- `src/domain/booking_store.py`
- `src/integrations/google_mcp/server.py`

## Required tests
- `tests/integration/test_reschedule_flow.py`
- `tests/integration/test_cancel_flow.py`
- `tests/integration/test_prepare_flow.py`
- `tests/integration/test_availability_flow.py`

## Checklist
- [ ] Reschedule validates code then offers two new slots
- [ ] Cancel validates code then deletes hold and appends cancellation note
- [ ] Prepare intent uses static approved content
- [ ] Availability intent does not create artifacts unless user books

