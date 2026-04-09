"""Rate-limit domain policy: decision type and pure policy helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a single rate-limit evaluation.

    Attributes:
        allowed:     True when the request should proceed.
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
