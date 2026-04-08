# Voice Agent Rules & Guardrails

This document defines practical rules for implementing the voice appointment scheduler
described in `Docs/Architecture.md`.

Rules are grouped as:
- **General** (apply across some or all phases)
- **Phase-specific** (`Phase 0` to `Phase 5`)

---

## General Rules (Cross-phase)

| # | Rule | Why it matters |
|---|------|----------------|
| G1 | **Do not collect or persist PII during calls.** No phone numbers, emails, account numbers, or identity IDs in transcripts, prompts, logs, or MCP payloads. | Core compliance requirement for pre-booking flow. |
| G2 | **Always enforce disclaimer and refusal policy.** The agent must clearly state informational-only scope and refuse investment advice. | Legal/compliance safety and user clarity. |
| G3 | **Keep architecture boundaries strict.** Use the sequence `Conversation Orchestration -> NLU/LLM -> Booking Domain Service -> MCP Integration`; ASR/TTS stay at boundaries only. | Prevents business logic leakage and future regressions. |
| G4 | **Use environment variables for secrets and config.** Never hardcode API keys, OAuth secrets, service account paths, or MCP commands. | Security hygiene and portable deployment. |
| G5 | **Fail gracefully with user-safe messaging.** If tools fail, return controlled fallback responses and preserve partial state where safe. | Reliability without silent failures. |
| G6 | **Log for auditability, never for sensitive content.** Log booking code, phase, operation status, and trace IDs; avoid raw sensitive utterances. | Debugging + compliance traceability. |
| G7 | **Use idempotent external operations.** Calendar/Docs/Gmail requests must support retries without creating duplicates. | Prevents duplicate holds, log rows, and draft spam. |
| G8 | **Keep responses short and confirmation-driven for voice UX.** Ask one focused question at a time and repeat critical values before commit. | Better recognition, fewer call errors. |
| G9 | **Timezone must be explicit.** Default to IST unless user overrides; repeat date/time + timezone before final confirmation. | Reduces scheduling ambiguity. |
| G10 | **Documentation must stay implementation-accurate.** Update `Docs/Architecture.md` and `Docs/README.md` when behavior changes. | Avoids doc drift and onboarding confusion. |

---

## Phase 0 - Foundations and Compliance Guardrails

| # | Rule | Details |
|---|------|---------|
| P0.1 | **Mandatory opening sequence.** Every new call starts with greeting and disclaimer before transactional actions. | No booking action before compliance framing. |
| P0.2 | **Use only approved topic taxonomy.** Accept/route only defined categories from architecture. | Ensures consistent downstream handling. |
| P0.3 | **PII block/redact at ingestion.** If caller provides PII, do not store it; prompt user to use secure link after call. | Keeps call flow compliant by design. |
| P0.4 | **Define shared session event schema first.** Session/turn events must be standardized before feature expansion. | Enables reliable tracing across phases. |

---

## Phase 1 - Voice I/O and Conversation Orchestration

| # | Rule | Details |
|---|------|---------|
| P1.1 | **ASR/TTS are adapters, not decision engines.** No booking rules or compliance logic in speech layers. | Maintains clean boundaries. |
| P1.2 | **State machine driven dialogs only.** Orchestration must follow explicit states (`greet`, `disclaimer`, `capture`, `offer`, `confirm`, `complete`). | Predictable and testable call behavior. |
| P1.3 | **Require explicit confirmation before commit.** No tentative booking, waitlist creation, or updates until user confirms. | Prevents accidental bookings. |
| P1.4 | **On low ASR confidence, clarify instead of guessing.** Ask user to repeat critical fields (topic/time). | Reduces wrong-slot bookings. |

---

## Phase 2 - NLU/LLM Intent + Entity Layer

| # | Rule | Details |
|---|------|---------|
| P2.1 | **Support only the 5 defined intents.** `book new`, `reschedule`, `cancel`, `what to prepare`, `check availability windows`. | Avoids uncontrolled action space. |
| P2.2 | **Return structured output contract.** LLM output must include intent, confidence, entities, and safety flags. | Domain layer should not parse free text. |
| P2.3 | **Use clarification for ambiguity.** If intent/entity confidence is low, ask targeted follow-up prompts. | Better accuracy than silent assumptions. |
| P2.4 | **Safety decisions precede business routing.** Investment-advice requests or PII attempts must trigger policy response first. | Compliance before convenience. |

---

## Phase 3 - Booking Domain Service

| # | Rule | Details |
|---|------|---------|
| P3.1 | **Domain is source of truth for booking state.** Orchestration and MCP layers must not mutate booking lifecycle directly. | Centralized business consistency. |
| P3.2 | **Generate unique booking code on confirmed action.** Use deterministic format and collision checks. | Reliable user reference and audit key. |
| P3.3 | **Offer two slots when available.** Follow architecture policy before confirmation. | Standardized booking UX. |
| P3.4 | **No-slot path must create waitlist state.** If no match exists, move to waitlist workflow rather than dead-end. | Ensures continuity for user intent. |
| P3.5 | **Secure-link handoff for personal details.** Any contact or account detail collection happens outside call flow. | Keeps call session non-PII. |

