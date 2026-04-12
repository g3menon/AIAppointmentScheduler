# Operational Runbook — AI Appointment Scheduler

*Last updated: 2026-04-12*

---

## 1. Service Overview

| Component          | Port  | Command                                                      |
|--------------------|-------|--------------------------------------------------------------|
| Backend API        | 8000  | `uvicorn src.api.http.chat_app:app --host 127.0.0.1 --port 8000` |
| Vite Chat UI       | 5173  | `cd web/chat-ui && npm run dev`                              |
| Streamlit UI       | 8501  | `streamlit run Phases/phase_9_streamlit_deploy/streamlit_app.py` (or root `streamlit_app.py` shim) |

**Health check:** `GET http://127.0.0.1:8000/api/health` → `{"status": "ok"}`

---

## 2. Outage Triage

### 2.1 Symptoms and Diagnosis

| Symptom | Likely Cause | First Action |
|---------|--------------|--------------|
| "Could not reach the server" in UI | API process down or port conflict | Check if uvicorn is running; check port 8000 |
| Booking confirmation hangs | MCP timeout (Google APIs) | Check Google API quotas and network |
| "could not complete" in chat | Partial MCP failure | Check audit records for `failure_stage` |
| "booking services unavailable" | Full MCP outage | Check Google service status page |
| Session not responding | Turn limit exceeded or stale session | Start new session |

### 2.2 Port Conflict Resolution (Windows)

```powershell
# Find process on port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object OwningProcess

# Kill it
Stop-Process -Id <PID> -Force

# Restart API
uvicorn src.api.http.chat_app:app --host 127.0.0.1 --port 8000
```

---

## 3. MCP Failure Handling

### 3.1 Failure Stages

The MCP booking triplet executes in order: **Calendar → Docs → Gmail**.
Failure at any stage stops execution of subsequent steps.

| Failure Stage | Calendar | Docs | Gmail | User Impact |
|---------------|----------|------|-------|-------------|
| Calendar      | failed   | skipped | skipped | No artifacts created |
| Docs          | success  | failed  | skipped | Calendar hold exists but booking incomplete |
| Gmail         | success  | success | failed  | Calendar + Docs exist, no email draft |

### 3.2 Retry Behavior

- Each MCP operation retries up to **3 times** for transient errors.
- Non-transient errors (auth failures, invalid requests) fail immediately.
- The retry loop is bounded — no infinite retry is possible.

### 3.3 Manual Recovery After Partial Failure

1. **Check audit records**: Look for `AuditRecord` entries with the session ID.
2. **Calendar hold created but booking failed**:
   - The calendar hold may need manual deletion via Google Calendar UI.
   - The hold was created with an idempotency key: `{namespace}:{booking_code}:calendar`.
3. **Docs entry created but Gmail draft failed**:
   - The pre-booking log entry exists in Google Docs.
   - Manually create the Gmail draft or retry the booking flow.

---

## 4. Runtime Controls

### 4.1 Session Limits

| Control | Value | Behavior |
|---------|-------|----------|
| Max turns per session | 50 | Session closes with message to start new session |
| Max request length | 16,000 chars | Message rejected with "too long" response |
| Session TTL | 3,600 seconds (1h) | Stale sessions purged on next access |
| FastAPI body validation | session_id: 1–128 chars, text: ≤16,000 chars | 422 Validation Error |

### 4.2 Session Cleanup

Sessions are stored in-memory. The `InMemorySessionStore.purge_stale()` method
removes sessions that have been idle beyond the TTL. This runs lazily —
operators can invoke it on a schedule or before health checks.

---

## 5. Observability

### 5.1 Log Events

Every orchestrator turn emits a `log_event("orchestrator_turn", ...)` with these
required fields:

- `session_id`
- `stage` (current state)
- `intent`
- `booking_code`
- `error_type` ("none", "integration", "system", etc.)
- `latency_ms`

**PII redaction**: All string values are automatically redacted before storage:
- Email → `[REDACTED_EMAIL]`
- Phone (10 digits) → `[REDACTED_PHONE]`
- PAN → `[REDACTED_PAN]`
- Aadhaar → `[REDACTED_AADHAAR]`

### 5.2 Audit Records

Artifact lifecycle events are recorded via `record_artifact_status()`.
The following keys are **automatically stripped** from audit payloads:

`raw_user_text`, `user_text`, `transcript`, `raw_transcript`, `email`, `phone`

### 5.3 Verifying PII Safety

Run the Phase 8 PII audit gate test:

```bash
pytest Phases/phase_8_hardening_ops/tests/integration/test_pii_audit_gate.py -v
```

---

## 6. Degraded Mode Behavior

When MCP services are unavailable, the system:

1. **Does NOT claim booking success** — messages explicitly state the operation was not completed.
2. **Records the failure** in audit records with `failure_stage` and per-service status.
3. **Guides the user** to retry or contact support.
4. **Closes the session** gracefully — no infinite retry loops.

### 6.1 Degraded Mode Messages

| Scenario | User-facing message |
|----------|-------------------|
| Timeout | "We're experiencing a temporary delay... Please try again in a few minutes." |
| Partial failure | "We could not complete all booking steps... Please try again shortly." |
| Full outage | "Our booking services are currently unavailable... No changes have been made." |

---

## 7. CI / Test Verification

### 7.1 Full Test Suite

```bash
pytest --tb=short -q
```

### 7.2 Phase 8 Specific Tests

```bash
# Runtime controls
pytest Phases/phase_8_hardening_ops/tests/unit/test_runtime_controls.py -v

# Session TTL
pytest Phases/phase_8_hardening_ops/tests/unit/test_session_ttl.py -v

# Observability compliance gate
pytest Phases/phase_8_hardening_ops/tests/unit/test_observability_gate.py -v

# MCP timeout degraded mode (integration)
pytest Phases/phase_8_hardening_ops/tests/integration/test_mcp_timeout_degraded_mode.py -v

# PII audit gate (integration)
pytest Phases/phase_8_hardening_ops/tests/integration/test_pii_audit_gate.py -v
```

### 7.3 CI Gate Failure Conditions

The CI pipeline MUST fail if:
- Any degraded-mode test fails (missing fallback message or incorrect artifact status)
- Any PII is detected in logged events or audit records after a full booking flow
- Runtime control tests fail (turn limits or request size guards not enforced)

---

## 8. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CALENDAR_ID` | No | `primary` | Google Calendar ID |
| `GOOGLE_PREBOOKING_DOC_ID` | Yes (prod) | — | Google Doc for pre-booking log |
| `ADVISOR_EMAIL_TO` | Yes (prod) | — | Advisor email for Gmail drafts |
| `IDEMPOTENCY_NAMESPACE` | No | `booking` | Idempotency key prefix |
| `GOOGLE_AUTH_MODE` | No | `oauth` | `oauth` or `service_account` |
| `BOOKING_MCP_DRIVER` | No | `direct` | `direct` or `llm` |
| `GEMINI_API_KEY` | For LLM path | — | Gemini API key |
| `CHAT_API_CORS_ORIGINS` | No | `localhost:5173` | Allowed CORS origins |
| `CHAT_API_BASE_URL` | Streamlit | `http://127.0.0.1:8000` | Backend URL for Streamlit |
