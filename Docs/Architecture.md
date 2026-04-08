# AI Appointment Scheduler - Phase-wise Architecture

## 1) System Goal
Build a compliant, pre-booking voice agent for advisor appointments that:
- Handles 5 intents: new booking, reschedule, cancel, preparation guidance, availability checks.
- Enforces disclaimer and safety policy ("informational, not investment advice").
- Avoids collecting PII during the call.
- Creates operational artifacts through MCP:
  - Calendar tentative hold (Google Calendar)
  - Pre-booking log entry (Google Docs)
  - Approval-gated advisor email draft (Gmail)

## 2) High-Level Layered Architecture
The runtime path is linear, while speech layers stay at the boundaries and do not interrupt business logic in the middle:

`Speech-to-Text (ingress)`  
-> `Conversation Orchestration`  
-> `NLU/LLM Layer`  
-> `Booking Domain Service`  
-> `MCP Integration Layer (FastMCP + Google APIs)`  
-> `Text-to-Speech (egress)`

### Layer Responsibilities
1. **Speech-to-Text (STT) Layer (Start Boundary)**
   - Converts caller audio to text utterances.
   - Provides confidence scores and partial/final transcript markers.
   - No business decision-making here; this layer only transcribes.

2. **Conversation Orchestration Layer**
   - Owns turn management, state machine, and flow progression.
   - Enforces required sequence:
     - Greeting
     - Disclaimer
     - Intent + topic capture
     - Time preference capture (with timezone = IST)
     - Slot offer (two options)
     - Confirmation
     - Next steps and secure link
   - Handles fallback, re-prompts, interruptions, and confirmation loops.
   - Delegates interpretation to NLU/LLM and business actions to Domain Service.

3. **NLU/LLM Layer**
   - Classifies intent and extracts entities:
     - `intent`: book/reschedule/cancel/prepare/availability
     - `topic`: allowed categories only
     - `time_preference`: day/time window in IST
   - Produces structured output (JSON contract) for orchestration/domain.
   - Applies policy-safe responses:
     - Refuse investment advice
     - Offer educational alternatives when required
   - Does not directly call Google APIs.

4. **Booking Domain Service**
   - Core business logic and policy enforcement.
   - Validates constraints:
     - No PII fields accepted or persisted
     - Topic must be from supported list
     - Date/time repeated back at confirmation
   - Generates booking code (example: `NL-A742`).
   - Decides booking outcome:
     - Tentative hold flow
     - Waitlist flow when no slot matches
   - Prepares canonical command payloads for MCP layer.

5. **MCP Integration Layer (FastMCP Server)**
   - Adapter layer exposing tools backed by Google APIs:
     - `calendar.create_hold(...)`
     - `docs.append_prebooking_log(...)`
     - `gmail.create_draft(...)` (approval-gated)
   - Handles auth, retries, idempotency keys, and error normalization.
   - Returns deterministic operation results to Domain Service.

6. **Text-to-Speech (TTS) Layer (End Boundary)**
   - Converts final response text to voice output.
   - Keeps responses concise and confirmation-centric for call clarity.
   - No orchestration or business logic here.

## 3) Data Contracts (Core Objects)
Use strict structured payloads between layers.

### 3.1 Intent Parse Output (NLU -> Orchestrator/Domain)
- `intent`
- `topic`
- `time_preference`
- `confidence`
- `policy_flags` (e.g., investment_advice_request = true)

### 3.2 Session State (Orchestration)
- `session_id`
- `current_stage` (greet/disclaimer/topic/time/offer/confirm/complete)
- `timezone` (default IST)
- `selected_slot` (optional)
- `booking_code` (optional)
- `transcript_log` (sanitized, no PII)

### 3.3 Booking Command (Domain -> MCP)
- `action`: hold | waitlist | reschedule | cancel
- `topic`
- `slot`
- `booking_code`
- `notes_entry`
- `email_draft_payload`

