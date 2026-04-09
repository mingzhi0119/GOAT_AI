"""Phase 15.8 — Clock injection into rate-limiter.

Tests verify InMemoryRateLimiter and the register_http_security middleware
using FakeClock so no real time passes and no time.sleep is needed.
"""

from __future__ import annotations

import unittest

from goat_ai.clocks import FakeClock
from backend.http_security import InMemoryRateLimiter


class TestInMemoryRateLimiterWithFakeClock(unittest.TestCase):
    """Unit tests for InMemoryRateLimiter.allow() with injectable `now`."""

    def _make(self) -> tuple[InMemoryRateLimiter, FakeClock]:
        return InMemoryRateLimiter(), FakeClock()

    # ── basic allow / block ───────────────────────────────────────────────────

    def test_first_request_always_allowed(self) -> None:
        limiter, clock = self._make()
        allowed, retry_after = limiter.allow(
            "key", now=clock.monotonic(), window_sec=60, max_requests=5
        )
        self.assertTrue(allowed)
        self.assertEqual(0, retry_after)

    def test_within_limit_all_allowed(self) -> None:
        limiter, clock = self._make()
        for _ in range(5):
            allowed, _ = limiter.allow(
                "key", now=clock.monotonic(), window_sec=60, max_requests=5
            )
            self.assertTrue(allowed)

    def test_at_limit_next_blocked(self) -> None:
        limiter, clock = self._make()
        for _ in range(5):
            limiter.allow("key", now=clock.monotonic(), window_sec=60, max_requests=5)

        allowed, retry_after = limiter.allow(
            "key", now=clock.monotonic(), window_sec=60, max_requests=5
        )
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_retry_after_is_within_window(self) -> None:
        limiter, clock = self._make()
        for _ in range(3):
            limiter.allow("key", now=clock.monotonic(), window_sec=30, max_requests=3)

        _, retry_after = limiter.allow(
            "key", now=clock.monotonic(), window_sec=30, max_requests=3
        )
        self.assertLessEqual(retry_after, 30)

    # ── window expiry ─────────────────────────────────────────────────────────

    def test_window_expiry_allows_again(self) -> None:
        limiter, clock = self._make()
        window = 60
        for _ in range(3):
            limiter.allow("key", now=clock.monotonic(), window_sec=window, max_requests=3)

        # Exhaust
        allowed, _ = limiter.allow(
            "key", now=clock.monotonic(), window_sec=window, max_requests=3
        )
        self.assertFalse(allowed)

        # Advance past the window
        clock.advance_monotonic(window + 1)
        allowed, retry_after = limiter.allow(
            "key", now=clock.monotonic(), window_sec=window, max_requests=3
        )
        self.assertTrue(allowed)
        self.assertEqual(0, retry_after)

    def test_partial_window_expiry_still_blocked(self) -> None:
        limiter, clock = self._make()
        window = 60
        for _ in range(3):
            limiter.allow("key", now=clock.monotonic(), window_sec=window, max_requests=3)

        # Advance only halfway
        clock.advance_monotonic(window / 2)
        allowed, _ = limiter.allow(
            "key", now=clock.monotonic(), window_sec=window, max_requests=3
        )
        self.assertFalse(allowed)

    # ── key isolation ─────────────────────────────────────────────────────────

    def test_different_keys_are_independent(self) -> None:
        limiter, clock = self._make()
        for _ in range(3):
            limiter.allow("keyA", now=clock.monotonic(), window_sec=60, max_requests=3)

        # keyA is exhausted
        allowed_a, _ = limiter.allow(
            "keyA", now=clock.monotonic(), window_sec=60, max_requests=3
        )
        self.assertFalse(allowed_a)

        # keyB is unaffected
        allowed_b, _ = limiter.allow(
            "keyB", now=clock.monotonic(), window_sec=60, max_requests=3
        )
        self.assertTrue(allowed_b)

    # ── sliding window ────────────────────────────────────────────────────────

    def test_sliding_window_clears_oldest_first(self) -> None:
        """Requests at t=0 should expire independently of requests made later."""
        limiter, clock = self._make()
        window = 60
        max_req = 3

        # t=0: fill 2 slots
        for _ in range(2):
            limiter.allow("key", now=clock.monotonic(), window_sec=window, max_requests=max_req)

        # t=30: fill last slot
        clock.advance_monotonic(30)
        limiter.allow("key", now=clock.monotonic(), window_sec=window, max_requests=max_req)

        # t=30: exhausted
        allowed, _ = limiter.allow(
            "key", now=clock.monotonic(), window_sec=window, max_requests=max_req
        )
        self.assertFalse(allowed)

        # t=61: first two slots expired (t=0+60<61), slot at t=30 still active → 1 slot open
        clock.advance_monotonic(31)
        allowed, _ = limiter.allow(
            "key", now=clock.monotonic(), window_sec=window, max_requests=max_req
        )
        self.assertTrue(allowed)


class TestRegisterHttpSecurityClockInjection(unittest.TestCase):
    """Integration test: middleware uses the injected clock for rate-limiting."""

    def _make_app(self, clock: FakeClock, max_requests: int = 2):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.http_security import register_http_security
        from backend.config import get_settings
        from goat_ai.config import Settings
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = Settings(
                ollama_base_url="http://127.0.0.1:11434",
                generate_timeout=120,
                max_upload_mb=20,
                max_upload_bytes=20 * 1024 * 1024,
                max_dataframe_rows=50000,
                use_chat_api=True,
                system_prompt="t",
                app_root=root,
                logo_svg=root / "x.svg",
                log_db_path=root / "db.sqlite",
                api_key="test-key",
                rate_limit_window_sec=60,
                rate_limit_max_requests=max_requests,
            )

        app = FastAPI()
        app.dependency_overrides[get_settings] = lambda: settings

        @app.get("/api/ping")
        async def _ping():
            return {"ok": True}

        register_http_security(app, clock=clock)
        return TestClient(app, raise_server_exceptions=False)

    def test_clock_injected_middleware_blocks_after_limit(self) -> None:
        clock = FakeClock()
        client = self._make_app(clock, max_requests=2)
        headers = {"X-GOAT-API-Key": "test-key"}

        r1 = client.get("/api/ping", headers=headers)
        r2 = client.get("/api/ping", headers=headers)
        self.assertEqual(200, r1.status_code)
        self.assertEqual(200, r2.status_code)

        r3 = client.get("/api/ping", headers=headers)
        self.assertEqual(429, r3.status_code)
        self.assertIn("Retry-After", r3.headers)

    def test_clock_advance_unblocks_after_window(self) -> None:
        clock = FakeClock()
        client = self._make_app(clock, max_requests=2)
        headers = {"X-GOAT-API-Key": "test-key"}

        client.get("/api/ping", headers=headers)
        client.get("/api/ping", headers=headers)
        self.assertEqual(429, client.get("/api/ping", headers=headers).status_code)

        # Advance the fake clock past the window without any real sleep
        clock.advance_monotonic(61)
        r = client.get("/api/ping", headers=headers)
        self.assertEqual(200, r.status_code)


if __name__ == "__main__":
    unittest.main()
