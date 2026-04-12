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
| P1.1 | Build chat runtime first. | Text in / text out via `Orchestrator.handle` and `post_message`; browser UI is **Phase 5** (Node Web UI + HTTP API). |
| P1.2 | Implement orchestrator state machine. | Required stages: greet, disclaimer, capture, offer, confirm, complete. |
| P1.3 | Support all 5 intents in chat mode. | book, reschedule, cancel, what to prepare, availability. |
| P1.4 | Enforce topic whitelist and no-PII prompts. | Unsupported topics and sensitive user inputs are handled safely. |
| P1.5 | Offer exactly two mock slots in IST. | Slot *options* are generated as future IST-labeled mock data relative to runtime date; the **selected** slot is persisted to Google Calendar as a tentative hold after confirmation. |
| P1.6 | Use real Google MCP for operational artifacts. | After explicit user confirmation, invoke **real** Calendar hold, Docs append, and Gmail **draft** (never auto-send) via `GoogleMcpClient` / FastMCP tools — not in-process fake Google services. |

### Definition of Done (Phase 1)
- Chat conversation supports all five intents end-to-end.
- Disclaimer appears before any booking confirmation path.
- IST date/time is repeated before user confirm.
- On confirmed booking, Calendar hold + Docs pre-booking append + Gmail draft succeed when Google credentials and resource IDs are configured (automated tests may substitute an in-memory recorder — see `Docs/Architecture.md`).

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

## 6) Phase 5 Rules - Web Chat UI (Node.js) + HTTP Chat API

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P5.1 | Thin HTTP boundary only. | Python API forwards to existing `post_message` / orchestrator; **no** booking or MCP logic in Node or duplicated in the API layer beyond transport. |
| P5.2 | Node is presentation + dev ergonomics. | `web/chat-ui/` uses Vite (or similar) for fast iteration; UI calls documented REST endpoints. |
| P5.3 | No secrets in the browser. | API keys, Google credentials, and service tokens stay server-side; front-end only sends `session_id` and user text. |
| P5.4 | CORS and localhost defaults. | Permit local dev origins explicitly; production deployments use HTTPS and tightened origin lists. |
| P5.5 | Reserve voice affordances. | Layout or routing allows adding mic/TTS controls in Phase 7 without rewriting the text chat flow. |

### Definition of Done (Phase 5)
- A developer can run the Python chat API and `npm run dev` and complete the full text booking journey in the browser.
- Behavior matches Phase 1 integration tests for the same transcript (disclaimer, IST confirmation, MCP trio on confirm when configured).
- CI remains green on existing pytest suites; Web UI adds optional smoke tests only.

---

## 7) Phase 6 Rules - Secondary Intent Subgraphs (Chat-First Completion)

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P6.1 | Implement full reschedule graph. | Collect booking code, validate, offer two alternatives, update hold/artifacts safely. |
| P6.2 | Implement full cancel graph. | Collect booking code, confirm, cancel hold, append cancellation note. |
| P6.3 | Implement deterministic prepare guidance. | `what_to_prepare` replies come from approved deterministic templates. |
| P6.4 | Implement availability peek safely. | Availability checks remain informational-only unless user enters booking path. |
| P6.5 | Preserve booking-code-only identity flow. | Reschedule/cancel lookup must use booking code only (no alternate identity capture). |
| P6.6 | Preserve compliance and idempotency. | Disclaimer/refusal/no-PII and no-duplicate side effects remain enforced. |

### Definition of Done (Phase 6)
- Secondary-intent subgraphs are complete and tested end-to-end in chat mode.
- Booking-code-only identity works for reschedule/cancel.
- Secondary intents do not introduce PII capture/persistence.

---

## 8) Phase 7 Rules - Voice Adapters (Chat <-> Voice Bridge) + Web UI Entry

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P7.1 | Voice must reuse chat runtime. | STT output becomes `user_text` for `Orchestrator.handle`; assistant lines feed TTS. |
| P7.2 | No logic duplication in voice layer. | Voice modules cannot implement domain/integration decisions. |
| P7.3 | Enforce behavior parity. | Same scenario in text Web UI and voice yields same domain commands/artifacts. |
| P7.4 | Preserve compliance in voice. | Disclaimer/refusal/no-PII behavior must match chat path; barge-in cannot skip policy gates. |
| P7.5 | Spoken outputs are concise and clear. | Booking code and IST time use `tts_formatter` (or equivalent); scripts do not elicit PII. |
| P7.6 | Voice is reachable from Phase 5 UI. | Users enable voice from the same `web/chat-ui/` app (mic toggle + playback). |
| P7.7 | Transcript hygiene. | STT text passes the same PII guard/redaction path as typed chat. |
| P7.8 | Voice UX baseline. | In voice mode: assistant responses must be text + speech, and user speech can interrupt TTS. |

