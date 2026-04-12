# Phase 8 — Hardening and Operations

## Implementation Structure

```
Phases/phase_8_hardening_ops/
├── README.md
├── src/phase8/
│   ├── __init__.py
│   ├── runtime_controls.py      # Turn limits, request size guards, TTL constants
│   ├── session_ttl.py           # Session timestamp tracking and stale-session detection
│   ├── degraded_mode.py         # MCP outage fallback messages and timeout detection
│   └── observability_gate.py    # PII leak scanner and compliance assertions
├── tests/
│   ├── unit/
│   │   ├── test_runtime_controls.py    # Turn limit and request size guard tests
│   │   ├── test_session_ttl.py         # Session TTL and purge tests
│   │   └── test_observability_gate.py  # PII scanner and audit key compliance tests
│   └── integration/
│       ├── test_mcp_timeout_degraded_mode.py  # Failure injection at each MCP stage
│       └── test_pii_audit_gate.py             # End-to-end PII safety verification
```

## Integration Points

Phase 8 modules are integrated into existing layers:
- **Orchestrator** (`phase1/session/orchestrator.py`): Turn limit and request size guards
- **Session Store** (`phase1/session/session_store.py`): TTL timestamp tracking and stale purge
- **Logger** (`phase4/observability/logger.py`): PII redaction (pre-existing, validated by Phase 8 tests)
- **Audit** (`phase4/observability/audit.py`): Forbidden key stripping (pre-existing, validated by Phase 8 tests)

## Operational Documentation

- Operator runbook: `Docs/Runbook.md`

## Checklist

- [x] Runtime limits and TTL cleanup enabled
- [x] Request size guard enforced
- [x] Bounded retries verified (max 3 per MCP operation)
- [x] MCP outage degraded mode documented and validated
- [x] Failure-injection tests pass for Calendar/Docs/Gmail timeouts
- [x] CI/runtime audits prove no PII in persisted outputs
- [x] Operator runbook documented
