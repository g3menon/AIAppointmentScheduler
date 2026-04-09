# Environment Setup Guide

Use this guide with `.env.example` to create your local `.env` safely.

## 1) Create your local `.env`
- Copy `.env.example` to `.env`.
- Fill every placeholder value.
- Never commit `.env` to git.

## 2) Minimum setup for Phase 1-2 (chat + domain only)
Set:
- `GOOGLE_MCP_MODE=fake`
- `ENABLE_VOICE_API=false`
- `ENABLE_STT=false`
- `ENABLE_TTS=false`
- `PII_GUARD_ENABLED=true`
- `PII_BLOCK_ON_DETECT=true`
- `PII_STORE_RAW_TRANSCRIPT=false`
- `PII_STORE_RAW_AUDIO=false`

You do not need Google credentials yet in fake mode.

## 3) NLU setup for Phase 3+
Set:
- `GEMINI_API_KEY`
- `NLU_PROVIDER`
- `NLU_MODEL`
- `NLU_CONFIDENCE_THRESHOLD`

If using rules-only fallback temporarily, keep your NLU interface the same and skip provider calls.

## 4) Google MCP real mode setup (Phase 3+ live integration)
1. Set `GOOGLE_MCP_MODE=real`.
2. Choose auth mode:
   - OAuth: fill `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`
   - Service account: set `GOOGLE_AUTH_MODE=service_account` and provide `GOOGLE_SERVICE_ACCOUNT_FILE`
3. Fill:
   - `GOOGLE_CALENDAR_ID`
   - `GOOGLE_PREBOOKING_DOC_ID`
   - `ADVISOR_EMAIL_TO`

## 5) Voice setup (Phase 7+)
Only after chat phases are green:
- Set `ENABLE_VOICE_API=true`
- Set `ENABLE_STT=true`
- Set `ENABLE_TTS=true`
- Keep PII guards enabled and raw audio/transcript storage disabled by default.

## 6) PII safety checks before running
Confirm all are true:
- `PII_GUARD_ENABLED=true`
- `PII_BLOCK_ON_DETECT=true`
- `PII_AUDIT_FAIL_ON_MATCH=true`

Confirm all are false:
- `PII_STORE_RAW_TRANSCRIPT=false`
- `PII_STORE_RAW_AUDIO=false`

## 7) Common mistakes to avoid
- Running real Google mode without filling doc/calendar IDs.
- Logging raw user text.
- Including user free text in Calendar/Docs/Gmail payloads.
- Enabling voice before chat baseline tests are stable.

