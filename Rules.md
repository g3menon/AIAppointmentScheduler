# 📏 INDMoney Weekly Pulse — Rules & Guardrails

> This document defines the rules, constraints, and guardrails for every phase of the
> pipeline. All contributors and AI agents **must** follow these rules to ensure
> data quality, cost efficiency, privacy compliance, and maintainable code.

---

## 🌍 Global Rules (Apply to ALL Phases)

| # | Rule | Rationale |
|---|------|-----------|
| G1 | **Do not overengineer.** Write the simplest code that solves the problem. Avoid premature abstraction, unnecessary classes, or complex patterns unless justified. | Minimise token usage, API costs, and maintenance burden. |
| G2 | **Minimise LLM token and API usage** wherever possible without degrading output quality. Batch inputs, reuse outputs, and avoid redundant calls. | Keep weekly run cost under $0.01. |
| G3 | **No PII or personal information** should exist in any file after Phase 3. Every downstream consumer (LLM prompts, emails, dashboard, logs) must operate on PII-stripped data only. | Privacy compliance and data-protection best practice. |
| G4 | **All README files must reflect the actual implementation** — not aspirational or copy-pasted boilerplate. Update READMEs as part of every PR that changes code. | Documentation drift causes onboarding friction and bugs. |
| G5 | **Use environment variables for all secrets.** Never hard-code API keys, passwords, or sensitive values. | Security hygiene. |
| G6 | **Log meaningfully.** Use the shared logger from Phase 1. Include counts, durations, and error context — but never log secrets or PII. | Debuggability without risk. |
| G7 | **Fail gracefully.** Every phase must handle its known failure modes (see architecture §9). Save partial outputs where possible; never crash silently. | Robust weekly automation. |
| G8 | **Pin dependencies.** Use exact versions in `requirements.txt`. | Reproducible builds across local, Docker, and CI. |

---

## Phase 1 — Setup & Configuration

| # | Rule | Details |
|---|------|---------|
| P1.1 | **Validate all required env vars at startup.** Exit with a clear error message listing the missing variable and how to fix it. | Prevents cryptic failures deep in the pipeline. |
| P1.2 | **Single source of truth.** Every constant (model IDs, app ID, file paths, window sizes) lives in `config.py`. Other phases import — never redefine. | Eliminates drift between phases. |
| P1.3 | **Safe `__repr__`.** The `Settings` object must never print full API keys or passwords in logs or tracebacks. | Prevents accidental credential leaks. |

---

## Phase 2 — Review Scraping

| # | Rule | Details |
|---|------|---------|
| P2.1 | **Discard reviews shorter than 30 words.** Reviews with fewer than 30 words lack context for meaningful theme classification and waste LLM tokens on low-signal input. | Improves downstream LLM output quality. |
| P2.2 | **Cap at `MAX_REVIEWS` (200).** Even if more reviews are available, never send more than 200 to the pipeline. | Token budget control — keeps total run ≤ 30K tokens. |
| P2.3 | **Deduplicate by `review_id`.** Reject any review that has already been seen within the current scrape window. | Prevents inflated counts and wasted LLM context. |
| P2.4 | **Date-window filter.** Only retain reviews from the last `DATE_WINDOW_WEEKS` (8 weeks). Older reviews are irrelevant to a *weekly* pulse. | Freshness and relevance. |
| P2.5 | **Do not collect PII or personal information.** If the scraper encounters profile pictures, usernames, or email addresses from the Play Store API response, drop those fields. Only retain: `review_id`, `rating`, `text`, `date`, `thumbs_up`. Note: `title` should not be preserved. | Minimise PII surface area from the start. |
| P2.6 | **Respect rate limits.** Use exponential backoff (max 3 retries) if the Play Store returns HTTP 429 or connection errors. | Avoid IP bans and maintain reliability. |
| P2.7 | **English reviews only.** Data got from google playscrape should not include sentences in languages that are not english. The sentences should be written in English and be comprehendable. | The LLM operates best on comprehendable English text. |
| P2.8 | **Prioritise helpful reviews.** If `thumbs_up` in the data refers to helpfulness of the review, prioritise reviews that have higher number of `thumbs_up`. | More helpful reviews carry more signal for the pulse summary. |
| P2.9 | **Do not store the title.** The title should not be included in the saved data. | Re-iteration of rule P2.5 for explicitness to save storage and context window. |
| P2.10 | **Remove emojis.** Remove all emojis from the review text. | Emojis add noise to the dataset and can interfere with LLM comprehension and formatting. |