## 4) FastMCP Server Design (Google API Wrappers)
FastMCP tools are thin wrappers with strong validation and stable responses.

### 4.1 Calendar Tool
- **Purpose:** Create tentative hold.
- **Title format:** `Advisor Q&A - {Topic} - {Code}`
- **Input:** topic, slot(IST), booking_code, mode(tentative/waitlist)
- **Output:** event_id, calendar_link, status

### 4.2 Docs Tool
- **Purpose:** Append pre-booking log row in "Advisor Pre-Bookings".
- **Input:** date, topic, slot, code, action_type
- **Output:** document_id, appended_range, status

### 4.3 Gmail Tool (Approval-Gated)
- **Purpose:** Create draft only; never auto-send.
- **Input:** advisor recipient, subject, body template, metadata
- **Output:** draft_id, preview, approval_status=`pending`

## 5) Phase-wise Delivery Plan

## Phase 1 - Conversational Skeleton + Compliance Guardrails
**Objective:** Get a safe call flow running end-to-end without external writes.

**Scope**
- Implement orchestrator states and transitions.
- Add mandatory disclaimer and refusal behavior.
- Add topic whitelist and no-PII checks.
- Mock slot offering (two slots from static calendar JSON).

**Exit Criteria**
- Voice flow supports all 5 intents at conversational level.
- No booking artifacts written yet.
- Confirm/repeat date-time in IST before final confirmation.

## Phase 2 - Domain Logic + Booking Code + Slot Decisions
**Objective:** Introduce deterministic business actions.

**Scope**
- Add Booking Domain Service with command generation.
- Implement booking code generator.
- Implement no-slot handling (waitlist path).
- Add reschedule/cancel rule handling.

**Exit Criteria**
- Domain emits valid commands for hold/waitlist/reschedule/cancel.
- All policy checks are centralized in Domain Service.

## Phase 3 - FastMCP Integration (Calendar, Docs, Gmail Draft)
**Objective:** Connect real systems through MCP adapters.

**Scope**
- Build FastMCP server wrappers for Google Calendar, Docs, Gmail.
- Wire Domain commands to MCP tool calls.
- Add operation idempotency and retry envelopes.
- Enforce approval-gated Gmail drafts (draft-only mode).

**Exit Criteria**
- Successful tentative hold creation in Calendar.
- Successful append into "Advisor Pre-Bookings" doc.
- Successful advisor draft creation with `pending approval`.

## Phase 4 - Reliability, Observability, and Recovery
**Objective:** Production-harden workflows.

**Scope**
- Structured logging by `session_id` and `booking_code`.
- Error buckets: STT failure, parsing failure, domain validation, MCP tool failure.
- User-safe fallback prompts and retry strategy.
- Compensating actions for partial failures (e.g., hold created but doc append failed).

**Exit Criteria**
- Traceable flow per call across all layers.
- Partial failure paths handled with user-safe messaging.

## Phase 5 - Voice UX Tuning + Demo Readiness
**Objective:** Improve call clarity and prepare deliverables.

**Scope**
- Shorten prompts and improve confirmation cadence.
- Add script file with production prompts/utterances.
- Validate demo artifacts:
  - call recording/live link
  - calendar hold screenshot
  - docs log proof
  - gmail draft proof
  - README updates

**Exit Criteria**
- End-to-end demo runs reliably.
- All required submission artifacts are reproducible.

## 6) Primary Runtime Sequence (Booking New Appointment)
1. STT transcribes caller utterance.
2. Orchestrator greets and enforces disclaimer.
3. NLU extracts intent/topic/time preference.
4. Orchestrator asks for missing slots/entities.
5. Domain validates inputs, selects/offers two slots.
6. User confirms selected slot.
7. Domain generates booking code.
8. MCP layer executes:
   - Calendar tentative hold
   - Docs pre-booking append
   - Gmail draft creation (approval pending)
9. Orchestrator returns booking code + secure URL instructions.
10. TTS speaks final concise confirmation.

