# Phase 2 - Domain Logic + Booking Decisioning

## Required implementation files
- `src/domain/models.py`
- `src/domain/booking_code_generator.py`
- `src/domain/booking_store.py`
- `src/domain/calendar_service.py`

## Required tests
- `tests/unit/test_booking_code_generator.py`
- `tests/unit/test_domain_models.py`
- `tests/integration/test_orchestrator_to_domain.py`

## Checklist
- [ ] Booking code format + collision retry implemented
- [ ] Domain validates no-PII payloads
- [ ] Waitlist branch works when no slots
- [ ] Orchestrator delegates booking decisions to domain

