# AI Appointment Scheduler - Phase-wise Architecture (Chat-First)

## 1) System Goal
Build a compliant, pre-booking assistant for advisor appointments in two tracks:
- **Track A (first):** full functionality in text/chat mode for rapid testing.
- **Track B (later):** add voice adapters (speech-to-text and text-to-speech) over the same chat runtime.

The system must:
- Handle 5 intents: book new, reschedule, cancel, what to prepare, availability windows.
- Enforce disclaimer and policy-safe behavior ("informational, not investment advice").
- Avoid collecting PII in chat or voice.
- Create operational artifacts through MCP:
  - Google Calendar tentative hold
  - Google Docs pre-booking log append
  - Gmail approval-gated draft

## 2) High-Level Layered Architecture

### 2.1 Primary Runtime (Phases 1-4): Chat Mode
`Chat Input (UI/API)`  
-> `Conversation Orchestration`  
-> `NLU/LLM Layer`  
-> `Booking Domain Service`  
-> `MCP Integration Layer (FastMCP + Google APIs)`  
-> `Chat Output`

### 2.2 Later Runtime (Phase 5): Voice Over Chat Runtime
`Speech-to-Text (ingress)`  
-> `Chat Runtime (same orchestration/domain/integrations)`  
-> `Text-to-Speech (egress)`

Speech layers remain boundary adapters only and never bypass chat runtime logic.

### 2.3 Layer Responsibilities
1. **Chat Input/Output Layer**
   - Receives user text and returns assistant text.
   - Primary interface for early build + testing.
   - Must drive the exact same orchestration/domain paths used by voice later.

2. **Conversation Orchestration**
   - State machine + turn management.
   - Required sequence:
     - greet
     - disclaimer
     - intent/topic capture
     - time preference capture (IST)
     - offer two slots
     - confirmation
     - booking code + secure link next step
   - Handles fallback and re-prompts.

3. **NLU/LLM Layer**
   - Intent + entity extraction:
     - `intent`: `book|reschedule|cancel|prepare|availability`
     - `topic`
     - `time_preference`
   - Emits structured parse output.
   - Applies policy-safe behavior (investment advice refusal).
   - Does not call Google APIs directly.

4. **Booking Domain Service**
   - Central business rules and policy checks.
   - Validates no PII fields, valid topics, confirmation prerequisites.
   - Generates booking code.
   - Emits canonical booking commands: `hold|waitlist|reschedule|cancel`.

5. **MCP Integration Layer (FastMCP Server)**
   - Exposes wrapped Google tools:
     - `calendar.create_hold(...)`
     - `docs.append_prebooking_log(...)`
     - `gmail.create_draft(...)`
   - Handles retries, idempotency, and error normalization.

6. **Voice Adapters (later)**
   - STT converts audio to text input for chat runtime.
   - TTS converts chat runtime output text to speech.
   - No domain/orchestration logic in adapters.

## 3) Data Contracts

### 3.1 Intent Parse Output
- `intent`
- `topic`
- `time_preference`
- `confidence`
- `policy_flags`

### 3.2 Session State
- `session_id`
- `current_stage`
- `timezone` (default `IST`)
- `selected_slot` (optional)
- `booking_code` (optional)
- `transcript_log` (sanitized)

### 3.3 Booking Command (Domain -> MCP)
- `action` (`hold|waitlist|reschedule|cancel`)
- `topic`
- `slot`
- `booking_code`
- `notes_entry`
- `email_draft_payload`

## 4) FastMCP Google Wrapper Design

### 4.1 Calendar Tool
- Purpose: create tentative hold.
- Title format: `Advisor Q&A - {Topic} - {Code}`
- Input: topic, slot(IST), booking_code, mode.
- Output: event_id, calendar_link, status.

### 4.2 Docs Tool
- Purpose: append pre-booking row to `"Advisor Pre-Bookings"`.
- Input: date, topic, slot, code, action_type.
- Output: document_id, appended_range, status.

### 4.3 Gmail Tool (Approval-Gated)
- Purpose: create draft only (never send).
- Input: advisor recipient, subject, body, metadata.
- Output: draft_id, preview, `approval_status=pending`.