---

## Phase 3 — Data Cleaning & PII Removal

| # | Rule | Details |
|---|------|---------|
| P3.1 | **Strip all PII using regex patterns.** Emails → `[EMAIL]`, phone numbers → `[PHONE]`, Aadhaar-style IDs → `[ID]`. | Legal and ethical data handling. |
| P3.2 | **Remove gibberish and nonsensical text.** Discard reviews that are random character strings, keyboard smashes, or text that does not form coherent sentences. Use a simple heuristic: if a review has > 50% non-dictionary words or consists of repeated characters, drop it. | Garbage in → garbage out. Gibberish wastes LLM tokens and degrades theme quality. |
| P3.3 | **Filter out hate speech, slang, and abusive language.** Flag and discard reviews containing profanity, slurs, or threatening language. Use a lightweight keyword-based filter (not an LLM call) to keep costs zero. | Keeps the pulse professional and safe for leadership consumption. No LLM tokens wasted on toxic content. |
| P3.4 | **Re-apply the 30-word minimum after cleaning.** PII replacement and text normalisation may reduce word count below the threshold — re-check and drop if needed. | Ensures only substantive reviews reach LLMs. |
| P3.5 | **Normalise whitespace and fix encoding.** Collapse multiple spaces, strip leading/trailing whitespace, and fix common UTF-8 encoding artefacts (e.g., `â€™` → `'`). | Clean input improves LLM comprehension and reduces token waste from junk characters. |
| P3.6 | **Log cleaning statistics.** Record: total input, PII-stripped count, gibberish-dropped count, profanity-dropped count, short-review-dropped count, final output count. | Observability for debugging and quality monitoring. |

---

## Phase 4 — Theme Generation & Classification (Groq)

| # | Rule | Details |
|---|------|---------|
| P4.1 | **Minimise LLM calls.** Theme discovery = 1 call. Batch classification = 1–2 calls. Never exceed 3 total Groq API calls. | Cost control: Groq calls should stay under $0.005. |
| P4.2 | **Batch reviews into a single prompt** rather than classifying one-by-one. Send all reviews in one payload. | 200 individual calls vs 1 batch call = 200× cost difference. |
| P4.3 | **Request structured JSON output.** Always instruct the LLM to return valid JSON. Validate the response schema before saving. | Prevents downstream parsing failures. |
| P4.4 | **Limit themes to exactly 5 or more.** Generate at least 5 themes, including at least one related to positive feedback or what is working well. If it fails, re-prompt once. | Too few themes = overgeneralisation. Capturing positive feedback is essential for a balanced pulse. |
| P4.5 | **Never send raw reviews to the LLM.** Only cleaned reviews (post-Phase 3) should reach any API. | PII and toxic content must never be sent to external APIs. |
| P4.6 | **Use temperature = 0 for classification tasks.** Deterministic output is preferred for reproducibility. | Consistent results across runs. |
| P4.7 | **Multiple themes per review.** A single review can be associated with multiple themes if it touches on several distinct topics. | Captures nuance in comprehensive reviews. |
| P4.8 | **Accurate sentiment classification.** Ensure that positive feedback is not wrongly classified under negative categories. Themes and quotes must match in sentiment. | Avoids misleading the leadership team. |

---

## Phase 5 — Pulse Generation (Gemini)

