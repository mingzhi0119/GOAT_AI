"""Phase 15.8/15.11 rate-limit clock and middleware delegation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.domain.rate_limit_policy import RateLimitPolicy
from goat_ai.shared.clocks import FakeClock


class FakeRateLimitStore:
    def __init__(self) -> None:
        self._timestamps: dict[str, list[float]] = {}
        self.get_calls: list[tuple[str, float, int]] = []
        self.replace_calls: list[tuple[str, list[float]]] = []

    def get_timestamps(self, key: str, *, now: float, window_sec: int) -> list[float]:
        self.get_calls.append((key, now, window_sec))
        bucket = self._timestamps.setdefault(key, [])
        cutoff = now - float(window_sec)
        bucket = [timestamp for timestamp in bucket if timestamp > cutoff]
        self._timestamps[key] = bucket
        return list(bucket)

    def replace_timestamps(self, key: str, timestamps: list[float]) -> None:
        snapshot = sorted(float(timestamp) for timestamp in timestamps)
        self._timestamps[key] = snapshot
        self.replace_calls.append((key, snapshot))


class TestRegisterHttpSecurityClockInjection(unittest.TestCase):
    """Integration test: middleware delegates to policy + store with fake clock."""

    def _make_app(
        self,
        clock: FakeClock,
        store: FakeRateLimitStore,
        *,
        window_sec: int = 60,
        max_requests: int = 2,
    ):
        import backend.platform.http_security as http_security
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from goat_ai.config.settings import Settings

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
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
                rate_limit_window_sec=window_sec,
                rate_limit_max_requests=max_requests,
            )

        app = FastAPI()
        app.dependency_overrides[http_security.get_settings] = lambda: settings

        @app.get("/api/ping")
        async def _ping():
            return {"ok": True}

        http_security.register_http_security(
            app,
            clock=clock,
            rate_limit_policy_factory=lambda resolved_settings: RateLimitPolicy(
                window_sec=resolved_settings.rate_limit_window_sec,
                max_requests=resolved_settings.rate_limit_max_requests,
            ),
            rate_limit_store=store,
        )
        return TestClient(app, raise_server_exceptions=False)

    def test_middleware_blocks_after_limit_and_records_store_access(self) -> None:
        clock = FakeClock()
        store = FakeRateLimitStore()
        client = self._make_app(clock, store, max_requests=2)
        headers = {"X-GOAT-API-Key": "test-key"}

        r1 = client.get("/api/ping", headers=headers)
        r2 = client.get("/api/ping", headers=headers)
        r3 = client.get("/api/ping", headers=headers)

        self.assertEqual(200, r1.status_code)
        self.assertEqual(200, r2.status_code)
        self.assertEqual(429, r3.status_code)
        self.assertIn("Retry-After", r3.headers)
        self.assertEqual(3, len(store.get_calls))
        self.assertEqual(2, len(store.replace_calls))

    def test_clock_advance_unblocks_after_window(self) -> None:
        clock = FakeClock()
        store = FakeRateLimitStore()
        client = self._make_app(clock, store, max_requests=2)
        headers = {"X-GOAT-API-Key": "test-key"}

        client.get("/api/ping", headers=headers)
        client.get("/api/ping", headers=headers)
        self.assertEqual(429, client.get("/api/ping", headers=headers).status_code)

        clock.advance_monotonic(61)
        r = client.get("/api/ping", headers=headers)
        self.assertEqual(200, r.status_code)


if __name__ == "__main__":
    unittest.main()
