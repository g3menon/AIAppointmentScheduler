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
`Chat Input (tests / programmatic API)`  
-> `Conversation Orchestration`  
-> `NLU/LLM Layer`  
-> `Booking Domain Service`  
-> `MCP Integration Layer (FastMCP + Google APIs)`  
-> `Chat Output`

### 2.2 Phase 5 — Web Chat UI (Node.js) for Manual QA
**Purpose:** ship a browser chat surface **before** voice so stakeholders can exercise the full text flow (disclaimer, booking, MCP trio) without pytest or ad-hoc scripts.

- **Stack:** lightweight **Node** dev server (e.g. Vite) serving static UI + hot reload; UI calls a **Python HTTP chat API** that wraps the existing `post_message(session_id, text)` contract (same orchestration as tests).
- **Voice entry (later):** after **Phase 6** (STT/TTS), add a **voice mode** (toggle, tab, or route) in the **same** web app that streams or posts audio to STT, feeds transcript text into the same orchestrator path, and plays TTS for assistant replies — no duplicate business logic.

### 2.3 Later Runtime (Phase 6+): Voice Over Chat Runtime
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
   - Does not call Google HTTP APIs with ad-hoc prompts. When `GEMINI_API_KEY` is configured (and tests are not running), **confirmed booking** may use Gemini **automatic function calling** so the model issues the same named MCP operations as FastMCP (`calendar_create_hold`, `docs_append_prebooking`, `gmail_create_draft`). The orchestrator supplies **canonical arguments**; tool implementations are shared with the FastMCP server via `dispatch_mcp_tool` → `GoogleMcpClient`. Set `BOOKING_MCP_DRIVER=direct` to skip the LLM and invoke Google directly.

4. **Booking Domain Service**
   - Central business rules and policy checks.
   - Validates no PII fields, valid topics, confirmation prerequisites.
   - Generates booking code.
   - Emits canonical booking commands: `hold|waitlist|reschedule|cancel`.

5. **MCP Integration Layer (FastMCP Server + shared dispatch)**
   - Exposes wrapped Google tools (FastMCP names align with Gemini tool names):
     - `calendar_create_hold`
     - `docs_append_prebooking`
     - `gmail_create_draft`
   - `src/integrations/google_mcp/mcp_tool_dispatch.dispatch_mcp_tool` is the single path to `GoogleMcpClient` for both the MCP server and LLM-driven booking execution (`booking_mcp_executor.run_booking_mcp_triplet`).
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

## Phase 1 - Chat Runtime Skeleton + Compliance + Real Google MCP
**Objective:** functional chat-first booking workflow with the same operational artifacts described in `Docs/Description.md`, using **real Google APIs** behind the MCP tool surface (not in-process fakes).

**Implementation Details**
- Build chat/session orchestration (Phase 1 code lives under `Phases/phase_1_chat_runtime/` as package `phase1`):
  - state machine stages through disclaimer, intent/topic/time capture, two-slot offer, explicit yes/no confirmation, then completion.
  - fallback/re-prompt handlers.
- Build compliance guards:
  - topic whitelist.
  - no-PII prompt/validation guard.
  - investment-advice refusal templates.
- Mock **slot offering** only (two deterministic IST options); calendar **holds** for the chosen slot are created via Google Calendar at confirmation.
- **MCP integration (real):** after the user confirms the slot, the runtime must invoke (in order, with idempotency keys):
  1. **Google Calendar** — tentative hold (`Advisor Q&A - {Topic} - {Code}`).
  2. **Google Docs** — append a policy-safe pre-booking log line to the configured document (`GOOGLE_PREBOOKING_DOC_ID`).
  3. **Gmail** — create an **approval-gated draft only** to `ADVISOR_EMAIL_TO` (never auto-send).
- Booking codes for Phase 1 use the shared generator (`src.domain.booking_code_generator`) until Phase 2 domain extraction is complete.
- Execution is centralized in `src/integrations/google_mcp/booking_mcp_executor.py`: **pytest**, missing `GEMINI_API_KEY`, or `BOOKING_MCP_DRIVER=direct` → direct `dispatch_mcp_tool` calls; otherwise Gemini automatic function calling drives the same three tools with orchestrator-built payloads.
- FastMCP server tools in `src/integrations/google_mcp/server.py` use the same `dispatch_mcp_tool` path as the chat runtime so CLI/MCP and in-app behavior stay aligned.

