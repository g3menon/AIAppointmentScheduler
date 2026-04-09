class RelativeDateResolver:
    def resolve(self, date_phrase: str | None, today_ist: str) -> str | None:
        # Placeholder for deterministic date phrase resolution.
        if not date_phrase:
            return None
        return date_phrase


class TopicMapper:
    def map_topic(self, raw_text: str) -> str | None:
        # Placeholder fuzzy mapping.
        normalized = raw_text.strip().lower()
        if "kyc" in normalized:
            return "kyc_onboarding"
        return None

