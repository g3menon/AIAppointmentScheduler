"""Unit tests — topic catalog per Architecture.md §9 Phase 1."""

from phase1.domain.models import Topic
from phase1.session.topic_catalog import is_topic_allowed, resolve_topic


# ── whitelist acceptance ─────────────────────────────────────────────


def test_kyc_accepted() -> None:
    assert is_topic_allowed("KYC")


def test_sip_accepted() -> None:
    assert is_topic_allowed("SIP")


def test_statements_accepted() -> None:
    assert is_topic_allowed("statements")


def test_withdrawals_accepted() -> None:
    assert is_topic_allowed("withdrawals")


def test_nominee_accepted() -> None:
    assert is_topic_allowed("nominee")


def test_account_changes_accepted() -> None:
    assert is_topic_allowed("account changes")


def test_case_insensitive() -> None:
    assert is_topic_allowed("kyc")
    assert is_topic_allowed("Kyc")
    assert is_topic_allowed("KYC")


# ── whitelist rejection ──────────────────────────────────────────────


def test_rejects_unsupported_topic() -> None:
    assert not is_topic_allowed("portfolio advice")


def test_rejects_empty_string() -> None:
    assert not is_topic_allowed("")


# ── resolve_topic returns correct enum ───────────────────────────────


def test_resolve_kyc() -> None:
    assert resolve_topic("KYC") == Topic.KYC_ONBOARDING


def test_resolve_sip_alias() -> None:
    assert resolve_topic("mandates") == Topic.SIP_MANDATES


def test_resolve_unsupported_returns_none() -> None:
    assert resolve_topic("crypto") is None
