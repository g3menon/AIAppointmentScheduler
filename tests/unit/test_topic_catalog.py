from src.session.topic_catalog import is_topic_allowed


def test_topic_whitelist_accepts_supported_topics() -> None:
    assert is_topic_allowed("KYC")
    assert is_topic_allowed("SIP")


def test_topic_whitelist_rejects_unsupported_topic() -> None:
    assert not is_topic_allowed("portfolio advice")
