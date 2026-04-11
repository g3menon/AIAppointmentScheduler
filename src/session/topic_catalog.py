ALLOWED_TOPICS = {
    "kyc",
    "onboarding",
    "sip",
    "mandates",
    "statements",
    "tax docs",
    "withdrawals",
    "account changes",
    "nominee",
}


def is_topic_allowed(topic: str) -> bool:
    topic_key = topic.strip().lower()
    return topic_key in ALLOWED_TOPICS
