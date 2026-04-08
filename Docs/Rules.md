# AI Appointment Scheduler - Rules & Execution Guardrails

This document defines implementation rules for the voice-agent architecture in `Docs/Architecture.md`.
All contributors and AI agents must follow these rules so each phase is built correctly and in order.

---

## 1) General Rules (Apply to All Phases)

| # | Rule | Why this exists |
|---|------|------------------|
| G1 | **Respect layer boundaries.** Runtime path must remain `STT -> Orchestration -> NLU/LLM -> Domain -> MCP -> TTS`. | Prevents business logic leakage and fragile coupling. |
| G2 | **Speech layers are boundary-only.** STT and TTS can transcribe/speak only; they must not trigger domain actions directly. | Keeps core workflow deterministic and testable. |
| G3 | **No PII collection in-call.** Never request or persist phone/email/account numbers in conversational flow, logs, or payloads. | Compliance and privacy by design. |
| G4 | **Mandatory safety disclaimer and refusal policy.** Include the "informational, not investment advice" disclaimer and refuse investment-advice requests. | Required compliance behavior. |
| G5 | **Use structured contracts only.** Cross-layer interfaces must use explicit typed/JSON payloads (`intent_parse`, `session_state`, `booking_command`). | Reduces ambiguity and parsing failures. |
| G6 | **All external writes go through MCP layer only.** No direct Google API calls from Orchestration, NLU, or Domain. | Guarantees clean integration architecture. |
| G7 | **Idempotent side effects.** Calendar/Docs/Gmail operations must support safe retries via operation keys. | Prevents duplicate holds/logs/drafts. |
| G8 | **Approval-gated email behavior.** Gmail integration must create drafts only; never auto-send. | Human-in-the-loop control. |
| G9 | **Timezone clarity.** Treat booking times in IST by default, and repeat date/time before confirmation. | Avoids booking errors and user confusion. |
| G10 | **Fail safely and traceably.** Every failure path must return user-safe messaging and produce structured logs keyed by `session_id` and `booking_code` where available. | Reliability and auditability. |

---

## 2) Phase 1 Rules - Conversational Skeleton + Compliance Guardrails

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P1.1 | **Implement orchestrator state machine first.** | Stages must include greet, disclaimer, intent/topic, time preference, slot offer, confirmation, completion. |
| P1.2 | **Gate progress by required slot filling.** | Missing topic or time preference must trigger re-prompts before next stage. |
| P1.3 | **Support all 5 intents at conversation level.** | Book new, reschedule, cancel, what to prepare, availability windows. |
| P1.4 | **Add topic whitelist validation.** | Only allow supported topics; unknown topics require clarification or safe fallback. |
| P1.5 | **No external writes in Phase 1.** | Calendar/Docs/Gmail actions must remain mocked or disabled. |
| P1.6 | **Mock two-slot offer behavior.** | Slot suggestion should return exactly two options from static/mock source. |
| P1.7 | **Enforce no-PII prompts.** | Prompt set must explicitly avoid asking contact/account details. |

### Definition of Done (Phase 1)
- End-to-end conversational flow runs for all five intents without external integrations.
- Disclaimer always appears before booking progression.
- Date/time is repeated in IST before user confirmation.
- No code path writes to Calendar, Docs, or Gmail.

---

## 3) Phase 2 Rules - Booking Domain Service

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P2.1 | **Introduce dedicated Domain Service module.** | Domain rules must not live in orchestrator handlers. |
| P2.2 | **Generate booking code centrally.** | Use a single generator contract for all booking/reschedule flows. |
| P2.3 | **Centralize policy validation in domain.** | Domain enforces no-PII, topic validity, and confirmation prerequisites. |
| P2.4 | **Model booking actions explicitly.** | Domain command `action` must support `hold`, `waitlist`, `reschedule`, `cancel`. |
| P2.5 | **Implement no-slot waitlist branch.** | If no slots match preference, produce waitlist command and message path. |
| P2.6 | **Return canonical command payloads.** | Output should include `topic`, `slot`, `booking_code`, and integration-ready fields. |

### Definition of Done (Phase 2)
- Domain Service emits valid commands for hold/waitlist/reschedule/cancel.
- Booking code generation is deterministic and reused across all relevant intents.
- Orchestration delegates business decisions to Domain Service, not embedded logic.
- Waitlist behavior works when no slot is available.

---