**Testing Details**
- Unit:
  - state transitions.
  - topic whitelist.
  - PII detector.
- Integration / E2E:
  - chat handler -> orchestrator session flow; all 5 intents in chat mode.
  - **Automated tests** use an in-memory **call recorder** (not Google) when `PYTEST_CURRENT_TEST` is set so CI stays credential-free.
  - **Manual / sandbox verification:** run the same flow with a filled `.env` and confirm hold, doc append, and draft in Google.

**Definition of Done**
- All 5 intents work in chat mode.
- Disclaimer is always shown before booking progression.
- Date/time repeated in IST before final confirmation.
- On confirmed booking, Calendar hold + Docs append + Gmail draft succeed against real Google when credentials and resource IDs are configured.

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

## Phase 5 - Web Chat UI (Node.js) + HTTP Chat API
**Objective:** browser-based manual testing of the Phase 1–4 chat runtime **before** integrating voice; same session/orchestrator/MCP behavior as automated tests.

**Implementation Details**
- **Python:** expose a small **HTTP API** (e.g. FastAPI) that forwards `POST /api/chat/message` to `phase1.api.chat.routes.post_message` (body: `session_id`, `text`); enable **CORS** for local Node dev origin.
- **Node:** `web/chat-ui/` — Vite (or equivalent) single-page chat: message list, text input, send to Python API via `fetch` (env-based base URL, e.g. `VITE_CHAT_API_URL`).
- **Security (dev):** bind API to localhost by default; do not expose raw `.env` to the browser; no secrets in front-end bundles.
- **Future hook:** reserve UI space or routing for **Phase 6 voice** (mic control, playback) without changing orchestrator contracts.

**Testing Details**
- Manual: full booking transcript in browser; with `.env` configured, confirm Calendar/Docs/Gmail draft side effects.
- Automated (optional): smoke test HTTP handler with `TestClient` or Playwright against local stack.
- Regression: existing **pytest** chat/orchestrator suites remain the primary CI gate; Web UI does not replace them.

**Definition of Done**
- Developer can run API + `npm run dev` and complete a booking conversation in the browser.
- Assistant messages and session state match expectations for the same turns as integration tests.
- Documentation lists exact run commands (see repository mapping below).

## Phase 6 - Voice Adapters (Chat <-> Voice Bridge)
**Objective:** add voice without changing core behavior; **surface voice from the Phase 5 Web UI** after STT/TTS are available.

**Implementation Details**
- Build `src/voice/` (or `src/integrations/voice/` per repo layout):
  - `stt_adapter.py` (audio -> normalized text input).
  - `tts_adapter.py` (chat response text -> speech output).
  - `chat_voice_bridge.py` for adapter orchestration.
  - `tts_formatter.py` for speaking clarity (booking code/date-time).
- **Web UI:** extend `web/chat-ui/` with voice controls that call STT → same `Orchestrator.handle` text path → TTS for each assistant line (or merged prompt), reusing compliance/PII behavior.
- Ensure parity:
  - Voice path reuses chat runtime exactly.
  - No duplicated domain or integration logic in voice modules.

**Testing Details**
- Unit:
  - STT/TTS adapter normalization.
  - booking code/date-time spoken formatting.
- Integration:
  - same scenario in chat (text UI) and voice yields equivalent domain command/artifacts.
- E2E:
  - simulated voice flow (STT -> chat runtime -> TTS) and/or browser voice mode against local stack.

**Definition of Done**
- Voice path works via chat runtime bridge with behavior parity.
- Chat (text) and voice produce equivalent business outcomes for same intent input.
- Voice is reachable from the **same** Web UI built in Phase 5.
- Demo artifacts are reproducible.

## 6) Cross-Phase Test Strategy

### 6.1 Test Suite Structure
- `tests/unit/`: deterministic logic (state machine, validators, formatters, retry/idempotency).
- `tests/integration/`: boundary handoffs (chat<->orchestration, orchestration<->domain, domain<->MCP, chat<->voice bridge).
- `tests/e2e/`:
  - Phases 1-4: chat-only journeys.
  - Phase 5: optional browser smoke against HTTP API + Node UI (manual or automated).
  - Phase 6 onward: chat + voice parity journeys (including voice entry from Web UI).

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
- chat-vs-voice outcome parity (from Phase 6 onward)

