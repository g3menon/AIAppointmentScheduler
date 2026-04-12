from src.nlu.engine import NluEngine
from src.nlu.resolvers import RelativeDateResolver, TopicMapper


def test_topic_mapper_returns_canonical_topic() -> None:
    mapper = TopicMapper()
    assert mapper.map_topic("Need help with KYC onboarding") == "KYC/Onboarding"
    assert mapper.map_topic("SIP mandate setup") == "SIP/Mandates"


def test_relative_date_resolver_handles_common_phrases() -> None:
    resolver = RelativeDateResolver()
    assert resolver.resolve("today", "2026-04-12") == "2026-04-12"
    assert resolver.resolve("tomorrow", "2026-04-12") == "2026-04-13"
    assert resolver.resolve("next week", "2026-04-12") == "2026-04-19"


def test_nlu_engine_emits_structured_schema() -> None:
    result = NluEngine().parse("Book appointment for KYC tomorrow afternoon", "intent_routing")
    assert result.intent == "book_new"
    assert result.topic == "KYC/Onboarding"
    assert result.time_preference in {"tomorrow", "afternoon"}
    assert isinstance(result.policy_flags, list)
    assert 0.0 <= result.confidence <= 1.0


def test_nlu_engine_flags_policy_risks_and_code_guess() -> None:
    result = NluEngine().parse(
        "Please reschedule AB-C123 and also give investment advice at me@example.com",
        "reschedule_collect_code",
    )
    assert result.intent == "reschedule"
    assert result.booking_code_guess == "AB-C123"
    assert "investment_advice_refusal" in result.policy_flags
    assert "pii_detected" in result.policy_flags
