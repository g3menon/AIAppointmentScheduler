# AI Appointment Scheduler - Rules & Execution Guardrails (Chat-First)

This document enforces how phases must be implemented against `Docs/Architecture.md`.

---

## 1) General Rules (All Phases)

| # | Rule | Why |
|---|------|-----|
| G1 | **Chat-first delivery is mandatory.** Core functionality must be implemented and validated in chat mode before voice work starts. | Faster iteration, easier debugging, cleaner architecture. |
| G2 | **Core runtime boundary must remain stable.** `Conversation Orchestration -> NLU/LLM -> Domain -> MCP` is the authoritative path. | Prevents logic duplication and drift. |
| G3 | **Voice is adapter-only.** STT/TTS can transform input/output only; they cannot contain domain or integration logic. | Ensures chat and voice parity. |
| G4 | **No PII collection in interaction.** Never ask/store phone, email, account number, or personal identifiers in chat/voice flow or logs. | Compliance requirement. |
| G5 | **Mandatory disclaimer + refusal policy.** "Informational, not investment advice" disclaimer and safe refusal behavior are non-negotiable. | Risk and compliance control. |
| G6 | **Only MCP layer can perform Google writes.** No direct Calendar/Docs/Gmail calls outside integration layer. | Keeps integration concerns isolated. |
| G7 | **Gmail is draft-only.** No direct send behavior in any phase. | Human approval gate. |
| G8 | **Idempotency for side effects is required.** Retries must not create duplicate holds/log entries/drafts. | Reliability and data correctness. |
| G9 | **Timezone clarity.** Use IST default and repeat date/time before confirmation. | Prevents scheduling mistakes. |
| G10 | **Structured logging required.** Logs must include session trace fields and never include secrets or PII. | Auditability and safe operations. |

---

## 2) Phase 1 Rules - Chat Runtime Skeleton + Compliance

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P1.1 | Build chat interface first. | Text input and text response path is available via CLI/web/API handler. |
| P1.2 | Implement orchestrator state machine. | Required stages: greet, disclaimer, capture, offer, confirm, complete. |
| P1.3 | Support all 5 intents in chat mode. | book, reschedule, cancel, what to prepare, availability. |
| P1.4 | Enforce topic whitelist and no-PII prompts. | Unsupported topics and sensitive user inputs are handled safely. |
| P1.5 | Offer exactly two mock slots in IST. | No real external dependency in this phase. |
| P1.6 | Disable all external writes. | Calendar/Docs/Gmail interactions remain stubbed. |

### Definition of Done (Phase 1)
- Chat conversation supports all five intents end-to-end.
- Disclaimer appears before any booking confirmation path.
- IST date/time is repeated before user confirm.
- No MCP writes occur in this phase.

---

## 3) Phase 2 Rules - Domain Logic + Booking Decisioning

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P2.1 | Introduce dedicated Domain Service. | Orchestrator delegates business decisioning to domain modules. |
| P2.2 | Booking code generation is domain-owned. | Central generator for book/reschedule flows. |
| P2.3 | Model explicit actions. | Domain command supports `hold`, `waitlist`, `reschedule`, `cancel`. |
| P2.4 | Enforce validation centrally. | Topic validity, required fields, and no-PII checks in domain validators. |
| P2.5 | Implement no-slot waitlist branch. | Empty slot match must produce waitlist behavior and command. |

### Definition of Done (Phase 2)
- Canonical domain command is emitted for all supported actions.
- Booking code generation is deterministic and centralized.
- Waitlist path is functional and user-visible in chat.

---

## 4) Phase 3 Rules - FastMCP Integration Layer

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P3.1 | Implement only three MCP tools. | Calendar hold, Docs append, Gmail draft. |
| P3.2 | Enforce schema contracts. | Validated request/response structures for all tools. |
| P3.3 | Calendar title format is fixed. | `Advisor Q&A - {Topic} - {Code}` |
| P3.4 | Docs target is fixed. | Append to `"Advisor Pre-Bookings"` with required fields. |
| P3.5 | Gmail must remain approval-gated. | Draft creation only with pending approval status. |
| P3.6 | Add retry + idempotency. | Retries only for transient failures and no duplicate side effects. |
| P3.7 | Normalize integration errors. | Return platform-neutral error classes to domain/orchestrator. |