### 6.4 Recommended CI Sequence
1. Lint + static checks
2. Unit tests
3. Integration tests
4. E2E smoke tests (chat-only for Phases 1-4; optional Web UI smoke in Phase 5; include voice from Phase 6)
5. Contract validation for Calendar/Docs/Gmail MCP payloads

## 7) Suggested Repository Mapping
- `Phases/phase_1_chat_runtime/src/phase1/` - Phase 1 orchestrator, session store, `post_message` chat routes
- `src/api/http/` - **Phase 5** FastAPI (or equivalent) HTTP wrapper for `post_message` (CORS for local Web UI)
- `web/chat-ui/` - **Phase 5** Node (Vite) browser chat client; **Phase 6** voice controls layered here
- `src/api/chat/` - re-exports Phase 1 chat surface for Python imports
- `src/orchestration/` - conversation state machine and handlers (later-phase consolidation)
- `src/nlu/` - intent/entity extraction and policy prompts
- `src/domain/booking/` - booking rules, codes, decisioning
- `src/integrations/mcp/` - FastMCP clients and contracts
- `src/voice/` or `src/integrations/voice/` - STT/TTS adapters (**Phase 6**)
- `tests/` - unit/integration/e2e suites
- `Docs/` - architecture, rules, scripts, and delivery notes

**Local run (Phase 5):** from repo root, start Python API (e.g. `uvicorn src.api.http.chat_app:app --reload --port 8000`) and in `web/chat-ui/` run `npm install` && `npm run dev` (Vite default port proxied or `VITE_CHAT_API_URL` pointing at the API).
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

## Phase 1 - Conversational Skeleton + Compliance Guardrails + Real Google MCP
**Objective:** Safe chat flow end-to-end with **real** Calendar hold, Docs log append, and Gmail **draft** (aligned with `Docs/Description.md`), after explicit user confirmation.

**Scope**
- Implement orchestrator states and transitions.
- Add mandatory disclaimer and refusal behavior.
- Add topic whitelist and no-PII checks.
- Mock slot offering only (two slots from static data); perform Google writes at confirmation via `GoogleMcpClient`.

**Exit Criteria**
- Chat supports all 5 intents at conversational level.
- Confirm/repeat date-time in IST before final confirmation.
- On “yes” after slot selection: Calendar hold + Docs append + Gmail draft created (draft-only; no send).

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

## Phase 5 - Web Chat UI (Node.js) + HTTP Chat API
**Objective:** Browser-based manual QA of the chat runtime before voice.

**Scope**
- Python HTTP API wrapping `post_message` with CORS for local development.
- Node/Vite chat UI under `web/chat-ui/` calling the API.
- Documented two-process dev workflow (API + `npm run dev`).

**Exit Criteria**
- Full booking flow can be completed in the browser with the same behavior as programmatic tests.
- No orchestrator or MCP logic duplicated in the front-end.

## Phase 6 - Voice Adapters + Web UI Voice Mode
**Objective:** STT/TTS on the same orchestrator path; expose voice from the Phase 5 Web UI.

**Scope**
- `src/voice/` (or `src/integrations/voice/`) adapters only.
- Extend `web/chat-ui/` with mic/playback (or equivalent) wired to STT → text chat path → TTS.
- Demo readiness: scripts, TTS formatting for booking codes/IST, optional `Docs/Script.md`.

**Exit Criteria**
- Text and voice modes produce parity outcomes for the same intents.
- Voice is reachable from the same web app as Phase 5 text chat.

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
- `Phases/phase_1_chat_runtime/src/phase1/` - Phase 1 orchestrator, session store, `post_message`
- `src/api/http/` - Phase 5 FastAPI chat bridge
- `web/chat-ui/` - Phase 5 Node/Vite browser UI; Phase 6 voice controls
- `src/orchestration/` - conversation state machine and handlers (later consolidation)
- `src/nlu/` - intent/entity extraction and response policy prompts
- `src/domain/booking/` - business rules, booking code, decisioning
- `src/integrations/mcp/` - FastMCP clients/tool contracts
- `src/voice/` - STT/TTS adapters (Phase 6 boundary)
- `Docs/` - architecture, rules, scripts, delivery notes

