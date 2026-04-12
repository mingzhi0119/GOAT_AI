from __future__ import annotations

from dataclasses import dataclass

from backend.services.rate_limiter import StoredSlidingWindowRateLimiter


@dataclass(frozen=True)
class _Decision:
    allowed: bool
    retry_after: int


class _Store:
    def __init__(self, timestamps: list[float] | None = None) -> None:
        self.timestamps = list(timestamps or [])
        self.replaced: list[tuple[str, list[float]]] = []

    def get_timestamps(self, key: str, *, now: float, window_sec: int) -> list[float]:
        _ = now, window_sec
        self.last_key = key
        return list(self.timestamps)

    def replace_timestamps(self, key: str, timestamps: list[float]) -> None:
        self.replaced.append((key, list(timestamps)))
        self.timestamps = list(timestamps)


class _Policy:
    window_sec = 60

    def __init__(self, *, allowed: bool) -> None:
        self.allowed = allowed
        self.seen_subjects: list[object] = []

    def key_for(self, subject: object) -> str:
        self.seen_subjects.append(subject)
        return "bucket-1"

    def decide(self, observed_timestamps: list[float], *, now: float) -> _Decision:
        _ = observed_timestamps, now
        return _Decision(allowed=self.allowed, retry_after=17)


def test_stored_sliding_window_rate_limiter_records_allowed_request() -> None:
    store = _Store([1.0, 2.0])
    policy = _Policy(allowed=True)
    limiter = StoredSlidingWindowRateLimiter(policy=policy, store=store)

    decision = limiter.evaluate(subject={"route": "/api/chat"}, now=3.0)

    assert decision.allowed is True
    assert policy.seen_subjects == [{"route": "/api/chat"}]
    assert store.replaced == [("bucket-1", [1.0, 2.0, 3.0])]


def test_stored_sliding_window_rate_limiter_keeps_store_unchanged_when_blocked() -> (
    None
):
    store = _Store([1.0, 2.0])
    limiter = StoredSlidingWindowRateLimiter(
        policy=_Policy(allowed=False),
        store=store,
    )

    decision = limiter.evaluate(subject={"route": "/api/chat"}, now=3.0)

    assert decision.allowed is False
    assert decision.retry_after == 17
    assert store.replaced == []
