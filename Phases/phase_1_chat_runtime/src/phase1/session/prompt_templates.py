"""Canonical response templates for the conversation orchestrator."""

GREETING = "Hello! I can help you with advisor appointments."

DISCLAIMER = (
    "Before we proceed: this assistant is informational only and does not "
    "provide investment advice. Please avoid sharing personal identifiers "
    "such as phone numbers, email addresses, or account numbers."
)

PII_REJECTION = (
    "I cannot process personal identifiers. "
    "Please remove any sensitive details and try again."
)

INVESTMENT_ADVICE_REFUSAL = (
    "I'm unable to provide investment advice. "
    "For educational resources, please visit: "
    "https://example.com/learn/investing-basics\n"
    "I can help you book an advisor appointment instead."
)

INTENT_PROMPT = (
    "How can I help you today? I can assist with:\n"
    "- Book a new appointment\n"
    "- Reschedule an existing booking\n"
    "- Cancel a booking\n"
    "- What to prepare for your appointment\n"
    "- Check advisor availability"
)

TOPIC_PROMPT = (
    "What topic would you like to discuss with the advisor?\n"
    "- KYC / Onboarding\n"
    "- SIP / Mandates\n"
    "- Statements / Tax Docs\n"
    "- Withdrawals & Timelines\n"
    "- Account Changes / Nominee"
)

TOPIC_UNSUPPORTED = (
    "That topic is not supported yet. "
    "Please choose from: KYC, SIP, Statements, Withdrawals, or Account Changes."
)

TIME_PREFERENCE_PROMPT = (
    "Do you have a preferred date or time? "
    "For example: 'tomorrow afternoon' or 'next Monday morning'. "
    "All times will be shown in IST."
)

SLOT_OFFER_HEADER = "Here are two available slots in IST:"

SLOT_CONFIRM_PROMPT = "Please reply with 1 or 2 to select a slot."

SLOT_INVALID_CHOICE = "Please confirm by replying with 1 or 2."


def slot_confirmation_message(slot_label: str) -> str:
    return f"You have selected: {slot_label}. Can you confirm this slot? (yes/no)"


def booking_confirmed_message(slot_label: str, booking_code: str, event_id: str, draft_id: str) -> str:
    return (
        f"Your appointment is confirmed for {slot_label}.\n"
        f"Booking code: {booking_code}.\n"
        "A tentative Google Calendar hold, a pre-booking log line in Google Docs, "
        "and an approval-gated Gmail draft have been created.\n"
        f"Calendar event id: {event_id}\n"
        f"Gmail draft id: {draft_id} (draft only — not sent).\n"
        "Use your secure link when you are ready to complete any remaining steps."
    )


def mcp_booking_failed_message() -> str:
    return (
        "Your slot was confirmed in chat, but we could not complete Google Calendar, Docs, or Gmail steps. "
        "Please try again shortly or contact support. No booking code was issued."
    )


SECURE_LINK_TEMPLATE = (
    "To complete the next steps, please visit: "
    "https://example.com/complete?ref={code}"
)

RESCHEDULE_COLLECT_CODE = "Please share your existing booking code to reschedule."

RESCHEDULE_PHASE1_STUB = (
    "Reschedule acknowledged. In Phase 1, this flow is conversational only. "
    "Full reschedule with new slot offers will be available in a later phase."
)

CANCEL_COLLECT_CODE = "Please share your booking code to cancel."

CANCEL_CONFIRM_PROMPT = "Are you sure you want to cancel booking {code}? (yes/no)"

CANCEL_PHASE1_STUB = (
    "Cancellation acknowledged. In Phase 1, this flow is conversational only. "
    "Full cancellation with hold removal will be available in a later phase."
)

PREPARE_GUIDANCE = (
    "To prepare for your advisor appointment:\n"
    "- Have your topic details ready\n"
    "- Gather any relevant prior statements or documents\n"
    "- Note down your questions in advance\n"
    "Please do not share personal identifiers during the call."
)

AVAILABILITY_RESPONSE = (
    "Advisor availability is generally open during weekdays (IST business hours). "
    "To see exact available slots, please proceed with booking a new appointment."
)

SESSION_COMPLETE = "This session is complete. Start a new session for another request."

UNKNOWN_INTENT = (
    "I didn't quite catch that. Could you please tell me if you'd like to "
    "book, reschedule, cancel, prepare for, or check availability of an appointment?"
)
