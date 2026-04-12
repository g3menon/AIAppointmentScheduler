# AI Appointment Scheduler - Low-Level Architecture and Phase Execution Plan

## 1) Objective and Runtime Invariants

### 1.1 Product objective
Build a compliant appointment assistant that:
- supports five user intents: book, reschedule, cancel, what-to-prepare, availability
- enforces disclaimer and no-PII behavior
- creates booking artifacts through MCP integrations:
  - Google Calendar tentative hold
  - Google Docs pre-booking append
  - Gmail draft (approval-gated, never auto-send)

### 1.2 Non-negotiable invariants
- **Single business path**: all user input (typed or voice) must flow through the same orchestrator/domain/MCP path.
- **Adapter-only voice**: STT/TTS and UI voice controls cannot contain domain logic.
- **No PII collection** in prompts, stored session fields, logs, and artifacts.
- **Idempotent side effects** for Calendar/Docs/Gmail writes.
- **IST clarity** on offered and confirmed slots.

---

## 2) Runtime Architecture (Implemented Shape)

### 2.1 Authoritative flow
`User input (text or STT transcript)`  
-> `Orchestrator state machine`  
-> `Domain command generation/validation`  
-> `MCP execution (Calendar/Docs/Gmail)`  
-> `Assistant response (text + optional TTS)`

### 2.2 Layer boundaries
1. **Orchestrator (`phase1.session.orchestrator`)**
   - state transitions
   - disclaimer/intent/topic/time/slot/confirm handling
   - reprompts and safe fallbacks
2. **Domain (`src.domain.*`)**
   - booking decisions and booking-code lifecycle
   - command shape for hold/waitlist/reschedule/cancel
3. **MCP integration (`src.integrations.google_mcp.*`)**
   - dispatch, tool execution, retries, idempotency
4. **Voice adapters (`Phases/phase_7_voice_adapters/src/phase7`)**
   - STT ingress, TTS egress, voice bridge
5. **UI/API transport**
   - API wrapper: `src/api/http/chat_app.py`
   - browser app: `web/chat-ui/src/main.js`

---

## 3) Current Behavioral Contracts (Must Match Code)

### 3.1 Conversation opening
- first turn includes greeting and informational disclaimer
- action choices are surfaced as clickable options immediately
- user can proceed directly if intent is clear at early turns

### 3.2 Slot behavior
- offered slots are generated relative to current date (future offsets), not static past dates
- two slot options are offered in booking and reschedule flows
- slot selection accepts:
  - numeric choices (`1`, `2`)
  - spoken variants (`one`, `first`, `slot 1`, `two`, `second`, `slot 2`)
  - fuzzy full-slot text (format and punctuation tolerant)

### 3.3 Voice mode behavior (web UI)
- mic is toggle-on/toggle-off (not hold-to-talk)
- voice loop is continuous turn-taking:
  - listen -> transcript -> API/orchestrator -> text response -> TTS -> listen again
- in voice mode, assistant replies are both visible text and spoken output
- user speech can interrupt active TTS playback (barge-in)

---

## 4) Low-Level Data Contracts

### 4.1 Session state (logical)
- `session_id`
- `state` / `current_stage`
- `intent`
- `topic`
- `time_preference`
- `offered_slots`
- `selected_slot`
- `booking_code`
- sanitized transcript metadata

### 4.2 Domain command (domain -> integrations)
- `action` (`hold|waitlist|reschedule|cancel`)
- `topic`
- `slot`
- `booking_code`
- `notes_entry`
- `email_draft_payload`

### 4.3 API contract (`POST /api/chat/message`)
- request: `{ "session_id": str, "text": str }`
- response includes:
  - `messages`
  - `state`
  - `session`
  - `quick_replies`
  - `intent_preview`
  - `booking_summary` (when applicable)

---

## 5) Phase-by-Phase Implementation (Executed + Planned)

## Phase 1 - Chat Runtime Skeleton + Compliance + MCP Wiring
### Implemented scope
- orchestrator state machine in `Phases/phase_1_chat_runtime/src/phase1/session/orchestrator.py`
- disclaimer, PII guard, investment-advice refusal templates
- booking flow: topic -> time preference -> two-slot offer -> confirm -> close
- chat route in `phase1.api.chat.routes.post_message`
- Google MCP path integration through shared dispatch/executor modules

### Required tests
- state machine unit coverage
- booking happy path integration/e2e
- no-PII and refusal behavior checks

### Done criteria
- all five intents reachable in chat path
- IST shown before confirmation
- confirmed booking triggers Calendar + Docs + Gmail draft path

---

## Phase 2 - Domain Decisioning
### Implemented scope
- booking command/decision centralization in domain layer
- booking code generation ownership moved to domain path
- waitlist/no-slot decision support

### Required tests
- domain validation, command generation, and code generation
- orchestration-to-domain handoff integration tests

---

## Phase 3 - MCP Integration Contracts/Idempotency
### Implemented scope
- tool dispatch + execution wrappers for Calendar/Docs/Gmail
- idempotency key usage and retry envelope behavior
- error normalization from provider/tool failures

### Required tests
- contract mapping tests
- duplicate-call safety tests
- integration failure-path tests

---

## Phase 4 - Reliability + Observability
### Implemented scope
- structured logging with session/stage/intent/latency/error context
- audit hooks for artifact status
- fallback/recovery behavior for partial integration failures

### Required tests
- log field and fallback mapping tests
- partial-failure recovery tests

---

## Phase 5 - Web Chat UI + HTTP API
### Implemented scope
- HTTP wrapper around chat runtime (`src/api/http/chat_app.py`)
- Vite-based UI (`web/chat-ui/`) calling API via `VITE_CHAT_API_URL`
- UI quick replies/intent preview/completion card and session continuity

