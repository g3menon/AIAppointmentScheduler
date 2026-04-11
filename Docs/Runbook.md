# Operations runbook

Use this with Phase 8 hardening (`Phases/phase_8_hardening_ops/README.md`).

## MCP / Google outage (degraded mode)

- Chat runtime should surface user-safe messages when Calendar, Docs, or Gmail tools fail or time out.
- Retry only transient errors; do not duplicate holds (idempotency keys per `Docs/Architecture.md` §11.2).
- Log `session_id`, `correlation_id`, tool name, and error class; never log raw user text.

## Session lifecycle

- Enforce session TTL and cleanup for in-memory stores in non-production; document limits for production.

## PII and compliance

- `PiiGuard` runs before NLU/state transitions; redact before any log or artifact write (`Docs/Architecture.md` §11.10).
