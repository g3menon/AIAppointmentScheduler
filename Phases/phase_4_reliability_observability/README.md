# Phase 4 - Reliability, Observability, Recovery

## Required implementation files
- `src/session/orchestrator.py` (error recovery transitions)
- `src/integrations/google_mcp/backing_services.py` (timeouts/retry)
- `src/observability/logger.py`
- `src/observability/audit.py`

## Required tests
- `tests/unit/test_logging_redaction.py`
- `tests/integration/test_partial_failure_recovery.py`

## Checklist
- [ ] Structured logs include correlation fields
- [ ] Redaction-before-write enforced
- [ ] Partial-failure compensation paths implemented
- [ ] User-safe fallback responses verified

