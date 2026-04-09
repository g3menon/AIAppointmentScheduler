# Phase 5 - Waitlist + Advice Refusal

## Required implementation files
- `src/session/orchestrator.py` (waitlist + advice branch)
- `src/domain/calendar_service.py` (no-slot behavior)
- `src/config/policy_links.py`

## Required tests
- `tests/integration/test_waitlist_flow.py`
- `tests/integration/test_advice_refusal_flow.py`

## Checklist
- [ ] Empty availability routes to waitlist
- [ ] Advice requests receive static refusal + links
- [ ] Final confirmation repeats IST slot details
- [ ] No PII introduced in waitlist/advice flows

