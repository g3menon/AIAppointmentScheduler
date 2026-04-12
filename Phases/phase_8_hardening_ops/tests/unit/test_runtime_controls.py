"""Unit tests for Phase 8 runtime controls: turn limits and request size guards."""

import pytest

from phase8.runtime_controls import (
    MAX_REQUEST_LENGTH,
    MAX_TURN_COUNT,
    RequestTooLarge,
    TurnLimitExceeded,
    guard_request_size,
    guard_turn_limit,
)


def test_guard_turn_limit_allows_within_bound() -> None:
    guard_turn_limit(1)
    guard_turn_limit(MAX_TURN_COUNT)


def test_guard_turn_limit_rejects_above_bound() -> None:
    with pytest.raises(TurnLimitExceeded):
        guard_turn_limit(MAX_TURN_COUNT + 1)


def test_guard_request_size_allows_normal_text() -> None:
    guard_request_size("book a new appointment")


def test_guard_request_size_allows_at_boundary() -> None:
    guard_request_size("x" * MAX_REQUEST_LENGTH)


def test_guard_request_size_rejects_oversized() -> None:
    with pytest.raises(RequestTooLarge):
        guard_request_size("x" * (MAX_REQUEST_LENGTH + 1))