| # | Rule | Details |
|---|------|---------|
| P5.1 | **Single Gemini call.** Generate the entire pulse JSON (themes summary, quotes, actions) in one API call. | Cost and latency control. |
| P5.2 | **Validate pulse schema before saving.** The output must contain: `themes` (array), `quotes` (array of 4), `actions` (array of 3), `meta` (object with counts and date range). | Prevents Phase 6 and Phase 7 from breaking on malformed data. |
| P5.3 | **Anonymise quotes.** Even though PII was stripped in Phase 3, ensure selected quotes contain no identifiable information, usernames, or app-specific account detail. | Extra safety layer before leadership-facing output. |
| P5.4 | **Keep the pulse concise.** Total pulse output should be under 1,500 tokens. Instruct the LLM to be succinct — leadership doesn't read walls of text. | Readability and email-friendliness. |
| P5.5 | **Positive Focus.** Ensure exactly 4 top themes and 4 quotes. The fourth theme must be generated from positive feedback to know what is working well. The fourth quote must match this positive theme to know what to keep doing. | Balanced perspective for leadership. |

---

## Phase 6 — Email Draft & Delivery

| # | Rule | Details |
|---|------|---------|
| P6.1 | **Single Gemini call for prose polishing.** Do not make multiple calls to refine wording. One call, one pass. | Token economy. |
| P6.2 | **Always save the HTML draft locally** (`data/email_draft.html`) before attempting SMTP. | If email delivery fails, the draft is still available for manual sending. |
| P6.3 | **Use Jinja2 for templating.** Do not generate HTML from string concatenation. | Maintainable, readable, and secure templates. |
| P6.4 | **The email must be a single-page, self-contained HTML.** No external CSS, no JavaScript, no image hotlinks. All styles must be inline. | Email client compatibility (Gmail, Outlook, Apple Mail). | Make sure the template is user friendly, content does not overlap, the look and feel is modern, modular and responsive, it is visually appealing and easy to read. |
| P6.5 | **Do not include any PII in the email.** Double-check that no user names, emails, or phone numbers appear in the final HTML. | Final gatekeeper before data leaves the system. |
| P6.6 | **Fallback on Gemini failure.** If the prose-polishing call fails, render the email using raw pulse data. Never skip sending because of a polish failure. | Reliability over perfection. |

---

## Phase 7 — Streamlit Dashboard

| # | Rule | Details |
|---|------|---------|
| P7.1 | **Read JSON files directly.** No backend server, no database. Streamlit reads from `data/*.json`. | Simplicity — one Python file, zero infrastructure. |
| P7.2 | **Show a clear warning if data files are missing.** Do not crash — display "Run the pipeline first" with instructions. | User-friendly error state. |
| P7.3 | **Do not display raw review text in the dashboard.** Only show LLM-generated summaries, anonymised quotes, and aggregated statistics. | Prevents accidental PII exposure through the UI. |

---

## Phase 8 — Docker Containerisation

| # | Rule | Details |
|---|------|---------|
| P8.1 | **Use `python:3.11-slim` as the base image.** No full Ubuntu, no Alpine (compatibility issues with some Python packages). | Minimal image size without dependency headaches. |
| P8.2 | **Never bake secrets into the Docker image.** Use `--env-file` or environment variables at runtime. | Security best practice. |
| P8.3 | **Include `.env` in both `.dockerignore` and `.gitignore`.** | Prevents accidental credential exposure. |

---

## Phase 9 — GitHub Actions Scheduler

| # | Rule | Details |
|---|------|---------|
| P9.1 | **Store all credentials in GitHub Secrets.** Never echo or log secret values in workflow steps. | Security compliance. |
| P9.2 | **Upload `data/` as workflow artifacts** (retained 30 days). | Auditability and debugging of past runs. |
| P9.3 | **Support `workflow_dispatch`** for manual trigger alongside the cron schedule. | Flexibility for on-demand runs. |
| P9.4 | **Timezone Awareness (`UTC` vs Local).** GitHub Actions cron runs strictly in UTC. Cron expressions must be explicitly converted to UTC (e.g. 9:00 AM IST corresponds to `30 3 * * 1` in UTC). | Prevents schedule mismatches and delayed operations. |

## Phase 10A — Fee Explanation

