"""Unit tests for session TTL cleanup and the hardened session store."""

import time
from unittest.mock import patch

from phase1.session.session_context import SessionContext
from phase1.session.session_store import InMemorySessionStore
from phase8.session_ttl import SessionTimestamps


class TestSessionTimestamps:
    def test_touch_creates_entry(self) -> None:
        ts = SessionTimestamps()
        ts.touch("s1")
        assert ts.last_active("s1") is not None
        assert len(ts) == 1

    def test_stale_ids_returns_expired(self) -> None:
        ts = SessionTimestamps()
        ts.touch("old-session")
        with patch("time.monotonic", return_value=time.monotonic() + 7200):
            stale = ts.stale_ids(ttl_seconds=3600)
        assert "old-session" in stale

    def test_stale_ids_excludes_fresh(self) -> None:
        ts = SessionTimestamps()
        ts.touch("fresh-session")
        stale = ts.stale_ids(ttl_seconds=3600)
        assert "fresh-session" not in stale

    def test_remove_deletes_entry(self) -> None:
        ts = SessionTimestamps()
        ts.touch("s1")
        ts.remove("s1")
        assert ts.last_active("s1") is None
        assert len(ts) == 0

    def test_clear_removes_all(self) -> None:
        ts = SessionTimestamps()
        ts.touch("s1")
        ts.touch("s2")
        ts.clear()
        assert len(ts) == 0


class TestSessionStorePurge:
    def test_purge_stale_removes_old_sessions(self) -> None:
        store = InMemorySessionStore()
        store.get_or_create("will-be-stale")
        store.get_or_create("will-be-fresh")

        old_ts = store._timestamps._timestamps["will-be-stale"]
        store._timestamps._timestamps["will-be-stale"] = old_ts - 7200

        purged = store.purge_stale(ttl_seconds=3600)
        assert "will-be-stale" in purged
        assert "will-be-fresh" not in purged
        assert store.session_count == 1

    def test_purge_stale_returns_empty_when_all_fresh(self) -> None:
        store = InMemorySessionStore()
        store.get_or_create("fresh")
        purged = store.purge_stale(ttl_seconds=3600)
        assert purged == []
        assert store.session_count == 1

    def test_session_count_property(self) -> None:
        store = InMemorySessionStore()
        assert store.session_count == 0
        store.get_or_create("s1")
        assert store.session_count == 1
        store.get_or_create("s2")
        assert store.session_count == 2

    def test_put_updates_timestamp(self) -> None:
        store = InMemorySessionStore()
        ctx = SessionContext(session_id="s1")
        store.put(ctx)
        assert store._timestamps.last_active("s1") is not None
