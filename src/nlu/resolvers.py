from __future__ import annotations

from datetime import date, timedelta

_TOPIC_ALIASES: dict[str, str] = {
    "kyc": "KYC/Onboarding",
    "onboarding": "KYC/Onboarding",
    "sip": "SIP/Mandates",
    "mandates": "SIP/Mandates",
    "statements": "Statements/Tax Docs",
    "tax": "Statements/Tax Docs",
    "withdrawals": "Withdrawals & Timelines",
    "timeline": "Withdrawals & Timelines",
    "account changes": "Account Changes/Nominee",
    "nominee": "Account Changes/Nominee",
}


class RelativeDateResolver:
    def resolve(self, date_phrase: str | None, today_ist: str) -> str | None:
        if not date_phrase:
            return None

        normalized = date_phrase.strip().lower()
        if not normalized:
            return None

        today = date.fromisoformat(today_ist)
        if "today" in normalized:
            return today.isoformat()
        if "tomorrow" in normalized:
            return (today + timedelta(days=1)).isoformat()
        if "next week" in normalized:
            return (today + timedelta(days=7)).isoformat()
        return None


class TopicMapper:
    def map_topic(self, raw_text: str) -> str | None:
        normalized = raw_text.strip().lower()
        if not normalized:
            return None

        for alias, canonical in _TOPIC_ALIASES.items():
            if alias in normalized:
                return canonical
        return None

