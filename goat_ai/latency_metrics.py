"""In-process rolling window for chat inference duration (milliseconds).

Used by ``GET /api/system/inference`` for the UI status strip. Single-process
assumption: one Uvicorn worker; no cross-worker aggregation.
"""
from __future__ import annotations

import threading
from collections import deque

_lock = threading.Lock()
_chat_ms: deque[float] | None = None


def init_latency_metrics(max_samples: int) -> None:
    """Configure deque capacity; safe to call once at app startup."""
    global _chat_ms
    n = max(1, int(max_samples))
    with _lock:
        _chat_ms = deque(maxlen=n)


def record_chat_inference_ms(elapsed_ms: float) -> None:
    """Append one completed chat stream duration (wall-clock, ms)."""
    with _lock:
        if _chat_ms is None:
            return
        _chat_ms.append(float(elapsed_ms))


def get_inference_snapshot() -> dict[str, float | int]:
    """Return rolling average and sample count for chat completions."""
    with _lock:
        if _chat_ms is None or len(_chat_ms) == 0:
            return {"chat_avg_ms": 0.0, "chat_sample_count": 0}
        total = sum(_chat_ms)
        n = len(_chat_ms)
        return {"chat_avg_ms": round(total / n, 1), "chat_sample_count": n}