### Definition of Done (Phase 3)
- Chat booking flow successfully creates hold + docs append + gmail draft.
- Duplicate retry attempts do not create duplicate artifacts.
- No direct send-email capability exists.

---

## 5) Phase 4 Rules - Reliability, Observability, Recovery

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P4.1 | Structured logs are mandatory. | Include session_id, stage, intent, booking_code, error_type, latency. |
| P4.2 | Error taxonomy by layer is mandatory. | Distinguish parse, domain, integration, and system failures. |
| P4.3 | User-safe fallbacks are required. | Friendly, actionable fallback messages without internal leak. |
| P4.4 | Bounded retries only. | No infinite retry loops. |
| P4.5 | Partial-failure compensation required. | Recoverable strategy when some MCP writes succeed and others fail. |

### Definition of Done (Phase 4)
- Every session is traceable across the runtime path.
- Known failures produce safe responses and structured diagnostics.
- Partial failures are recoverable and auditable.

---

## 6) Phase 5 Rules - Voice Adapters (Chat <-> Voice Bridge)

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P5.1 | Voice must reuse chat runtime. | STT output enters chat path; chat output feeds TTS. |
| P5.2 | No logic duplication in voice layer. | Voice modules cannot implement domain/integration decisions. |
| P5.3 | Enforce behavior parity. | Same scenario in chat and voice yields same domain commands/artifacts. |
| P5.4 | Preserve compliance behavior in voice. | Disclaimer/refusal/no-PII behavior must match chat path. |
| P5.5 | Keep spoken outputs concise and clear. | Booking code and IST time must be spoken in user-friendly format. |

### Definition of Done (Phase 5)
- Voice path is functional through chat runtime bridge.
- Chat and voice outcomes are parity-verified.
- Voice demo artifacts are reproducible.

---

## 7) Cross-Phase Test Strategy

### 7.1 Test Suite Structure
- **Unit tests:** deterministic modules (state machine, validators, code generator, retry/idempotency, formatters).
- **Integration tests:** boundary handoffs (chat->orchestration, orchestration->domain, domain->MCP, voice adapters->chat runtime).
- **E2E tests:**
  - Phases 1-4: chat-only journeys.
  - Phase 5 onward: include voice journeys and parity checks.

### 7.2 Quality Gates for Phase Completion
- New/changed unit tests pass.
- Touched integration boundaries are tested and pass.
- Phase Definition of Done checklist is fully met.
- Compliance checks pass (PII, disclaimer, Gmail draft-only).

### 7.3 Regression Scenarios (Must Stay Green)
- happy-path booking
- no-slot waitlist
- reschedule
- cancel
- what-to-prepare
- investment-advice refusal
- MCP transient failure and retry/idempotency behavior
- chat-vs-voice parity (Phase 5 onward)

### 7.4 Recommended CI Sequence
1. Lint + static checks
2. Unit tests
3. Integration tests
4. E2E smoke tests (chat-only before Phase 5; chat+voice from Phase 5)
5. MCP contract validation tests (Calendar/Docs/Gmail)

---

## 8) Execution Gating Rules

| # | Rule | Enforcement |
|---|------|-------------|
| E1 | No phase skipping. | A phase cannot be marked complete unless all DoD checks pass. |
| E2 | No premature voice work. | Voice adapters cannot start before Phase 1-4 quality gates are green. |
| E3 | No backward leakage. | Later-phase logic must not appear in earlier phases. |
| E4 | Interface freeze before integrations. | Contracts across orchestration/domain/MCP must be stable before production wiring. |
| E5 | Docs and implementation must stay aligned. | Architecture/rules updates are required when behavior changes. |

---

## 9) Phase Completion Checklist

Before closing any phase:
- [ ] Phase-specific rules are implemented.
- [ ] Phase Definition of Done is verified.
- [ ] Required unit/integration/e2e tests pass.
- [ ] Compliance gates pass (PII, disclaimer, draft-only email).
- [ ] Logging and error-handling expectations are met.

---

*Last updated: 2026-04-08*