## 5) Phase-wise Delivery Plan

## Phase 1 - Chat Runtime Skeleton + Compliance
**Objective:** functional chat-first booking workflow without external writes.

**Implementation Details**
- Build `src/interfaces/chat/`:
  - `chat_handler.py` (text in/out).
  - `session_router.py` (maps user session to orchestrator state).
- Build `src/orchestration/`:
  - state machine stages: greet -> disclaimer -> capture -> offer -> confirm -> complete.
  - fallback/re-prompt handlers.
- Build compliance guards:
  - topic whitelist.
  - no-PII prompt/validation guard.
  - investment-advice refusal templates.
- Build mock slots provider returning exactly two slots in IST.
- Keep MCP integration as stubs only.

**Testing Details**
- Unit:
  - state transitions.
  - topic whitelist.
  - PII detector.
- Integration:
  - chat handler -> orchestrator session flow.
  - all 5 intents in chat mode.
  - assert no MCP writes happen.
- E2E:
  - one full booking chat transcript with disclaimer and IST repetition.

**Definition of Done**
- All 5 intents work in chat mode.
- Disclaimer is always shown before booking progression.
- Date/time repeated in IST before confirmation.
- No Calendar/Docs/Gmail write path active.

## Phase 2 - Domain Logic + Booking Decisioning
**Objective:** centralize deterministic business decisions.

**Implementation Details**
- Build `src/domain/booking/`:
  - `models.py` (`BookingCommand`, `BookingDecision`).
  - `validator.py` (topic, required fields, no PII).
  - `code_generator.py` (booking code generation + collision handling).
  - `decision_engine.py` (book, waitlist, reschedule, cancel logic).
  - `slot_selector.py` (best two slots or waitlist).
- Orchestrator must delegate command creation to domain.

**Testing Details**
- Unit:
  - booking code format + uniqueness behavior.
  - validation failures for topic/slot/PII.
  - command generation for all actions.
- Integration:
  - orchestrator -> domain handoff.
  - no-slot -> waitlist command path.
- E2E:
  - happy booking.
  - no-slot waitlist.
  - reschedule and cancel scenarios.

**Definition of Done**
- Domain emits valid canonical commands for all supported actions.
- Booking codes generated only by domain.
- Waitlist behavior works and is surfaced in chat replies.

## Phase 3 - FastMCP Integration (Calendar, Docs, Gmail Draft)
**Objective:** connect real systems through MCP wrappers.

**Implementation Details**
- Build `src/integrations/mcp/`:
  - `contracts.py` (tool input/output schemas).
  - `client.py` (calendar/docs/gmail wrapper methods).
  - `idempotency.py` (operation-key strategy).
  - `retry_policy.py` (transient retry only).
  - normalized error types.
- Enforce operational policies:
  - Calendar title format.
  - Docs append target + fields.
  - Gmail draft-only with pending approval.

**Testing Details**
- Unit:
  - schema contract validation.
  - idempotency key behavior.
  - retry policy logic.
- Integration:
  - domain command -> MCP request mapping.
  - mocked Google API wrapper tests.
- E2E:
  - booking flow creates hold + docs append + gmail draft.

**Definition of Done**
- Calendar hold, docs append, and gmail draft all succeed from a single chat flow.
- Duplicate retries do not duplicate side effects.
- No email send path exists.

## Phase 4 - Reliability, Observability, Recovery
**Objective:** production hardening on chat runtime.

**Implementation Details**
- Build `src/observability/`:
  - structured logger (session_id, stage, intent, booking_code, error_type, latency).
  - metrics counters/histograms.
  - audit trail of artifact status.
- Build fallback and recovery:
  - error-class to user-safe prompt mapping.
  - bounded retries.
  - compensation handlers for partial integration failures.

**Testing Details**
- Unit:
  - mandatory log fields.
  - fallback message mapping.
  - compensation strategy selection.
- Integration:
  - STT is not required yet; test parse/domain/MCP failures in chat runtime.
  - partial write scenarios (hold success, docs/gmail failure).
- E2E:
  - failure journeys produce safe user messages and traceable logs.

