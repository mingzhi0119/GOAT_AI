from __future__ import annotations

import unittest

from backend.http_security import InMemoryRateLimiter


class InMemoryRateLimiterTests(unittest.TestCase):
    def test_allow_within_threshold(self) -> None:
        limiter = InMemoryRateLimiter()
        allowed1, retry1 = limiter.allow(
            "key", now=100.0, window_sec=60, max_requests=2
        )
        allowed2, retry2 = limiter.allow(
            "key", now=101.0, window_sec=60, max_requests=2
        )
        self.assertTrue(allowed1)
        self.assertEqual(0, retry1)
        self.assertTrue(allowed2)
        self.assertEqual(0, retry2)

    def test_blocks_after_threshold_and_returns_retry_after(self) -> None:
        limiter = InMemoryRateLimiter()
        limiter.allow("key", now=100.0, window_sec=60, max_requests=2)
        limiter.allow("key", now=101.0, window_sec=60, max_requests=2)
        allowed, retry_after = limiter.allow(
            "key", now=102.0, window_sec=60, max_requests=2
        )
        self.assertFalse(allowed)
        self.assertEqual(58, retry_after)

    def test_expires_old_requests_after_window(self) -> None:
        limiter = InMemoryRateLimiter()
        limiter.allow("key", now=100.0, window_sec=60, max_requests=1)
        blocked, retry_after = limiter.allow(
            "key", now=120.0, window_sec=60, max_requests=1
        )
        self.assertFalse(blocked)
        self.assertEqual(40, retry_after)

        allowed_again, retry_again = limiter.allow(
            "key", now=161.0, window_sec=60, max_requests=1
        )
        self.assertTrue(allowed_again)
        self.assertEqual(0, retry_again)

    def test_tracks_each_key_independently(self) -> None:
        limiter = InMemoryRateLimiter()
        limiter.allow("key-a", now=100.0, window_sec=60, max_requests=1)

        blocked_a, retry_a = limiter.allow(
            "key-a", now=101.0, window_sec=60, max_requests=1
        )
        allowed_b, retry_b = limiter.allow(
            "key-b", now=101.0, window_sec=60, max_requests=1
        )

        self.assertFalse(blocked_a)
        self.assertGreater(retry_a, 0)
        self.assertTrue(allowed_b)
        self.assertEqual(0, retry_b)


if __name__ == "__main__":
    unittest.main()