### Definition of Done (Phase 7)
- Voice path is functional through the chat runtime bridge with parity versus text UI.
- Voice controls are integrated into the Web UI delivered in Phase 5.
- No raw audio/transcript persistence by default in production; demo artifacts are reproducible.

---

## 9) Phase 8 Rules - Hardening, Ops, and Degraded Modes

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P8.1 | Enforce production redaction policy. | Log/event pipelines redact sensitive text before write/export. |
| P8.2 | Add runtime abuse controls. | Session creation limits, TTL cleanup, and bounded retries are active. |
| P8.3 | Define MCP outage behavior. | User-safe degraded mode messaging and runbook steps are documented and tested. |
| P8.4 | Add failure-injection coverage. | Timeout/transient failure tests validate retry + fallback + compensation behavior. |
| P8.5 | Verify no-PII in observability/export. | Metrics, traces, and audit outputs contain metadata only and no raw user text. |

### Definition of Done (Phase 8)
- Failure injection tests pass for MCP outages/timeouts.
- Degraded mode behavior is documented and operator-ready.
- Production observability path is PII-safe by policy and test.

---

## 10) PII Rules by Phase (Mandatory)

| Phase | PII requirement |
|---|---|
| Phase 1 | `PiiGuard` blocks obvious identifiers at input; prompts never ask for PII. |
| Phase 2 | Domain validators reject commands carrying disallowed PII-like fields. |
| Phase 3 | MCP payload validator blocks PII in Calendar/Docs/Gmail payloads before send. |
| Phase 4 | Logging/audit redaction is enforced before persistence/export. |
| Phase 5 | Web UI does not store raw transcripts in browser persistence by default; never ship secrets to the client; HTTPS in non-local deployments. |
| Phase 6 | Reschedule/cancel use booking code only; no alternate identity capture. |
| Phase 7 | STT/TTS path uses same PII gate as chat; scripts/TTS avoid eliciting or repeating PII; no raw audio retention by default. |
| Phase 8 | CI/runtime audits verify no PII in logs, traces, artifacts, and test fixtures. |

---

## 11) Cross-Phase Test Strategy

### 11.1 Test Suite Structure
- **Unit tests:** deterministic modules (state machine, validators, code generator, retry/idempotency, formatters).
- **Integration tests:** boundary handoffs (chat->orchestration, orchestration->domain, domain->MCP, HTTP API->`post_message`, voice adapters->chat runtime).
- **E2E tests:**
  - Phases 1-4: chat-only journeys (pytest).
  - Phase 5: optional browser or HTTP smoke against API + Node UI.
  - Phase 6 onward: include secondary-intent depth checks.
  - Phase 7 onward: include voice journeys, parity checks, and Web UI voice mode where applicable.

### 11.2 Quality Gates for Phase Completion
- New/changed unit tests pass.
- Touched integration boundaries are tested and pass.
- Phase Definition of Done checklist is fully met.
- Compliance checks pass (PII, disclaimer, Gmail draft-only).

### 11.3 Regression Scenarios (Must Stay Green)
- happy-path booking
- no-slot waitlist
- reschedule
- cancel
- what-to-prepare
- investment-advice refusal
- MCP transient failure and retry/idempotency behavior
- chat-vs-voice parity (Phase 7 onward)

### 11.4 Recommended CI Sequence
1. Lint + static checks
2. Unit tests
3. Integration tests
4. E2E smoke tests (chat-only for Phases 1-4; optional Web UI smoke in Phase 5; expanded secondary-intent depth in Phase 6; chat+voice from Phase 7)
5. MCP contract validation tests (Calendar/Docs/Gmail)

---

## 12) Execution Gating Rules

| # | Rule | Enforcement |
|---|------|-------------|
| E1 | No phase skipping. | A phase cannot be marked complete unless all DoD checks pass. |
| E2 | No premature voice work. | Voice adapters (**Phase 7**) cannot start before Phase 1-6 and **Phase 5 Web UI** quality gates are green (text path proven in browser + HTTP API). |
| E3 | No backward leakage. | Later-phase logic must not appear in earlier phases. |
| E4 | Interface freeze before integrations. | Contracts across orchestration/domain/MCP must be stable before production wiring. |
| E5 | Docs and implementation must stay aligned. | Architecture/rules updates are required when behavior changes. |

---

## 13) Phase Completion Checklist

Before closing any phase:
- [ ] Phase-specific rules are implemented.
- [ ] Phase Definition of Done is verified.
- [ ] Required unit/integration/e2e tests pass.
- [ ] Compliance gates pass (PII, disclaimer, draft-only email).
- [ ] Logging and error-handling expectations are met.

---

*Last updated: 2026-04-12*