**Definition of Done**
- Every session is traceable end-to-end in logs.
- Known failure classes are recoverable or safely surfaced.
- Partial failures are auditable and actionable.

## Phase 5 - Voice Adapters (Chat <-> Voice Bridge)
**Objective:** add voice without changing core behavior.

**Implementation Details**
- Build `src/voice/`:
  - `stt_adapter.py` (audio -> normalized text input).
  - `tts_adapter.py` (chat response text -> speech output).
  - `chat_voice_bridge.py` for adapter orchestration.
  - `tts_formatter.py` for speaking clarity (booking code/date-time).
- Ensure parity:
  - Voice path reuses chat runtime exactly.
  - No duplicated domain or integration logic in voice modules.

**Testing Details**
- Unit:
  - STT/TTS adapter normalization.
  - booking code/date-time spoken formatting.
- Integration:
  - same scenario in chat and voice yields equivalent domain command/artifacts.
- E2E:
  - simulated voice flow (STT -> chat runtime -> TTS).

**Definition of Done**
- Voice path works via chat runtime bridge with behavior parity.
- Chat and voice produce equivalent business outcomes for same intent input.
- Demo artifacts are reproducible.

## 6) Cross-Phase Test Strategy

### 6.1 Test Suite Structure
- `tests/unit/`: deterministic logic (state machine, validators, formatters, retry/idempotency).
- `tests/integration/`: boundary handoffs (chat<->orchestration, orchestration<->domain, domain<->MCP, chat<->voice bridge).
- `tests/e2e/`:
  - Phases 1-4: chat-only journeys.
  - Phase 5 onward: chat + voice parity journeys.

### 6.2 Quality Gates for Phase Completion
- New unit tests for changed modules must pass.
- Touched integration boundaries must have passing tests.
- Phase Definition of Done checklist must be fully satisfied.
- No phase can advance with unresolved compliance failures (PII/disclaimer/draft-only rules).

### 6.3 Regression Scenarios
Maintain a stable regression suite with:
- happy-path booking
- no-slot waitlist
- reschedule
- cancel
- "what to prepare"
- investment-advice refusal
- MCP transient failure + retry behavior
- chat-vs-voice outcome parity (from Phase 5 onward)

### 6.4 Recommended CI Sequence
1. Lint + static checks
2. Unit tests
3. Integration tests
4. E2E smoke tests (chat-only for early phases; include voice from Phase 5)
5. Contract validation for Calendar/Docs/Gmail MCP payloads

## 7) Suggested Repository Mapping
- `src/interfaces/chat/` - chat API/CLI handlers and session routing
- `src/orchestration/` - conversation state machine and handlers
- `src/nlu/` - intent/entity extraction and policy prompts
- `src/domain/booking/` - booking rules, codes, decisioning
- `src/integrations/mcp/` - FastMCP clients and contracts
- `src/voice/` - STT/TTS adapters (introduced in Phase 5)
- `tests/` - unit/integration/e2e suites
- `Docs/` - architecture, rules, scripts, and delivery notes

## 8) Low-Level Architecture Gap Closure (Chat-First Canonical)

This section captures key low-level implementation elements that were not explicit in earlier sections and should be treated as canonical for build sequencing.

### 8.1 Chat-First Execution Rule
- Ship full text/chat behavior before any audio path.
- Core API contract:
  - `Orchestrator.handle(user_text: str, session: SessionContext) -> AgentTurn`
  - `AgentTurn.messages: list[str]` is the canonical assistant output for both chat UI and later TTS.
- Voice is adapter-only:
  - `SpeechToText -> user_text`
  - `for message in AgentTurn.messages: TextToSpeech.synthesize(message)`
  - No changes to orchestration, NLU, domain, or MCP for voice enablement.

### 8.2 Cross-Cutting Conventions (Canonical)
- **Time model**
  - Persist UTC instants (`start_utc`, `end_utc`) and render using `ZoneId=Asia/Kolkata`.
  - Use injectable `Clock` in all time-dependent modules/tests.
- **Correlation and identity**
  - Every turn carries `session_id` and `correlation_id`.
  - Propagate `correlation_id` through MCP calls and structured logs.