## 9) Low-Level, Phase-wise Implementation Plan

This section defines concrete implementation details and test coverage expected in each phase.

### Phase 1 - Conversational Skeleton + Compliance + Real Google MCP

#### Implementation Details
- **Package layout:** Phase 1 chat runtime is implemented under `Phases/phase_1_chat_runtime/src/phase1/` (orchestrator, prompts, PII guard, topic catalog, in-memory session store, chat routes).
- **State machine:** maps to Architecture §11.5 states (`GREET`, `DISCLAIMER_AWAIT_ACK`, intent routing, `BOOK_TOPIC`, `BOOK_TIME_PREFERENCE`, `BOOK_OFFER_SLOTS`, `BOOK_CONFIRM`, `CLOSE`, plus reschedule/cancel/prepare/availability branches).
- **Mock slot source:** `MockCalendarService` returns exactly two IST-labeled slots; UTC instants on each `TimeSlot` feed Calendar API `start`/`end`.
- **Real Google MCP (shared implementation):** `src/integrations/google_mcp/client.py` (`GoogleMcpClient`) performs:
  - Calendar `events.insert` tentative hold with title `Advisor Q&A - {Topic} - {Code}` and private extended property carrying an idempotency key.
  - Docs `documents.batchUpdate` append of a **policy-safe** log line (topic, IST slot label, booking code, action type) — **no user free text**.
  - Gmail `users.drafts.create` — **draft only** to `ADVISOR_EMAIL_TO`.
- **FastMCP:** `src/integrations/google_mcp/server.py` tools call the same `GoogleMcpClient` methods for MCP-driven invocations.
- **Booking code:** Phase 1 uses `src.domain.booking_code_generator.BookingCodeGenerator` until Phase 2 domain owns codes exclusively.
- **Credentials:** OAuth refresh token or service account JSON via environment variables (see `.env.example`).

#### Testing Details
- **Unit tests** (`Phases/phase_1_chat_runtime/tests/unit/`): state transitions, PII guard, topic catalog.
- **Integration / E2E** (`Phases/phase_1_chat_runtime/tests/integration`, `.../e2e`): full transcripts per intent; **pytest** uses `RecordingGoogleMcpClient` (in-memory) automatically when `PYTEST_CURRENT_TEST` is set — not a substitute for production Google behavior, only for CI.
- **Manual acceptance:** with valid `.env`, run a booking through chat and verify the three Google artifacts.
- **Acceptance tests**
  - Disclaimer appears before booking confirmation path.
  - IST time is repeated before final user confirmation.
  - Exactly two slots are offered in happy path.
  - After “yes”, three MCP operations are invoked (Calendar, Docs, Gmail draft).

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

### Phase 5 - Web Chat UI (Node.js) + HTTP Chat API

#### Implementation Details
- Create `src/api/http/chat_app.py` (FastAPI recommended):
  - `POST /api/chat/message` with JSON `{ "session_id": string, "text": string }` → returns same shape as `post_message` (messages, state, session snapshot).
  - `GET /api/health` for readiness checks.
  - CORS middleware allowing `http://localhost:5173` (Vite default) and configurable extra origins via environment if needed.
- Bootstrap `sys.path` so imports resolve `phase1` and top-level `src` when launched via `uvicorn` from repo root.
- Create `web/chat-ui/`:
  - `package.json` with Vite dev server; static chat UI (message thread + input).
  - Environment variable for API base URL (e.g. `VITE_CHAT_API_URL=http://127.0.0.1:8000`).
  - Optional Vite proxy from `/api` → Python API to avoid CORS during dev.
- Do **not** embed secrets in the front-end; browser only sends user text and `session_id`.

#### Testing Details
- **Manual acceptance**
  - Run API + Vite; complete disclaimer → book → confirm → verify three MCP writes when Google is configured (or recorder under test).
- **Optional automated**
  - HTTP `TestClient` test for `/api/chat/message` returning 200 and non-empty messages for `"hello"`.
- **Regression**
  - Phase 1 `pytest` suites unchanged and mandatory in CI.

### Phase 6 - Voice Adapters + Web UI Voice Mode

#### Implementation Details
- Create `src/voice/response_style.py` (or under `src/integrations/voice/`)
  - Response constraints: concise turns, confirmation-first, no policy leakage.