## 7) Non-Functional Requirements
- **Compliance:** no PII capture in-call; mandatory disclaimer.
- **Safety:** refuse investment advice and redirect to educational resources.
- **Latency:** keep turn responses short and deterministic.
- **Idempotency:** safe retries on MCP tools via operation keys.
- **Auditability:** correlated logs by session and booking code.

## 8) Suggested Repository Mapping
- `src/orchestration/` - conversation state machine and handlers
- `src/nlu/` - intent/entity extraction and response policy prompts
- `src/domain/booking/` - business rules, booking code, decisioning
- `src/integrations/mcp/` - FastMCP clients/tool contracts
- `src/voice/` - STT/TTS adapters (boundary only)
- `Docs/` - architecture, rules, scripts, delivery notes

## 9) Low-Level, Phase-wise Implementation Plan

This section defines concrete implementation details and test coverage expected in each phase.

### Phase 1 - Conversational Skeleton + Compliance Guardrails

#### Implementation Details
- Create `src/orchestration/state_machine.py`
  - `ConversationStage` enum:
    - `GREET`
    - `DISCLAIMER`
    - `INTENT_CAPTURE`
    - `TOPIC_CAPTURE`
    - `TIME_CAPTURE`
    - `SLOT_OFFER`
    - `CONFIRMATION`
    - `COMPLETION`
  - `advance(session_state, nlu_result)` function for deterministic stage transitions.
- Create `src/orchestration/session_store.py`
  - In-memory session model:
    - `session_id`
    - `current_stage`
    - `intent`
    - `topic`
    - `time_preference`
    - `selected_slot`
    - `timezone="IST"`
    - `policy_flags`
- Create `src/orchestration/prompt_templates.py`
  - Canonical response templates for:
    - disclaimer
    - topic clarification
    - time capture
    - two-slot offer
    - confirmation with IST repeat
    - secure-link completion message
- Create `src/orchestration/topic_catalog.py`
  - Allowed topics:
    - KYC/Onboarding
    - SIP/Mandates
    - Statements/Tax Docs
    - Withdrawals & Timelines
    - Account Changes/Nominee
- Create `src/orchestration/pii_guard.py`
  - Regex/heuristic checks for phone/email/account-like patterns.
  - Reject or redact user-provided sensitive values in session transcript.
- Create `src/orchestration/mock_calendar.py`
  - Static slot provider returning exactly two slots in IST.
- Keep external integration stubs only:
  - `src/integrations/mcp/stub_client.py` returns `NOT_ENABLED_IN_PHASE_1`.

#### Testing Details
- **Unit tests**
  - `tests/orchestration/test_state_machine.py`
    - Valid stage transitions.
    - Missing-topic and missing-time re-prompt behavior.
  - `tests/orchestration/test_pii_guard.py`
    - Phone/email/account strings are blocked/redacted.
  - `tests/orchestration/test_topic_catalog.py`
    - Supported topics accepted; unsupported topics rejected.
- **Integration tests**
  - `tests/integration/test_phase1_conversation_paths.py`
    - Simulated transcript for each intent:
      - book
      - reschedule
      - cancel
      - prepare
      - availability
    - Asserts no MCP call is attempted.
- **Acceptance tests**
  - Disclaimer appears before booking confirmation path.
  - IST time is repeated before final user confirmation.
  - Exactly two slots are offered in happy path.

### Phase 2 - Domain Logic + Booking Code + Slot Decisions

#### Implementation Details
- Create `src/domain/booking/models.py`
  - `BookingCommand`:
    - `action` (`hold|waitlist|reschedule|cancel`)
    - `topic`
    - `slot`
    - `booking_code`
    - `notes_entry`
    - `email_draft_payload`
  - `BookingDecision`:
    - `status` (`ready|needs_clarification|rejected`)
    - `reason`
    - `command` (optional)
