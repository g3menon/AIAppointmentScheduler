"""Topic whitelist per Architecture.md §9 Phase 1 and §11.4."""

from phase1.domain.models import Topic

_TOPIC_ALIASES: dict[str, Topic] = {
    "kyc": Topic.KYC_ONBOARDING,
    "onboarding": Topic.KYC_ONBOARDING,
    "kyc/onboarding": Topic.KYC_ONBOARDING,
    "sip": Topic.SIP_MANDATES,
    "mandates": Topic.SIP_MANDATES,
    "sip/mandates": Topic.SIP_MANDATES,
    "statements": Topic.STATEMENTS_TAX_DOCS,
    "tax docs": Topic.STATEMENTS_TAX_DOCS,
    "statements/tax docs": Topic.STATEMENTS_TAX_DOCS,
    "withdrawals": Topic.WITHDRAWALS_TIMELINES,
    "withdrawals & timelines": Topic.WITHDRAWALS_TIMELINES,
    "account changes": Topic.ACCOUNT_CHANGES_NOMINEE,
    "nominee": Topic.ACCOUNT_CHANGES_NOMINEE,
    "account changes/nominee": Topic.ACCOUNT_CHANGES_NOMINEE,
}


def is_topic_allowed(topic: str) -> bool:
    return topic.strip().lower() in _TOPIC_ALIASES


def resolve_topic(topic: str) -> Topic | None:
    return _TOPIC_ALIASES.get(topic.strip().lower())