- Create `src/voice/script_builder.py` and `Docs/Script.md` (or equivalent) for demo scripts.
- Create `src/voice/tts_formatter.py`
  - Spoken clarity: booking code spelling, explicit IST date-time phrasing.
- Wire STT/TTS into `web/chat-ui/` (voice toggle) so audio never bypasses `Orchestrator.handle` text contract.

#### Testing Details
- **Unit tests**
  - `tests/voice/test_response_style.py`, `tests/voice/test_tts_formatter.py`
- **Integration tests**
  - `tests/integration/test_end_to_end_voice_flow.py` (simulated STT text → orchestrator → TTS payload).
  - Parity: same transcript as typed chat yields same booking artifacts.
- **Acceptance tests**
  - Voice mode in browser (post Phase 6) matches text chat outcomes; demo artifacts reproducible.

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

## 11) Low-Level Completeness Addendum (Chat-First, Implementation-Critical)

This addendum preserves all existing architecture details and adds missing low-level elements required for implementation parity with the chat-first execution model.

### 11.1 Chat-First Invariant and Runtime Contract
- **Implementation rule:** Ship full chat before any audio path.
- **Single core API contract:** `Orchestrator.handle(user_text, session) -> AgentTurn`
  - `AgentTurn.messages: list[str]` (one or more assistant text messages).
  - `AgentTurn.side_effects: list[SideEffect]` (internal operations queue).
- **Adapter invariant:** Voice is an adapter only:
  - STT maps audio -> `user_text`.
  - Each `AgentTurn.messages[i]` is sent to TTS in order.
  - Orchestrator, NLU, domain, and Google MCP code are unchanged when voice is added.

### 11.2 Cross-Cutting Conventions (Mandatory)
- **Time model**
  - Store `Instant` in UTC for persistence and integrations.
  - Store/compute display timezone as `ZoneId("Asia/Kolkata")`.
  - Use one injectable `Clock` in all domain/session logic for deterministic tests.
- **Identifiers**
  - `session_id`: UUID.
  - `correlation_id`: per request/turn, propagated through logs and MCP tool calls.
- **Idempotency**
  - Booking hold idempotency key: `booking:{code}` (or hash of `code + slot_start_utc`).
  - Retries must never duplicate external side effects.
- **Configuration**
  - Environment-driven config for:
    - Google OAuth/service account credentials.
    - Gemini (or equivalent) NLU API key.
    - Secure link base template.
    - Voice adapter enablement flags (default disabled).
  - Secrets must be loaded from `.env` and `.env` remains gitignored.

### 11.3 Recommended Repository Seams (Monolith-First)
Use these seams even if framework/library choices differ:

- `src/domain/` pure business/domain objects and rules.
- `src/session/` orchestrator, state machine, session context, session store.
- `src/nlu/` prompting, parsing, policy flags, PII-aware preprocessing.
- `src/integrations/google_mcp/` FastMCP server + real and fake tool adapters.
- `src/integrations/voice/` STT/TTS wrappers only (phase-gated).
- `src/api/http/` HTTP chat API for **Phase 5** Web UI (`post_message` wrapper).
- `web/chat-ui/` Node/Vite UI (**Phase 5** text; **Phase 6** voice controls).
- `src/api/chat/` Python re-exports Phase 1 chat routes.
- `src/api/voice/` optional real-time audio bridge (late Phase 6+ as needed).
- `tests/unit/` and `tests/integration/` with chat-first as the default regression gate.

### 11.4 Domain Completeness Additions
- **Closed enums**
  - `Topic`: strict keys matching problem statement and MCP title formatting.
  - `Intent`: `book_new | reschedule | cancel | what_to_prepare | check_availability | unknown`
  - `AdvisorDisclaimerStatus`: `pending | acknowledged`
- **DTO expectations**
  - `TimeSlot` includes `start_utc`, `end_utc`, and `label_ist` (render-safe for chat/TTS parity).
  - `BookingPreference` includes normalized date/time window plus original user phrase (sanitized in logs).
  - `BookingRecord` stores code/topic/slot/status (`tentative|waitlisted|cancelled`) and `created_at_utc`.
