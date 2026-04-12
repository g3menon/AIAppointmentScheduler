from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from src.nlu.resolvers import RelativeDateResolver, TopicMapper

_BOOKING_CODE = re.compile(r"\b[A-Z]{2}-[A-Z]\d{3}\b", re.IGNORECASE)
_TIME_WINDOWS = ("morning", "afternoon", "evening")
_PII_SIGNALS = ("@", "account number", "aadhaar", "pan ", "phone")

_INTENT_SET = {
    "book_new",
    "reschedule",
    "cancel",
    "what_to_prepare",
    "check_availability",
    "unknown",
}

@dataclass
class NluResult:
    intent: str
    topic: str | None
    time_preference: str | None
    resolved_date_ist: str | None
    booking_code_guess: str | None
    confidence: float
    policy_flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.intent not in _INTENT_SET:
            raise ValueError(f"Invalid intent: {self.intent}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")


class NluEngine:
    def __init__(self) -> None:
        self._topic_mapper = TopicMapper()
        self._date_resolver = RelativeDateResolver()

    def parse(self, transcript: str, state: str) -> NluResult:
        text = (transcript or "").strip()
        lower = text.lower()
        policy_flags: list[str] = []
        if "investment advice" in lower:
            policy_flags.append("investment_advice_refusal")
        if any(signal in lower for signal in _PII_SIGNALS):
            policy_flags.append("pii_detected")

        intent = "unknown"
        if "reschedule" in lower:
            intent = "reschedule"
        elif "cancel" in lower:
            intent = "cancel"
        elif "prepare" in lower:
            intent = "what_to_prepare"
        elif "availability" in lower or "available" in lower:
            intent = "check_availability"
        elif "book" in lower or "appointment" in lower:
            intent = "book_new"

        topic = self._topic_mapper.map_topic(lower)
        date_phrase = self._extract_date_phrase(lower)
        resolved_date_ist = self._date_resolver.resolve(date_phrase, datetime.now().date().isoformat())
        time_window = self._extract_time_window(lower)
        booking_code_guess = self._extract_booking_code(text)

        return NluResult(
            intent=intent,
            topic=topic,
            time_preference=time_window or date_phrase,
            resolved_date_ist=resolved_date_ist,
            booking_code_guess=booking_code_guess,
            policy_flags=policy_flags,
            confidence=0.92 if intent != "unknown" else 0.4,
        )

    @staticmethod
    def _extract_date_phrase(lower: str) -> str | None:
        for token in ("today", "tomorrow", "next week"):
            if token in lower:
                return token
        return None

    @staticmethod
    def _extract_time_window(lower: str) -> str | None:
        for token in _TIME_WINDOWS:
            if token in lower:
                return token
        return None

    @staticmethod
    def _extract_booking_code(text: str) -> str | None:
        match = _BOOKING_CODE.search(text)
        if not match:
            return None
        return match.group(0).upper()

