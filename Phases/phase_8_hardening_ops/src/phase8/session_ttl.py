"""Session TTL (time-to-live) cleanup policy.

Wraps InMemorySessionStore to periodically purge sessions that have been
idle longer than SESSION_TTL_SECONDS.  The purge runs lazily on access,
keeping the implementation lock-free and suitable for single-process
deployments.
"""

from __future__ import annotations

import time

from phase8.runtime_controls import SESSION_TTL_SECONDS


class SessionTimestamps:
    """Tracks created_at and last_active_at for each session_id."""

    def __init__(self) -> None:
        self._timestamps: dict[str, float] = {}

    def touch(self, session_id: str) -> None:
        now = time.monotonic()
        if session_id not in self._timestamps:
            self._timestamps[session_id] = now
        self._timestamps[session_id] = now

    def last_active(self, session_id: str) -> float | None:
        return self._timestamps.get(session_id)

    def stale_ids(self, ttl_seconds: int | None = None) -> list[str]:
        cutoff = time.monotonic() - (ttl_seconds or SESSION_TTL_SECONDS)
        return [
            sid for sid, ts in self._timestamps.items()
            if ts < cutoff
        ]

    def remove(self, session_id: str) -> None:
        self._timestamps.pop(session_id, None)

    def clear(self) -> None:
        self._timestamps.clear()

    def __len__(self) -> int:
        return len(self._timestamps)
