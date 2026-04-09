from dataclasses import dataclass


@dataclass
class NluResult:
    intent: str
    topic: str | None
    date_phrase: str | None
    time_window: str | None
    booking_code_guess: str | None
    wants_investment_advice: bool
    confidence: float


class NluEngine:
    def parse(self, transcript: str, state: str) -> NluResult:
        # Phase scaffold only; replace with LLM/rules implementation.
        return NluResult(
            intent="unknown",
            topic=None,
            date_phrase=None,
            time_window=None,
            booking_code_guess=None,
            wants_investment_advice=False,
            confidence=0.0,
        )

