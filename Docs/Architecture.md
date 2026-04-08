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
