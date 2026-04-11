"""Replaceable rate-limiter boundary over the current sliding-window store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.services.rate_limit_store import RateLimitStore


class RateLimitDecisionLike(Protocol):
    allowed: bool
    retry_after: int


class RateLimitPolicyLike(Protocol):
    window_sec: int

    def key_for(self, subject: object) -> str: ...

    def decide(
        self, observed_timestamps: list[float], *, now: float
    ) -> RateLimitDecisionLike: ...


class RateLimiter(Protocol):
    """Execution boundary for one rate-limit decision."""

    def evaluate(self, *, subject: object, now: float) -> RateLimitDecisionLike: ...


@dataclass
class StoredSlidingWindowRateLimiter:
    """Rate limiter backed by a store/policy pair.

    Keeping this orchestration behind one boundary makes it easier to replace the
    current in-memory implementation with a shared store later without rewriting
    the HTTP middleware contract.
    """

    policy: RateLimitPolicyLike
    store: RateLimitStore

    def evaluate(self, *, subject: object, now: float) -> RateLimitDecisionLike:
        key = self.policy.key_for(subject)
        timestamps = self.store.get_timestamps(
            key,
            now=now,
            window_sec=self.policy.window_sec,
        )
        decision = self.policy.decide(timestamps, now=now)
        if decision.allowed:
            self.store.replace_timestamps(key, [*timestamps, now])
        return decision
