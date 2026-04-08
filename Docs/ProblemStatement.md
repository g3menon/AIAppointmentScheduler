
Who this helps
Users who want a human consult; PMs/Support running compliant pre-booking.

What you must build
Intents (5): book new, reschedule, cancel, “what to prepare,” check availability windows.

Flow: greet → disclaimer (“informational, not investment advice”) → confirm topic (KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals & Timelines, Account Changes/Nominee) → collect day/time preference → offer two slots (mock calendar) → on confirm:

Generate Booking Code (e.g., NL-A742).

MCP Calendar: create tentative hold “Advisor Q&A — {Topic} — {Code}”.

MCP Notes/Doc: append {date, topic, slot, code} to “Advisor Pre-Bookings”.

MCP Email Draft: prepare advisor email with details (approval-gated).

Read the booking code + give a secure URL for contact details (outside the call).

Key constraints
No PII on the call (no phone/email/account numbers).

State time zone (IST) and repeat date/time on confirm.

If no slots match → create waitlist hold + draft email.

Refuse investment advice; provide educational links if asked.

What to submit (deliverables)
Working voice demo (live link) or ≤3-min call recording.

Calendar hold screenshot (with title incl. booking code).

Notes/Doc entry + Email draft screenshot/text.

Script file (the short prompts/utterances you used).

README: mock calendar JSON; how reschedule/cancel works.

Skills being tested
W9 — Building Voice Agents: ASR/TTS basics, confirmations, short responses.

W5 — Multi-Agent & MCP: Calendar + Notes/Doc + Email with human-in-the-loop approvals.

W4 — AI Agents & Protocols: slot-filling (topic/time), reschedule/cancel flows.

W2 — LLMs & Prompting: safe disclaimers/refusals, crisp phrasing.

W7 — Designing for AI Products: compliance microcopy, booking-code UX, clear next steps.