### Required tests
- API smoke and browser transcript sanity checks
- parity checks vs integration transcript expectations

---

## Phase 6 - Secondary Intent Subgraphs
### Implemented scope
- complete reschedule/cancel subgraphs with booking-code identity
- deterministic what-to-prepare guidance
- availability as informational path (no booking writes unless booking path entered)

### Required tests
- `Phases/phase_6_secondary_intents/tests/integration/*`
- no-PII and no-artifact-on-availability checks

---

## Phase 7 - Voice Adapters + Voice UI
### Implemented scope
- adapters/bridge in `Phases/phase_7_voice_adapters/src/phase7/`:
  - `config.py`
  - `stt_adapter.py`
  - `tts_adapter.py`
  - `tts_formatter.py`
  - `chat_voice_bridge.py`
- web UI voice controls in `web/chat-ui/src/main.js` and style updates
- voice parity routed through same API/orchestrator path

### Required tests
- phase7 unit tests for adapters/formatter/config
- voice bridge integration parity tests

---

## Phase 8 - Hardening and Operations (Detailed)

### 8.1 Runtime controls
- enforce session/runtime limits:
  - request size bounds
  - max turn count / timeout guards
  - stale session TTL cleanup policy
- ensure bounded retries only (no infinite loops)

### 8.2 Observability and audit guarantees
- `src/observability/logger.py`
  - mandatory structured fields
  - redaction-safe logging policy
- `src/observability/audit.py`
  - artifact lifecycle audit records (attempt/success/failure/degraded)
  - no raw PII payload persistence

### 8.3 Degraded mode and outage behavior
- define explicit MCP outage fallback messages
- continue safe conversation without claiming artifact success
- document operator runbook in `Docs/Runbook.md`:
  - outage triage
  - retry/replay guidance
  - manual recovery process

### 8.4 Failure injection and compliance gates
- integration tests required:
  - `tests/integration/test_mcp_timeout_degraded_mode.py`
  - `tests/integration/test_pii_audit_gate.py`
- CI gates should fail on:
  - missing degraded-mode handling
  - PII leakage in logs/audit outputs

### 8.5 Phase 8 completion checklist
- runtime limits and TTL cleanup enabled
- degraded mode documented and validated
- failure-injection tests passing
- CI/runtime audits proving no PII in persisted outputs

---

## Phase 9 - Final Deployment Phase (Streamlit)

### 9.1 Deployment target
Deploy a Streamlit frontend that uses the same backend chat API contracts and preserves runtime invariants.

### 9.2 Required code/config additions for deployability
1. **Create Streamlit app entry**
   - Canonical app: `Phases/phase_9_streamlit_deploy/streamlit_app.py` (and `src/phase9/` client + UI modules).
   - Optional root shim: `streamlit_app.py` at repo root delegates to the same `phase9.app.main()`.
   - responsibilities:
     - session bootstrap
     - render chat timeline
     - post messages to backend API
     - render quick replies/intent preview
     - show booking summary card data

2. **Add Streamlit dependency and lock**
   - add `streamlit` to Python dependency manifest used by deployment
   - ensure runtime install command matches hosting environment

3. **Add Streamlit config**
   - create `.streamlit/config.toml`:
     - `server.headless = true`
     - `server.enableCORS = false` (or host-specific safe value)
     - theme/log settings as required
   - optional `.streamlit/secrets.toml` local template (not committed with secrets)

4. **Backend URL and env strategy**
   - support `CHAT_API_BASE_URL` in Streamlit app
   - default to local API for dev, hosted API for production
   - do not expose Google credentials to Streamlit client-side code

5. **Session handling in Streamlit**
   - persist `session_id` in `st.session_state`
   - preserve transcript in `st.session_state.messages`
   - include explicit reset/new-session action

6. **Health and deployment scripts**
   - add deployment docs section and startup commands:
     - local: `streamlit run Phases/phase_9_streamlit_deploy/streamlit_app.py` or `streamlit run streamlit_app.py` (root shim)
     - hosted: platform start command for Streamlit app
   - optionally add a lightweight `/health` check on API if not already available

### 9.3 Streamlit architecture boundary rules
- Streamlit app is transport/presentation only.
- No domain/MCP logic is implemented in Streamlit layer.
- Calls backend API only; backend remains source of truth.

### 9.4 Phase 9 testing and release criteria
- smoke tests:
  - new session -> intent selection -> booking completion
  - reschedule/cancel flows
  - degraded mode messaging rendering
- parity checks:
  - Streamlit responses match API contract fields
- deployment criteria:
  - app starts on clean environment
  - env var wiring documented
  - secrets excluded from repo

---

## 6) Repository Mapping (Current + Deployment)
- `Phases/phase_1_chat_runtime/src/phase1/` - orchestration/session/chat runtime
- `Phases/phase_6_secondary_intents/` - secondary intent test/coverage
- `Phases/phase_7_voice_adapters/src/phase7/` - voice adapters + bridge
- `src/api/http/` - API wrapper layer
- `src/integrations/google_mcp/` - MCP integration path
- `src/observability/` - logging/audit/reliability
- `web/chat-ui/` - Vite web client
- `Phases/phase_9_streamlit_deploy/` - Streamlit deployment UI (entry + `phase9` client)
- `streamlit_app.py` (repo root) - thin shim to Phase 9 entry

---

## 7) Local/Deploy Runbook Summary
- API local: `uvicorn src.api.http.chat_app:app --host 127.0.0.1 --port 8000`
- Vite UI local: `cd web/chat-ui && npm run dev`
- Streamlit local (Phase 9): `streamlit run Phases/phase_9_streamlit_deploy/streamlit_app.py` (or `streamlit run streamlit_app.py`)

---
*Last updated: 2026-04-13*
