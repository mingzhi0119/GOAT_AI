"""Rate-limit domain policy: subject, decision, and pure policy helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitSubject:
    """Stable subject used to derive a rate-limit bucket key."""

    api_key_fingerprint: str
    owner_id: str
    route_group: str
    method_class: str


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a single rate-limit evaluation.

    Attributes:
        allowed: True when the request should proceed.
        retry_after: Seconds the caller should wait before retrying.
            Always 0 when *allowed* is True.
    """

    allowed: bool
    retry_after: int

    def __post_init__(self) -> None:
        if self.allowed and self.retry_after != 0:
            raise ValueError("retry_after must be 0 when allowed is True")
        if not self.allowed and self.retry_after < 1:
            raise ValueError("retry_after must be >= 1 when allowed is False")


@dataclass(frozen=True)
class RateLimitPolicy:
    """Pure sliding-window policy for request admission."""

    window_sec: int
    max_requests: int

    def __post_init__(self) -> None:
        if self.window_sec <= 0:
            raise ValueError("window_sec must be > 0")
        if self.max_requests <= 0:
            raise ValueError("max_requests must be > 0")

    def key_for(self, subject: object) -> str:
        """Derive a stable storage key from a rate-limit subject."""
        canonical = {
            "api_key_fingerprint": _subject_value(subject, "api_key_fingerprint"),
            "method_class": _subject_value(subject, "method_class"),
            "owner_id": _subject_value(subject, "owner_id"),
            "route_group": _subject_value(subject, "route_group"),
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()

    def decide(self, observed_timestamps: list[float], *, now: float) -> RateLimitDecision:
        """Return whether a request is allowed and the retry delay when blocked."""
        windowed = sorted(
            float(timestamp)
            for timestamp in observed_timestamps
            if now - float(timestamp) < float(self.window_sec)
        )
        if len(windowed) >= self.max_requests:
            retry_after = max(1, int(windowed[0] + float(self.window_sec) - now))
            return RateLimitDecision(allowed=False, retry_after=retry_after)
        return RateLimitDecision(allowed=True, retry_after=0)


def fingerprint_api_key(api_key: str) -> str:
    """Return an irreversible fingerprint for an API key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _subject_value(subject: object, name: str) -> str:
    if isinstance(subject, RateLimitSubject):
        return getattr(subject, name)
    if isinstance(subject, dict):
        value = subject.get(name, "")
        if isinstance(value, str):
            return value
        return str(value)
    value = getattr(subject, name, "")
    if isinstance(value, str):
        return value
    return str(value)
