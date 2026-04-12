"""Canonical response templates for the conversation orchestrator."""

GREETING = (
    "Hello! I can help you with advisor appointments.\n"
    "Note: this assistant is informational only and does not "
    "provide investment advice. Please avoid sharing personal identifiers."
)

DISCLAIMER = (
    "How can I help you today?\n"
    "- Book a new appointment\n"
    "- Reschedule an existing booking\n"
    "- Cancel a booking\n"
    "- What to prepare for your appointment\n"
    "- Check advisor availability"
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
        f"Your appointment is confirmed.\n"
        f"Date & time: {slot_label}.\n"
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

RESCHEDULE_NOT_FOUND = (
    "I could not find an active booking with that code. "
    "Please double-check your booking code and try again."
)

RESCHEDULE_OFFER_HEADER = "Here are two alternative slots in IST for your rescheduled appointment:"

RESCHEDULE_SLOT_CONFIRM_PROMPT = "Please reply with 1 or 2 to select your new slot."


def reschedule_confirmation_message(old_code: str, new_slot: str) -> str:
    return (
        f"You want to reschedule booking {old_code} to: {new_slot}. "
        "Can you confirm? (yes/no)"
    )


def reschedule_confirmed_message(new_slot: str, new_code: str) -> str:
    return (
        f"Your appointment has been rescheduled to {new_slot}.\n"
        f"New booking code: {new_code}.\n"
        "The previous calendar hold has been removed and a new one created.\n"
        "A reschedule note has been appended to the pre-booking log."
    )


RESCHEDULE_ABORTED = "Reschedule cancelled. Your original booking remains active."

CANCEL_COLLECT_CODE = "Please share your booking code to cancel."

CANCEL_NOT_FOUND = (
    "I could not find an active booking with that code. "
    "Please double-check your booking code and try again."
)

CANCEL_CONFIRM_PROMPT = "Are you sure you want to cancel booking {code}? (yes/no)"


def cancel_confirmed_message(code: str) -> str:
    return (
        f"Booking {code} has been cancelled.\n"
        "The calendar hold has been removed and a cancellation note "
        "has been appended to the pre-booking log."
    )


CANCEL_ABORTED = "Cancellation aborted. Your booking remains active."

PREPARE_GUIDANCE = (
    "To prepare for your advisor appointment:\n"
    "- Have your topic details ready\n"
    "- Gather any relevant prior statements or documents\n"
    "- Note down your questions in advance\n"
    "Please do not share personal identifiers during the call."
)

PREPARE_TOPIC_GUIDANCE = {
    "KYC/Onboarding": (
        "For your KYC / Onboarding appointment:\n"
        "- Keep a valid ID proof reference handy (do NOT share the number here)\n"
        "- Have your basic account preferences noted\n"
        "- Prepare questions about the onboarding process"
    ),
    "SIP/Mandates": (
        "For your SIP / Mandates appointment:\n"
        "- Know the fund categories you are interested in\n"
        "- Note your preferred SIP amount range and tenure\n"
        "- Prepare questions about mandate setup or modification"
    ),
    "Statements/Tax Docs": (
        "For your Statements / Tax Docs appointment:\n"
        "- Note the financial year or period you need statements for\n"
        "- Have any prior statement references ready\n"
        "- Prepare questions about capital gains or tax implications"
    ),
    "Withdrawals & Timelines": (
        "For your Withdrawals & Timelines appointment:\n"
        "- Know which holdings you want to discuss\n"
        "- Note the approximate amounts and timelines\n"
        "- Prepare questions about exit loads or settlement periods"
    ),
    "Account Changes/Nominee": (
        "For your Account Changes / Nominee appointment:\n"
        "- Know what changes you need (nominee, contact, bank details)\n"
        "- Have the relevant form names or references ready\n"
        "- Prepare questions about the update process and timelines"
    ),
}

AVAILABILITY_RESPONSE = (
    "Advisor availability is generally open during weekdays (IST business hours). "
    "To see exact available slots, please proceed with booking a new appointment."
)


def availability_slots_message(slots: list[str]) -> str:
    if not slots:
        return (
            "No advisor slots are currently available. "
            "Would you like to book an appointment? I can add you to the waitlist."
        )
    lines = ["Here are the currently available advisor slots (IST):"]
    for i, label in enumerate(slots, 1):
        lines.append(f"{i}) {label}")
    lines.append(
        "\nThese are for informational purposes only. "
        "To reserve a slot, please say 'book appointment'."
    )
    return "\n".join(lines)

SESSION_COMPLETE = "This session is complete. Start a new session for another request."

UNKNOWN_INTENT = (
    "I didn't quite catch that. Could you please tell me if you'd like to "
    "book, reschedule, cancel, prepare for, or check availability of an appointment?"
)