| # | Rule | Details |
|---|------|---------|
| P10A.1 | **Handle scraping failures gracefully.** INDMoney blocks basic requests. The scraper must catch `requests.exceptions.RequestException` and HTTP errors, and fall back to mock data or skip the fee section silently, rather than crashing the pipeline. | Cloudflare or bot protection can block requests. We cannot let a 403 on the fee explainer stop the primary weekly pulse email from going out. |
| P10A.2 | **Use simple requests/bs4.** Do not introduce bulky dependencies like Playwright or Selenium. If simple requests fail, rely on the fallback. | Keep deployment lightweight, particularly to avoid bloating the Docker image. |
| P10A.3 | **Read target URL from `config.py`.** The target fund URL must be specified via `FEE_FUND_URL` in `config.py`, not hardcoded in the scraper files. | Improves maintainability and allows for targeting different funds in the future. |

## Phase 10B — Google Docs MCP Appender

| # | Rule | Details |
|---|------|---------|
| P10B.1 | **Schema Strictness.** `json_combiner.py` must produce exactly the schema defined in `architecture.md`. | Google Docs MCP expects a consistent formatting. |
| P10B.2 | **Graceful MCP failure.** Appending to the Doc is an enhancement. If the MCP client fails to invoke, log an error, save the combined JSON locally, and allow the pipeline to complete successfully. | A Google API failure should not mark the whole weekly run as failed. |
| P10B.3 | **Configurable MCP Server invocation.** The Python MCP Client must NOT hardcode the server command. Read `MCP_GOOGLE_DOCS_SERVER_CMD` and `MCP_GOOGLE_DOCS_SERVER_ARGS` from `.env`. | Allows execution environments to swap to a different MCP backend without code changes. |
| P10B.4 | **MCP Authentication Variables.** Ensure `GOOGLE_APPLICATION_CREDENTIALS` and `SERVICE_ACCOUNT_PATH` are mapped from `GOOGLE_DOCS_CREDENTIALS` in the subprocess environment before invoking the MCP Server. | The `mcp-gdocs` server requires standard Google authentication variable patterns to initiate correctly. |

---

## 📐 Deployment Checklist

Before every deployment or merge to `main`, verify:

- [ ] All `README.md` files are updated to match the actual code
- [ ] `requirements.txt` has pinned, accurate versions
- [ ] `.env.example` lists every required variable with placeholder values
- [ ] No secrets or PII in any committed file (`grep -r "password\|api_key" --include="*.py"`)
- [ ] All phases run end-to-end without errors (`python main.py`)
- [ ] Email draft renders correctly in Gmail web client
- [ ] Dashboard loads without errors (`streamlit run phase7_dashboard/app.py`)
- [ ] Docker build succeeds (`docker build -t weekly-pulse .`)
- [ ] Total LLM calls per run ≤ 5
- [ ] Total token usage per run ≤ 35K

---

## 📊 Rule Summary by Phase

```
Phase 1 (Setup)     → 3 rules   — Config validation, single source of truth, safe repr
Phase 2 (Scrape)    → 6 rules   — 30-word min, cap 200, dedup, date filter, no PII fields, rate limits
Phase 3 (Clean)     → 6 rules   — PII regex, gibberish filter, hate speech filter, re-check length, normalise, log stats
Phase 4 (Themes)    → 8 rules   — Min calls, batch, JSON output, >=5 themes with positive, no raw reviews, temp=0, multi-theme, sentiment matching
Phase 5 (Pulse)     → 5 rules   — Single call, validate schema, anonymise quotes, keep concise, positive focus
Phase 6 (Email)     → 6 rules   — Single call, save draft first, Jinja2, self-contained HTML, no PII, fallback
Phase 7 (Dashboard) → 3 rules   — Read JSON, warn if missing, no raw text
Phase 8 (Docker)    → 3 rules   — Slim image, no baked secrets, gitignore .env
Phase 9 (Scheduler) → 4 rules   — GitHub Secrets, upload artifacts, manual trigger, timezone awareness (UTC)
Phase 10A (Fee Expl)→ 3 rules   — Graceful scraping failures, simple requests, unhardcoded target URL
Phase 10B (GDocs)   → 4 rules   — Schema strictness, graceful failure, configurable invocation, MCP auth mapping
Global              → 8 rules   — Simplicity, cost control, PII, READMEs, env vars, logging, error handling, pinned deps
──────────────────────────────────
Total               → 57 rules
```

---

*Last updated: 2026-03-22 · Maintainer: @g3menon*
