"""SQLiteIdempotencyStore with FakeClock — no ``time.sleep`` for TTL behaviour."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from backend.services.db_migrations import apply_migrations
from backend.services.idempotency_service import SQLiteIdempotencyStore
from goat_ai.clocks import FakeClock


class TestIdempotencyClock(unittest.TestCase):
    def test_replay_then_expiry_without_sleep(self) -> None:
        clock = FakeClock()
        ttl = 60
        tmp = tempfile.mkdtemp()
        try:
            db_path = Path(tmp) / "idem.db"
            apply_migrations(db_path)
            store = SQLiteIdempotencyStore(db_path=db_path, ttl_sec=ttl, clock=clock)

            r1 = store.claim(
                key="k1",
                route="/api/chat",
                scope="s1",
                request_hash="aa" * 32,
            )
            self.assertEqual(r1.state, "claimed")

            store.store_completed(
                key="k1",
                route="/api/chat",
                scope="s1",
                request_hash="aa" * 32,
                status_code=200,
                content_type="application/json",
                body="{}",
            )

            r2 = store.claim(
                key="k1",
                route="/api/chat",
                scope="s1",
                request_hash="aa" * 32,
            )
            self.assertEqual(r2.state, "replay")
            assert r2.completed is not None
            self.assertEqual(r2.completed.status_code, 200)

            clock.advance_utc(timedelta(seconds=ttl + 1))

            r3 = store.claim(
                key="k1",
                route="/api/chat",
                scope="s1",
                request_hash="aa" * 32,
            )
            self.assertEqual(r3.state, "claimed")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