---

## Phase 4 - MCP Integration Layer + FastMCP

| # | Rule | Details |
|---|------|---------|
| P4.1 | **All Google interactions go through FastMCP.** No direct Calendar/Docs/Gmail API calls from orchestration or domain code. | Tool boundary and governance. |
| P4.2 | **Use typed MCP operations only.** `create/update/cancel hold`, `append doc log`, `create/update draft`. | Prevents ad-hoc tool misuse. |
| P4.3 | **Gmail must remain approval-gated.** Create draft only; never auto-send advisor communications. | Human-in-the-loop safety. |
| P4.4 | **Persist MCP receipts and trace IDs.** Save event IDs, doc refs, draft IDs, and statuses in booking record. | End-to-end auditability. |
| P4.5 | **Map errors to retry policy categories.** Classify transient/policy/permanent failures and respond accordingly. | Reliable recovery behavior. |

---

## Phase 5 - Reliability, Observability, and Production Readiness

| # | Rule | Details |
|---|------|---------|
| P5.1 | **Define and monitor voice-agent SLOs.** Track turn latency and booking completion success rate. | Production quality baseline. |
| P5.2 | **Instrument cross-layer traces.** Every call must correlate session ID, booking code, and MCP trace IDs. | Fast root-cause analysis. |
| P5.3 | **Track quality and safety metrics.** Include intent accuracy, fallback rate, refusal rate, tool success/failure, average call duration. | Detect drift and regressions. |
| P5.4 | **Test critical edge paths routinely.** No slot, low confidence, PII attempt, investment-advice request, MCP tool failure. | Prevents high-risk regressions. |
| P5.5 | **Provide operational runbooks.** Include retry guidance, partial-failure behavior, and manual recovery steps. | Safer on-call operations. |

---

## Quick Rule Index

| Section | Rule IDs |
|---|---|
| General | G1-G10 |
| Phase 0 | P0.1-P0.4 |
| Phase 1 | P1.1-P1.4 |
| Phase 2 | P2.1-P2.4 |
| Phase 3 | P3.1-P3.5 |
| Phase 4 | P4.1-P4.5 |
| Phase 5 | P5.1-P5.5 |

---

## Definition of Done (Per Phase)

Use this section as an implementation tracking checklist.

### Phase 0 - Foundations and Compliance Guardrails
- [ ] Greeting + mandatory disclaimer is always delivered before any booking action.
- [ ] Approved topic taxonomy is implemented and enforced.
- [ ] PII block/redaction behavior is verified for call ingestion.
- [ ] Session and turn event schema is finalized and documented.

### Phase 1 - Voice I/O and Conversation Orchestration
- [ ] ASR input and TTS output are integrated as boundary adapters.
- [ ] Conversation state machine (`greet -> disclaimer -> capture -> offer -> confirm -> complete`) is implemented.
- [ ] Explicit confirmation gate exists before creating/updating/canceling booking actions.
- [ ] Low-confidence ASR paths trigger clarification prompts.

### Phase 2 - NLU/LLM Intent + Entity Layer
- [ ] All 5 intents are correctly recognized and routed.
- [ ] Structured output contract (`intent`, `confidence`, `entities`, `safety_flags`) is enforced.
- [ ] Ambiguous intent/entity cases trigger clarification (not silent assumptions).
- [ ] Safety policy routing (investment-advice refusal, PII handling) is active and tested.

### Phase 3 - Booking Domain Service
- [ ] Booking lifecycle states are implemented and validated.
- [ ] Unique booking code generation with collision handling is in place.
- [ ] Two-slot offer policy works for eligible booking requests.
- [ ] No-slot path creates waitlist state and continues guided flow.
- [ ] Secure-link handoff is used for personal details collection outside the call.

### Phase 4 - MCP Integration Layer + FastMCP
- [ ] Calendar, Docs, and Gmail operations are invoked only via FastMCP.
- [ ] Typed MCP operations are implemented for create/update/cancel + append + draft.
- [ ] Gmail remains draft-only with explicit approval gate (no auto-send).
- [ ] MCP receipts (`event_id`, `doc_ref`, `draft_id`, trace IDs) persist in booking records.
- [ ] Error mapping and retry behavior are implemented for transient/policy/permanent classes.

### Phase 5 - Reliability, Observability, and Production Readiness
- [ ] SLOs are defined for turn latency and booking completion success.
- [ ] Cross-layer tracing links session IDs, booking codes, and MCP trace IDs.
- [ ] Metrics dashboard/logs track quality and safety indicators.
- [ ] Edge-case test scenarios are executed and passing.
- [ ] Runbooks exist for retries, partial failures, and manual recovery.

---

*Last updated: 2026-04-08*
