from __future__ import annotations

import unittest

from backend.domain.rate_limit_policy import (
    RateLimitPolicy,
    RateLimitSubject,
    fingerprint_api_key,
)


class TestRateLimitPolicyDomain(unittest.TestCase):
    def test_fingerprint_is_stable_and_hides_raw_key(self) -> None:
        key = "test-api-key"
        fingerprint = fingerprint_api_key(key)
        self.assertEqual(fingerprint, fingerprint_api_key(key))
        self.assertNotIn(key, fingerprint)
        self.assertNotEqual(fingerprint, fingerprint_api_key("other-key"))

    def test_key_derivation_includes_subject_dimensions(self) -> None:
        policy = RateLimitPolicy(window_sec=60, max_requests=2)
        subject = RateLimitSubject(
            api_key_fingerprint=fingerprint_api_key("test-api-key"),
            owner_id="alice",
            route_group="/api/chat",
            method_class="write",
        )
        baseline = policy.key_for(subject)
        self.assertEqual(baseline, policy.key_for(subject))
        self.assertNotIn("test-api-key", baseline)
        self.assertNotEqual(
            baseline,
            policy.key_for(
                RateLimitSubject(
                    api_key_fingerprint=fingerprint_api_key("test-api-key"),
                    owner_id="bob",
                    route_group="/api/chat",
                    method_class="write",
                )
            ),
        )
        self.assertNotEqual(
            baseline,
            policy.key_for(
                RateLimitSubject(
                    api_key_fingerprint=fingerprint_api_key("test-api-key"),
                    owner_id="alice",
                    route_group="/api/history",
                    method_class="write",
                )
            ),
        )
        self.assertNotEqual(
            baseline,
            policy.key_for(
                RateLimitSubject(
                    api_key_fingerprint=fingerprint_api_key("test-api-key"),
                    owner_id="alice",
                    route_group="/api/chat",
                    method_class="read",
                )
            ),
        )

    def test_decide_allows_until_limit_then_blocks(self) -> None:
        policy = RateLimitPolicy(window_sec=60, max_requests=2)
        allowed = policy.decide([100.0], now=120.0)
        self.assertTrue(allowed.allowed)
        self.assertEqual(0, allowed.retry_after)

        blocked = policy.decide([100.0, 110.0], now=120.0)
        self.assertFalse(blocked.allowed)
        self.assertEqual(40, blocked.retry_after)

    def test_window_expiry_allows_again(self) -> None:
        policy = RateLimitPolicy(window_sec=60, max_requests=1)
        blocked = policy.decide([100.0], now=120.0)
        self.assertFalse(blocked.allowed)
        self.assertEqual(40, blocked.retry_after)

        allowed = policy.decide([100.0], now=161.0)
        self.assertTrue(allowed.allowed)
        self.assertEqual(0, allowed.retry_after)


if __name__ == "__main__":
    unittest.main()
