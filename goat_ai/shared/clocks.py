"""Injectable time sources for TTL, rate limits, and tests (no `time.sleep`)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Wall clock (UTC) plus a monotonic counter for intervals."""

    def utc_now(self) -> datetime:
        """Timezone-aware UTC `datetime`."""
        ...

    def monotonic(self) -> float:
        """Opaque monotonic seconds (see `time.monotonic`)."""
        ...


class SystemClock:
    """Production clock backed by the system."""

    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


@dataclass
class FakeClock:
    """Test clock with a controllable UTC instant and monotonic counter."""

    _utc: datetime = field(
        default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    _mono: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self._utc, str):
            parsed = datetime.fromisoformat(self._utc.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            self._utc = parsed

    def utc_now(self) -> datetime:
        return self._utc

    def monotonic(self) -> float:
        return self._mono

    def advance_utc(self, delta: timedelta) -> None:
        self._utc = self._utc + delta

    def advance_monotonic(self, seconds: float) -> None:
        self._mono += seconds
