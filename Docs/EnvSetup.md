# Environment Setup Guide

Use this with `.env.example` to create your local `.env` safely. The example file lists **every variable** and **where secrets come from**.

## 1) Create your local `.env`

1. From the repository root, copy the template:
   - **Windows (PowerShell):** `Copy-Item .env.example .env`
   - **macOS / Linux:** `cp .env.example .env`
2. Edit `.env` and replace all placeholders (`YOUR_...`, empty fields you intend to use).
3. **Never** commit `.env` or paste secrets into chat, tickets, or screenshots.

## 2) Minimum setup for Phase 1–2 (chat + domain, no Google writes)

Set at least:

| Variable | Value | Notes |
|----------|--------|--------|
| `GOOGLE_MCP_MODE` | `fake` | No Google credentials needed |
| `ENABLE_VOICE_API` | `false` | Voice comes in Phase 7+ |
| `ENABLE_STT` / `ENABLE_TTS` | `false` | Same |
| `PII_GUARD_ENABLED` | `true` | Required |
| `PII_BLOCK_ON_DETECT` | `true` | Required |
| `PII_STORE_RAW_TRANSCRIPT` | `false` | Required |
| `PII_STORE_RAW_AUDIO` | `false` | Required |

You can leave `GEMINI_API_KEY` and all `GOOGLE_OAUTH_*` / `GOOGLE_SERVICE_ACCOUNT_FILE` unset until you need live NLU or Google tools.

## 3) NLU (Gemini) for Phase 3+

1. Open [Google AI Studio API keys](https://aistudio.google.com/apikey).
2. Create an API key and copy it into `.env` as `GEMINI_API_KEY`.
3. Set `NLU_PROVIDER=gemini` and adjust `NLU_MODEL` / `NLU_CONFIDENCE_THRESHOLD` if needed.
4. Prefer restricting the key (IP / app) in Google Cloud Console.

If you temporarily use **rules-only** NLU (no provider calls), you can still keep the same env keys for when you switch the implementation on.

## 4) Google MCP “real” mode (Phase 3+)

### 4.1 Enable real mode

- Set `GOOGLE_MCP_MODE=real`.
- Fill **all** of: auth (OAuth *or* service account), `GOOGLE_CALENDAR_ID`, `GOOGLE_PREBOOKING_DOC_ID`, `ADVISOR_EMAIL_TO`.

### 4.2 OAuth (user credentials)

1. In [Google Cloud Console](https://console.cloud.google.com/), select or create a project.
2. **APIs & Services → Library** — enable **Google Calendar API**, **Google Docs API**, **Gmail API** (and any others your code uses).
3. **OAuth consent screen** — configure; add test users if the app is External.
4. **Credentials → Create credentials → OAuth client ID** (Desktop or Web, depending on your token script).
5. Run a **one-time local OAuth flow** with your client ID/secret to obtain a **refresh token** (tools such as `oauth2l` or a small Python script are common). Store only:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REFRESH_TOKEN`
6. If you use a Web client, set `GOOGLE_OAUTH_REDIRECT_URI` to the exact redirect URI registered in the console.

### 4.3 Service account (JSON file)

1. **IAM & Admin → Service accounts** — create a service account and a **JSON key**; download the file.
2. Set `GOOGLE_AUTH_MODE=service_account` and `GOOGLE_SERVICE_ACCOUNT_FILE` to the **absolute path** of that JSON file.
3. **Share** the target calendar and the pre-booking Doc with the service account’s email (from the JSON, `client_email`).
4. Domain-wide delegation is optional and advanced; if your admin sets it up, you may use `GOOGLE_DELEGATED_SUBJECT` as documented in `.env.example`.

### 4.4 Resource IDs

- **Calendar:** `GOOGLE_CALENDAR_ID=primary` uses the authenticated user’s primary calendar, or paste a shared calendar ID from Calendar settings.
- **Docs:** Open the pre-booking document; the ID is the long string in the URL between `/d/` and `/edit`.
- **Advisor email:** `ADVISOR_EMAIL_TO` is the mailbox used for **draft** creation (design is draft-only, never auto-send).

## 5) Voice (Phase 7+)

Only after chat phases are stable:

- `ENABLE_VOICE_API=true`
- `ENABLE_STT=true`
- `ENABLE_TTS=true` (when your adapters are ready)

Keep PII flags as in §2: no raw transcript/audio storage unless explicitly approved.

## 6) PII safety checklist before any demo or prod run

Confirm **true:**

- `PII_GUARD_ENABLED`
- `PII_BLOCK_ON_DETECT`
- `PII_AUDIT_FAIL_ON_MATCH`

Confirm **false:**

- `PII_STORE_RAW_TRANSCRIPT`
- `PII_STORE_RAW_AUDIO`

## 7) Common mistakes

- Turning on `GOOGLE_MCP_MODE=real` without calendar/doc IDs or without sharing resources with a service account.
- Logging raw user text (`LOG_REDACT_USER_TEXT` must stay `true` in production).
- Putting user free text into Calendar/Docs/Gmail payloads (forbidden by product design).
- Enabling voice before the chat baseline and PII gates are green.
