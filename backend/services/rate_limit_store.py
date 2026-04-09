"""Rate-limit storage adapters used by HTTP security wiring."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol


class RateLimitStore(Protocol):
    """Minimal persistence contract for sliding-window timestamps."""

    def get_timestamps(self, key: str, *, now: float, window_sec: int) -> list[float]:
        """Return the active timestamps for the provided bucket key."""

    def replace_timestamps(self, key: str, timestamps: list[float]) -> None:
        """Persist the active timestamps for the provided bucket key."""


@dataclass
class InMemorySlidingWindowRateLimitStore:
    """Thread-safe in-memory store for sliding-window rate limiting."""

    _timestamps_by_key: dict[str, deque[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_timestamps(self, key: str, *, now: float, window_sec: int) -> list[float]:
        with self._lock:
            bucket = self._timestamps_by_key.setdefault(key, deque())
            cutoff = now - float(window_sec)
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            return list(bucket)

    def replace_timestamps(self, key: str, timestamps: list[float]) -> None:
        with self._lock:
            self._timestamps_by_key[key] = deque(
                sorted(float(timestamp) for timestamp in timestamps)
            )