- Create `src/domain/booking/code_generator.py`
  - Booking code format validator and generator:
    - Prefix `NL-`
    - Alphanumeric suffix length policy (for example 4 chars).
  - Collision check hook (in-memory initially; replaceable later).
- Create `src/domain/booking/validator.py`
  - Validate:
    - topic in whitelist
    - required fields per action
    - timezone normalization to IST
    - no PII in domain command payload
- Create `src/domain/booking/decision_engine.py`
  - Functions:
    - `decide_new_booking(...)`
    - `decide_reschedule(...)`
    - `decide_cancel(...)`
    - `decide_waitlist(...)`
  - Converts orchestrator inputs into canonical `BookingCommand`.
- Create `src/domain/booking/slot_selector.py`
  - Accepts candidate slots and user preference.
  - Returns best two options or empty list for waitlist branch.

#### Testing Details
- **Unit tests**
  - `tests/domain/test_code_generator.py`
    - Format, uniqueness, and collision retry behavior.
  - `tests/domain/test_validator.py`
    - Invalid topic, missing slot, and PII contamination rejection.
  - `tests/domain/test_decision_engine.py`
    - `hold`, `waitlist`, `reschedule`, `cancel` command generation.
- **Integration tests**
  - `tests/integration/test_orchestration_to_domain.py`
    - Ensures orchestrator delegates action creation to domain.
    - Confirms waitlist output when slot selection fails.
- **Acceptance tests**
  - Every supported action produces a complete `BookingCommand`.
  - Domain is the only source of booking-code generation.
  - No domain output includes restricted PII fields.

### Phase 3 - FastMCP Integration (Calendar, Docs, Gmail Draft)

#### Implementation Details
- Create `src/integrations/mcp/contracts.py`
  - Input/output schemas for:
    - calendar hold request/response
    - docs append request/response
    - gmail draft request/response
- Create `src/integrations/mcp/idempotency.py`
  - Operation-key generation:
    - Hash of (`session_id`, `action`, `booking_code`, `slot`).
  - Cache/replay strategy for duplicate requests.
- Create `src/integrations/mcp/retry_policy.py`
  - Retry transient errors with bounded exponential backoff.
  - No retry for validation/auth hard failures.
- Create `src/integrations/mcp/client.py`
  - `create_calendar_hold(command)`
  - `append_prebooking_log(command)`
  - `create_approval_gated_draft(command)`
  - Error normalization:
    - `IntegrationTransientError`
    - `IntegrationValidationError`
    - `IntegrationAuthError`
- Create `src/integrations/mcp/fastmcp_server/` tool wrappers:
  - `calendar_tool.py`
  - `docs_tool.py`
  - `gmail_tool.py`
- Enforce Google operation policies:
  - Calendar title: `Advisor Q&A - {Topic} - {Code}`
  - Docs append target: `"Advisor Pre-Bookings"`
  - Gmail action: draft-only, `approval_status=pending`

#### Testing Details
- **Unit tests**
  - `tests/integrations/test_contracts.py`
    - Schema validation for each tool payload.
  - `tests/integrations/test_idempotency.py`
    - Duplicate operation returns same logical result.
  - `tests/integrations/test_retry_policy.py`
    - Retries only on transient failures.
- **Integration tests**
  - `tests/integration/test_domain_to_mcp.py`
    - Domain command to MCP request mapping verification.
  - `tests/integration/test_google_wrappers.py`
    - Mocked Google API calls validate required fields and response mapping.
- **Acceptance tests**
  - Successful hold creation flow returns `event_id`.
  - Docs append returns `document_id` and `appended_range`.
  - Gmail draft returns `draft_id` and `approval_status=pending`.
  - No code path sends email directly.

### Phase 4 - Reliability, Observability, and Recovery

#### Implementation Details
- Create `src/observability/logger.py`
  - Structured logger with fields:
    - `timestamp`
    - `session_id`
    - `stage`
    - `intent`
    - `booking_code`
    - `error_type`
    - `latency_ms`
