# Phase 6 - Secondary Intents (Full Subgraphs)

## Objective
Implement full secondary intent subgraphs: reschedule, cancel, prepare, and availability — replacing Phase 1 stubs with real store-backed flows, MCP operations, and policy-safe behavior.

## Implementation files modified
- `Phases/phase_1_chat_runtime/src/phase1/session/orchestrator.py` — full reschedule/cancel subgraphs with MCP operations
- `Phases/phase_1_chat_runtime/src/phase1/session/state.py` — added `RESCHEDULE_CONFIRM` state
- `Phases/phase_1_chat_runtime/src/phase1/session/prompt_templates.py` — new templates for reschedule/cancel/prepare/availability flows
- `Phases/phase_1_chat_runtime/src/phase1/api/chat/ui_hints.py` — quick replies for new reschedule states
- `Phases/phase_1_chat_runtime/src/phase1/integrations/mcp/recording_client.py` — added `calendar_delete_hold` recording
- `src/domain/calendar_service.py` — `BookingDomainService` with store-backed lookup, save, cancel, reschedule
- `src/domain/booking_store.py` — added `delete` method
- `src/domain/models.py` — `BookingRecord` with `event_id` and `draft_id` fields
- `src/integrations/google_mcp/server.py` — added `calendar_delete_hold` FastMCP tool
- `src/integrations/google_mcp/client.py` — added `delete_calendar_hold` on `GoogleMcpClient`
- `src/integrations/google_mcp/mcp_tool_dispatch.py` — dispatch for `calendar_delete_hold`
- `src/integrations/google_mcp/backing_services.py` — re-export `CalendarDeleteRequest`
- `Phases/phase_3_nlu_and_mcp/src/phase3/integrations/contracts.py` — `CalendarDeleteRequest` contract

## Tests (23 total)
- `tests/integration/test_reschedule_flow.py` (6 tests)
- `tests/integration/test_cancel_flow.py` (6 tests)
- `tests/integration/test_prepare_flow.py` (6 tests)
- `tests/integration/test_availability_flow.py` (5 tests)

## Checklist
- [x] Reschedule validates code against booking store then offers two new slots
- [x] Reschedule deletes old calendar hold, creates new MCP trio, marks old booking cancelled
- [x] Cancel validates code against store then deletes hold and appends cancellation note
- [x] Prepare intent uses static approved content (generic + topic-specific)
- [x] Availability intent shows slots without creating artifacts unless user books
- [x] Booking-code-only identity flow (no PII capture for reschedule/cancel)
- [x] All 107 tests pass (23 Phase 6 + 84 existing regression)
