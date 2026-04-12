# Phase 3 - NLU Wiring + FastMCP Integration

## Required implementation files
- `src/nlu/engine.py`
- `src/nlu/resolvers.py`
- `src/integrations/google_mcp/server.py`
- `src/integrations/google_mcp/backing_services.py`
- `src/integrations/google_mcp/fakes.py`

## Required tests
- `tests/unit/test_nlu_resolvers.py`
- `tests/unit/test_google_mcp_contracts.py`
- `tests/integration/test_domain_to_mcp.py`

## Checklist
- [x] Structured NLU output schema enforced
- [x] FastMCP tools exposed for Calendar/Docs/Gmail
- [x] Fake MCP integrations used by CI
- [x] Idempotency and retry behavior covered by tests