- **Booking code behavior**
  - Pattern target: `[A-Z]{2}-[A-Z][0-9]{3}` (configurable).
  - Collision retry cap (example: 5).
  - Add `to_spelling(code)` helper for voice-only readout path without altering chat value.
- **Slot provider behavior**
  - `findTwoSlots(...)` returns 0-2 slots, with deterministic test mode.
  - Empty list must route to waitlist in orchestrator (not inside slot finder).
  - Optional `holdWaitlistSlot(...)` for synthetic marker slot when PM flow requires.

### 11.5 Session/State Machine Completeness Additions
- **Full low-level state set**
  - `GREET`
  - `DISCLAIMER_AWAIT_ACK`
  - `INTENT_ROUTING`
  - `BOOK_TOPIC`
  - `BOOK_TIME_PREFERENCE`
  - `BOOK_OFFER_SLOTS`
  - `BOOK_CONFIRM`
  - `BOOK_EXECUTE_MCP`
  - `CLOSE`
  - `RESCHEDULE_COLLECT_CODE`
  - `RESCHEDULE_OFFER_SLOTS`
  - `CANCEL_COLLECT_CODE`
  - `CANCEL_CONFIRM`
  - `PREPARE_TOPIC_OR_GENERIC`
  - `AVAILABILITY_QUERY`
  - `ERROR_RECOVER`
- **SessionContext fields**
  - `state`, `disclaimer`, `intent`, `preference`, `offered_slots`, `selected_slot`
  - `pending_booking_code`, `last_mcp_error`, `turn_count`, `advice_redirect_count`
- **Turn execution model**
  - Run PII gate first.
  - Run advice-policy gate second.
  - Run NLU parse third.
  - Compute state transition and enqueue side effects.
  - Commit state, then execute side effects in order.
  - On MCP failure: transition to recovery state and emit user-safe retry/handoff message.

### 11.6 NLU Contract and Resolver Pipeline Additions
- **Strict structured NLU output**
  - `intent`, `topic`, `date_phrase`, `time_window`, `booking_code_guess`, `wants_investment_advice`, `confidence`
- **Resolver chain**
  - `RelativeDateResolver(date_phrase, today_ist) -> LocalDate | needs_clarification`
  - `TopicMapper` with fuzzy threshold and explicit clarification prompt below threshold.
  - `IntentPolicy` with confidence threshold and bounded clarification loops per state.
- **Prompt context packaging**
  - Include current state name + last assistant question + recent transcript context.
  - Enforce "JSON-only" output mode for parser stability.

### 11.7 Google MCP + Google API Backing Additions
- **FastMCP tool surface (in-process server)**
  - `calendar_create_hold(...) -> external_event_id`
  - `calendar_delete_hold(...)`
  - `docs_append_prebooking(...)`
  - `gmail_create_draft(...) -> draft_id` (never auto-send)
- **Google API clients**
  - Calendar: `build("calendar", "v3")`
  - Docs: `build("docs", "v1")`
  - Gmail: `build("gmail", "v1")`
- **Operational policy**
  - Per-tool timeout budgets (calendar 5-10s; docs/gmail ~5s).
  - Single retry for transient network failures.
  - Structured logs include `correlation_id`, tool name, latency, success/failure.
  - Avoid logging full sensitive bodies where unnecessary.
- **CI-safe fakes**
  - `FakeCalendarMcp`, `FakeNotesMcp`, `FakeEmailMcp` using same signatures as production tools.
  - CI integration tests must default to fakes and require no cloud credentials.

### 11.8 Missing Late-Phase Delivery Detail (Phases 6-8)
- **Phase 6: Voice adapters + Web UI voice mode**
  - STT/TTS boundary only; same `Orchestrator.handle` contract; expose voice from `web/chat-ui/`.
- **Phase 7: Secondary intent subgraphs**
  - Reschedule, cancel, what-to-prepare, and availability flows fully integrated through chat API (text and, where applicable, voice).
- **Phase 8: Hardening and operations**
  - Correlation-friendly logging with transcript redaction policy.
  - Session rate limits and TTL cleanup.
  - Runbook for MCP outage degraded mode and failure-injection coverage.