## 4) Phase 3 Rules - FastMCP Integration Layer (Google APIs)

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P3.1 | **Build FastMCP wrappers for 3 tools only.** | `calendar.create_hold`, `docs.append_prebooking_log`, `gmail.create_draft`. |
| P3.2 | **Standardize input/output schemas per tool.** | Each tool validates request payload and returns stable structured response. |
| P3.3 | **Calendar title format is mandatory.** | `Advisor Q&A - {Topic} - {Code}` for tentative hold events. |
| P3.4 | **Docs writes append-only pre-booking rows.** | Store date, topic, slot, code, action type in "Advisor Pre-Bookings". |
| P3.5 | **Gmail is draft-only and approval-pending.** | Output must include `draft_id` and `approval_status=pending`. |
| P3.6 | **Add retries + idempotency at integration boundary.** | Prevent duplicates on transient failure. |
| P3.7 | **Normalize integration errors.** | Return integration-safe error types to Domain Service (no provider-specific leakage to user). |

### Definition of Done (Phase 3)
- Successful creation of tentative Calendar hold from domain command.
- Successful append to Docs pre-booking log.
- Successful Gmail draft creation with pending approval status.
- Integration failures are retriable, normalized, and non-destructive.

---

## 5) Phase 4 Rules - Reliability, Observability, and Recovery

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P4.1 | **Structured logging is required.** | All major actions log with `session_id`, `intent`, stage, and `booking_code` if present. |
| P4.2 | **Classify failures by layer.** | Distinguish STT, parsing, domain validation, and MCP integration errors. |
| P4.3 | **Implement user-safe fallback prompts.** | On errors, provide concise next steps without exposing internal details. |
| P4.4 | **Define retry policy per error class.** | Retries only for transient conditions; no infinite loops. |
| P4.5 | **Handle partial-write scenarios.** | Add compensating workflow when one integration succeeds and another fails. |
| P4.6 | **Capture execution metrics.** | Track call success rate, fallback frequency, and integration latency. |

### Definition of Done (Phase 4)
- A single session can be traced across all layers from transcript to integration writes.
- Known failures return predictable user messaging and structured diagnostics.
- Partial failures are handled with compensating or recovery behavior.
- Retry behavior is bounded and verified.

---

## 6) Phase 5 Rules - Voice UX Tuning + Demo Readiness

### Rules
| # | Rule | Implementation expectation |
|---|------|----------------------------|
| P5.1 | **Keep prompts short and confirmation-focused.** | Avoid verbose assistant turns; preserve clarity. |
| P5.2 | **Maintain confirmation cadence.** | Reconfirm topic and IST slot at critical transitions. |
| P5.3 | **Provide secure-link next step consistently.** | End-state response includes booking code + secure details link guidance. |
| P5.4 | **Prepare script artifact from live prompts.** | Keep a source-of-truth script file for demo/review. |
| P5.5 | **Verify required demo artifacts.** | Call recording/live demo, calendar hold evidence, docs entry evidence, gmail draft evidence, README updates. |

### Definition of Done (Phase 5)
- Voice interaction is concise, clear, and compliant in live/demo execution.
- All required submission artifacts are generated and reproducible.
- README and supporting docs match actual implemented behavior.

---

## 7) Execution Gating Rules (How Phases Must Be Coded)

| # | Rule | Enforcement |
|---|------|-------------|
| E1 | **Do not skip phase prerequisites.** | A phase cannot be marked complete unless its Definition of Done is fully met. |
| E2 | **No backward leakage.** | Later-phase logic (e.g., direct Google writes) must not be introduced in earlier phases. |
| E3 | **Test minimums per phase are mandatory.** | Each phase must add/update tests for its own rules and success/failure paths. |
| E4 | **Interfaces freeze before integration.** | Contracts between Orchestration, NLU, Domain, and MCP must be finalized before external API hookup. |
| E5 | **Docs and rules must co-evolve.** | If architecture or behavior changes, update `Docs/Architecture.md` and `Docs/Rules.md` in the same change set. |

---

## 8) Phase Completion Checklist

Before marking any phase complete, confirm:
- [ ] All phase rules are implemented.
- [ ] All Definition of Done bullets are verified.
- [ ] New and changed tests pass for phase-specific behavior.
- [ ] No violation of general rules (PII, disclaimer, boundaries, draft-only email).
- [ ] Logs and error handling are present for new flows.

---

*Last updated: 2026-04-08*