- **Idempotency baseline**
  - Use idempotency key `booking:{code}` (or deterministic hash of code + slot start) for create-hold workflows.
- **Config baseline**
  - Environment-driven config for Gemini key, Google credentials, secure-link template, and feature flags (`chat_enabled`, `voice_enabled`).
  - Secrets only in `.env` (gitignored).

### 8.3 Canonical Session State (Expanded)
- Required `SessionContext` fields:
  - `state`
  - `disclaimer_status` (`pending|acknowledged`)
  - `intent`
  - `preference` (partial `BookingPreference` allowed)
  - `offered_slots` (0-2)
  - `selected_slot`
  - `pending_booking_code`
  - `last_mcp_error` (sanitized)
  - `turn_count`
  - `advice_redirect_count`
- Session store requirements:
  - `get(session_id)`, `put(session)`
  - idle TTL default 30 minutes
  - thread-safe behavior for multi-worker runtime

### 8.4 Deterministic State Handling + Side-Effect Ordering
- Implement transition logic as:
  - pure state handler returns `(new_state, side_effects[])`
  - commit state first, then execute side effects in order
- Canonical side-effect queue shape:
  - `emit_assistant_text(text)`
  - `google_calendar_mcp.createHold(...)`
  - `google_docs_mcp.append(...)`
  - `gmail_mcp.createDraft(...)`
  - `persist_session`
- Failure behavior:
  - MCP failures transition to recovery state and produce user-safe apology/retry text
  - apply compensation where feasible (for example delete hold if subsequent append fails)

### 8.5 NLU Structured Contract (Strict)
- NLU result should support this full shape:
  - `intent`
  - `topic`
  - `date_phrase`
  - `time_window`
  - `booking_code_guess`
  - `wants_investment_advice`
  - `confidence`
- Resolver pipeline requirements:
  - relative-date resolution with IST-aware `Clock`
  - topic fuzzy mapping with clarification threshold
  - low-confidence targeted clarification with capped retries per state

### 8.6 FastMCP Tooling and CI Fakes (Explicit)
- Define FastMCP tools as first-class contracts:
  - `calendar_create_hold(...) -> external_event_id`
  - `calendar_delete_hold(...)`
  - `docs_append_prebooking(...)`
  - `gmail_create_draft(...) -> draft_id`
- Back each tool via `google-api-python-client`:
  - Calendar v3, Docs v1, Gmail v1
- Add in-memory fake implementations for CI:
  - `FakeCalendarMcp`
  - `FakeNotesMcp`
  - `FakeEmailMcp`
- CI default uses fakes; real Google calls are manual/integration-environment only.

### 8.7 Repo Layout Baseline (Monolith First)
- Canonical module seams:
  - `src/domain/`
  - `src/session/`
  - `src/nlu/`
  - `src/integrations/google_mcp/`
  - `src/integrations/voice/` (Phase 7+)
  - `src/api/chat/` (primary in Phases 1-6)
  - `src/api/voice/` (Phase 7+)

### 8.8 Phase Realignment (Canonical 1-8)
- `Phase 1`: domain primitives + mock calendar (no external I/O)
- `Phase 2`: session state machine + chat entrypoint (`handle` path only)
- `Phase 3`: NLU wiring to orchestrator
- `Phase 4`: FastMCP + Google execution and idempotent side effects
- `Phase 5`: waitlist + investment-advice refusal hardening
- `Phase 6`: secondary intent subgraphs (reschedule/cancel/prepare/availability)
- `Phase 7`: voice adapters only (STT/TTS + audio glue, no core logic rewrite)
- `Phase 8`: hardening/ops (redaction, rate limiting, failure-injection runbooks)

### 8.9 Traceability Addendum
- Acceptance must remain chat-regression-first:
  - all five intents pass through chat suite before voice work begins
  - voice tests add coverage but do not replace chat as quality gate
- Requirement mapping must include:
  - disclaimer gate
  - no PII gate
  - no investment advice gate
  - two-slot offer rule
  - booking code + Calendar/Docs/Gmail side effects