### 11.9 Traceability Matrix (Requirement -> Implementation)
- **Five intents** -> Intent enum + state branches + integration tests.
- **Disclaimer + topic list + IST** -> disclaimer states + topic catalog + IST formatter.
- **Two-slot offering** -> slot provider + offer state + deterministic tests.
- **Booking code + Calendar/Docs/Gmail** -> booking execution use case + MCP trio.
- **No PII** -> front-door PII gate + NLU/domain constraints + redacted logging.
- **No investment advice** -> policy gate + static educational redirects.
- **Waitlist + email draft** -> empty-slot branch + draft creation path.
- **Secure URL output** -> config template consumed at close state.
- **Web text QA** -> Phase 5 `web/chat-ui/` + `src/api/http/chat_app.py` calling `post_message`.
- **Voice UX** -> Phase 6 STT/TTS adapters with unchanged orchestrator contract; entry from the same Web UI.

### 11.10 PII Zero-Retention Policy (Non-Negotiable)
This system must not collect or store PII at any stage (chat, voice, logs, analytics, or Google artifacts).

- **PII denylist scope**
  - Direct identifiers: full name, phone number, email, postal address, account/folio number, PAN/Aadhaar/tax IDs, DOB.
  - Sensitive free text patterns and obvious variants (with spaces, separators, masking, or OCR/STT noise).
- **Input-time rejection**
  - Run `PiiGuard` before NLU parsing and before state transition on every turn.
  - If PII detected: return fixed safe response with secure external handoff link and do not process user text further in that turn.
  - Never ask users for PII in prompts, clarifications, or confirmations.
- **State and storage constraints**
  - `SessionContext` and `BookingRecord` are PII-free by schema.
  - Disallow raw transcript persistence by default in production.
  - If temporary transcript buffering is required for debugging, store redacted text only and enforce strict TTL.
- **Logging and observability**
  - Apply redaction before any log write.
  - Logs must contain only metadata (`session_id`, `correlation_id`, state, intent, status, latency) and never raw user input.
  - Redaction is mandatory for chat text, STT text, errors, and third-party exception payloads.
- **NLU and model boundaries**
  - NLU prompt builder must pass sanitized transcript only.
  - Disable provider-side data retention where configurable.
  - NLU structured output must not include PII fields; parser rejects responses containing disallowed keys/patterns.
- **MCP/Google artifact constraints**
  - Calendar title/body, Docs append lines, and Gmail drafts must use only topic, slot label, booking code, and policy-safe template text.
  - Never include user-entered free text in Google artifacts.
  - Pre-send validator blocks any artifact payload that matches PII rules.
- **Voice-specific controls**
  - STT partial/final transcripts are treated as sensitive input and pass through the same `PiiGuard`.
  - Do not persist raw audio or raw transcript in production unless explicitly approved; default is disabled.
  - TTS should never speak back suspected PII.
- **Testing and release gates**
  - Unit tests for `PiiGuard` and redaction with adversarial pattern variants.
  - Integration tests asserting no PII reaches session store, logs, MCP payloads, or email drafts.
  - Add CI gate that fails build if forbidden fields/patterns appear in fixtures, logs, or serialized artifacts.
  - Add periodic audit test using synthetic PII injections across all intents (book/reschedule/cancel/prepare/availability).

### 11.11 PII Controls Mapped to Delivery Phases
- **Phase 1 (chat skeleton):** add `PiiGuard` before NLU/state transitions; block and redirect on detection; prompts never request identifiers.
- **Phase 2 (domain decisioning):** enforce PII-free domain schemas and reject contaminated command payloads.
- **Phase 3 (MCP integration):** validate outbound Calendar/Docs/Gmail payloads to prevent any user free text or identifier leaks.
- **Phase 4 (observability):** apply redaction-before-write for logs/audit/telemetry; store metadata-only traces.
- **Phase 5 (Web UI):** browser must not persist raw transcripts in `localStorage`/analytics by default; use HTTPS in non-local deployments; never ship API keys or Google credentials to the client.
- **Phase 6 (voice + TTS):** scripts and TTS formatting do not elicit or repeat PII; STT partial/final transcripts use the same `PiiGuard` as chat; disable raw audio retention by default.
- **Phase 7 (secondary intents):** reschedule/cancel identity checks rely on booking code only; no alternate personal verification fields.
- **Phase 8 (hardening/ops):** add CI/runtime PII audits and failure-injection checks proving PII-safe degraded behavior.
