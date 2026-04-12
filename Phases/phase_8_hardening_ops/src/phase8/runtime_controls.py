"""Runtime abuse controls: turn limits, request size guards, session TTL.

Enforced by the orchestrator and session store layers. Constants are
module-level so they can be patched in tests if needed.
"""

from __future__ import annotations

MAX_TURN_COUNT: int = 50
MAX_REQUEST_LENGTH: int = 16_000
SESSION_TTL_SECONDS: int = 3600  # 1 hour


class TurnLimitExceeded(RuntimeError):
    """Raised when a session exceeds the maximum allowed turns."""


class RequestTooLarge(RuntimeError):
    """Raised when a single user message exceeds the size limit."""


def guard_turn_limit(turn_count: int) -> None:
    if turn_count > MAX_TURN_COUNT:
        raise TurnLimitExceeded(
            f"Session exceeded {MAX_TURN_COUNT} turns. "
            "Please start a new session."
        )


def guard_request_size(text: str) -> None:
    if len(text) > MAX_REQUEST_LENGTH:
        raise RequestTooLarge(
            f"Message length {len(text)} exceeds the "
            f"{MAX_REQUEST_LENGTH}-character limit."
        )