- Create `src/observability/metrics.py`
  - Counters:
    - `calls_total`
    - `calls_success`
    - `fallback_prompts_total`
    - `mcp_failures_total`
  - Histograms:
    - `turn_latency_ms`
    - `integration_latency_ms`
- Create `src/orchestration/fallback_policy.py`
  - Error-class to user-message mapping.
  - Re-prompt limit and graceful termination behavior.
- Create `src/domain/booking/compensation.py`
  - Partial-failure handlers:
    - hold created, docs failed
    - hold + docs success, gmail failed
  - Recovery action queue (for deferred retries/manual follow-up).
- Create `src/observability/audit_trail.py`
  - Correlate each call with final artifact status:
    - calendar_status
    - docs_status
    - gmail_status

#### Testing Details
- **Unit tests**
  - `tests/observability/test_logger_fields.py`
    - Required log keys present.
  - `tests/orchestration/test_fallback_policy.py`
    - Correct user-facing fallback prompts for each error class.
  - `tests/domain/test_compensation.py`
    - Partial-write recovery strategy selection.
- **Integration tests**
  - `tests/integration/test_failure_scenarios.py`
    - STT error
    - NLU parse failure
    - domain validation failure
    - MCP timeout/transient failure
- **Acceptance tests**
  - Each failed session has complete trace entries by `session_id`.
  - User receives safe message for every known failure class.
  - Partial integration failures are recoverable and visible in audit output.

### Phase 5 - Voice UX Tuning + Demo Readiness

#### Implementation Details
- Create `src/voice/response_style.py`
  - Response constraints:
    - concise turn length policy
    - confirmation-first formatting
    - no jargon and no policy leakage
- Create `src/voice/script_builder.py`
  - Generate and maintain script artifacts in `Docs/`:
    - opening prompts
    - clarification prompts
    - confirmations
    - refusal responses
    - completion prompts
- Create `src/voice/tts_formatter.py`
  - Improve spoken clarity:
    - slow spelling for booking code
    - explicit date-time phrasing in IST
- Create `Docs/Script.md` (or equivalent) as the canonical demo script.
- Ensure README documents:
  - mock slot JSON source
  - reschedule/cancel behavior
  - artifact generation and verification steps

#### Testing Details
- **Unit tests**
  - `tests/voice/test_response_style.py`
    - Turn length and compliance phrase requirements.
  - `tests/voice/test_tts_formatter.py`
    - Booking-code and IST phrasing format checks.
- **Integration tests**
  - `tests/integration/test_end_to_end_voice_flow.py`
    - Full simulated call from greeting to completion with artifact checks.
  - `tests/integration/test_prepare_intent_flow.py`
    - "What to prepare" intent does not trigger booking artifacts unless requested.
- **Acceptance tests**
  - Live/demo call is understandable, concise, and policy-compliant.
  - Required evidence artifacts are generated and reproducible:
    - calendar hold proof
    - docs log proof
    - gmail draft proof
    - call demo recording or link

## 10) Cross-Phase Test Strategy

### Test Suite Structure
- `tests/unit/` for deterministic logic:
  - state machine
  - validators
  - formatters
  - idempotency/retry logic
- `tests/integration/` for boundary handoffs:
  - Orchestration <-> NLU
  - Orchestration <-> Domain
  - Domain <-> MCP
- `tests/e2e/` for complete conversational journeys with mocked STT/TTS and sandboxed integrations.

### Quality Gates per Phase
- Unit tests for new modules must pass before moving phases.
- Integration tests for touched boundaries are mandatory.
- No phase is complete unless its acceptance tests pass.
- Regression suite must include:
  - one happy-path booking
  - one no-slot waitlist
  - one reschedule
  - one cancel
  - one policy refusal (investment advice)

### Recommended CI Sequence
1. Lint + static checks
2. Unit tests
3. Integration tests
4. E2E smoke tests (mock integrations for PR; real sandbox optional for nightly)
5. Artifact contract validation (Calendar/Docs/Gmail response schema checks)
