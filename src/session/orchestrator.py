from dataclasses import dataclass, field

from src.domain.calendar_service import MockCalendarService
from src.domain.models import Intent
from src.integrations.mcp.stub_client import Phase1McpStubClient
from src.session.pii_guard import contains_pii
from src.session.session_context import SessionContext
from src.session.state import State
from src.session.topic_catalog import is_topic_allowed

DISCLAIMER = (
    "Before we proceed: this assistant is informational and not investment advice. "
    "Please avoid sharing personal identifiers."
)


@dataclass
class AgentTurn:
    messages: list[str] = field(default_factory=list)
    side_effects: list[dict] = field(default_factory=list)


class Orchestrator:
    def __init__(self) -> None:
        self.calendar = MockCalendarService()
        self.mcp_stub = Phase1McpStubClient()

    def handle(self, user_text: str, session: SessionContext) -> AgentTurn:
        text = (user_text or "").strip()
        lower = text.lower()
        session.turn_count += 1

        if contains_pii(text):
            return AgentTurn(
                messages=[
                    "I cannot process personal identifiers here. "
                    "Please remove sensitive details and continue."
                ]
            )

        if "investment advice" in lower:
            return AgentTurn(
                messages=[
                    "I cannot provide investment advice. I can help with appointment booking details."
                ]
            )

        if session.state == State.GREET:
            session.state = State.DISCLAIMER_AWAIT_ACK
            return AgentTurn(messages=["Hello, I can help with advisor appointments.", DISCLAIMER])

        if session.state == State.DISCLAIMER_AWAIT_ACK:
            session.disclaimer_acknowledged = True
            session.state = State.INTENT_ROUTING
            return AgentTurn(
                messages=["Please share your request: book, reschedule, cancel, prepare, or availability."]
            )

        if session.state == State.INTENT_ROUTING:
            detected = self._detect_intent(lower)
            session.intent = detected.value

            if session.intent in {Intent.WHAT_TO_PREPARE.value, Intent.CHECK_AVAILABILITY.value}:
                session.state = State.CLOSE
                return AgentTurn(messages=[self._handle_non_booking(session.intent)])

            if session.intent in {Intent.RESCHEDULE.value, Intent.CANCEL.value}:
                session.state = State.CLOSE
                return AgentTurn(
                    messages=[
                        "Please share your booking code to continue this request. "
                        "For Phase 1, this branch is conversational only."
                    ]
                )

            session.state = State.BOOK_OFFER_SLOTS
            return AgentTurn(
                messages=["What topic is this about? (KYC, SIP, statements, withdrawals, account changes, nominee)"]
            )

        if session.state == State.BOOK_OFFER_SLOTS:
            if not session.topic:
                if not is_topic_allowed(text):
                    return AgentTurn(messages=["That topic is not supported yet. Please choose a supported topic."])
                session.topic = text
                slots = self.calendar.find_two_slots()
                session.offered_slots = [slot.label_ist for slot in slots]
                session.state = State.BOOK_CONFIRM
                return AgentTurn(
                    messages=[
                        "I can offer exactly two slots in IST:",
                        f"1) {session.offered_slots[0]}",
                        f"2) {session.offered_slots[1]}",
                        "Please reply with 1 or 2.",
                    ]
                )

        if session.state == State.BOOK_CONFIRM:
            selection = self._parse_slot_choice(lower)
            if selection is None:
                return AgentTurn(messages=["Please confirm by replying with 1 or 2."])
            session.selected_slot = session.offered_slots[selection]
            session.state = State.CLOSE
            return AgentTurn(
                messages=[
                    f"Confirmed in IST: {session.selected_slot}.",
                    "Phase 1 complete: no Calendar/Docs/Gmail writes are active.",
                ]
            )

        return AgentTurn(messages=["This session is complete. Start a new session for another request."])

    @staticmethod
    def _detect_intent(text: str) -> Intent:
        if "reschedule" in text:
            return Intent.RESCHEDULE
        if "cancel" in text:
            return Intent.CANCEL
        if "prepare" in text:
            return Intent.WHAT_TO_PREPARE
        if "availability" in text or "available" in text:
            return Intent.CHECK_AVAILABILITY
        if "book" in text or "appointment" in text:
            return Intent.BOOK_NEW
        return Intent.UNKNOWN

    @staticmethod
    def _parse_slot_choice(text: str) -> int | None:
        if "1" in text:
            return 0
        if "2" in text:
            return 1
        return None

    @staticmethod
    def _handle_non_booking(intent: str) -> str:
        if intent == Intent.WHAT_TO_PREPARE.value:
            return "Please prepare your topic details and prior statements. Avoid sharing personal identifiers."
        return "Current availability is open this week; for exact options, continue with booking flow."
