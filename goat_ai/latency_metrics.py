"""In-process rolling window for chat inference duration (milliseconds).

Used by ``GET /api/system/inference`` for the UI status strip. Single-process
assumption: one Uvicorn worker; no cross-worker aggregation.
"""
from __future__ import annotations

import threading
from collections import deque
from statistics import quantiles

_lock = threading.Lock()
_chat_ms: deque[float] | None = None
_first_token_ms: deque[float] | None = None
_chat_ms_by_model: dict[str, deque[float]] | None = None
_first_token_ms_by_model: dict[str, deque[float]] | None = None
_max_samples = 20


def init_latency_metrics(max_samples: int) -> None:
    """Configure deque capacity; safe to call once at app startup."""
    global _chat_ms, _first_token_ms, _chat_ms_by_model, _first_token_ms_by_model, _max_samples
    n = max(1, int(max_samples))
    with _lock:
        _max_samples = n
        _chat_ms = deque(maxlen=n)
        _first_token_ms = deque(maxlen=n)
        _chat_ms_by_model = {}
        _first_token_ms_by_model = {}


def _ensure_model_bucket(
    buckets: dict[str, deque[float]] | None,
    model: str,
) -> deque[float] | None:
    if buckets is None:
        return None
    bucket = buckets.get(model)
    if bucket is None:
        bucket = deque(maxlen=_max_samples)
        buckets[model] = bucket
    return bucket


def record_chat_inference_ms(elapsed_ms: float, model: str | None = None) -> None:
    """Append one completed chat stream duration (wall-clock, ms)."""
    with _lock:
        if _chat_ms is None:
            return
        _chat_ms.append(float(elapsed_ms))
        if model:
            bucket = _ensure_model_bucket(_chat_ms_by_model, model)
            if bucket is not None:
                bucket.append(float(elapsed_ms))


def record_chat_first_token_ms(elapsed_ms: float, model: str | None = None) -> None:
    """Append one first-token latency sample (wall-clock, ms)."""
    with _lock:
        if _first_token_ms is None:
            return
        _first_token_ms.append(float(elapsed_ms))
        if model:
            bucket = _ensure_model_bucket(_first_token_ms_by_model, model)
            if bucket is not None:
                bucket.append(float(elapsed_ms))


def _mean(values: deque[float] | list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _p50(values: deque[float] | list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return round(ordered[mid], 1)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 1)


def _p95(values: deque[float] | list[float]) -> float:
    if not values:
        return 0.0
    if len(values) < 2:
        return round(float(values[0]), 1)
    pct = quantiles(list(values), n=100, method="inclusive")[94]
    return round(float(pct), 1)


def get_inference_snapshot() -> dict[str, float | int]:
    """Return rolling average and sample count for chat completions."""
    with _lock:
        chat_values = list(_chat_ms or [])
        first_values = list(_first_token_ms or [])

        chat_sample_count = len(chat_values)
        chat_avg_ms = _mean(chat_values)
        chat_p50_ms = _p50(chat_values)
        chat_p95_ms = _p95(chat_values)

        first_token_sample_count = len(first_values)
        first_token_avg_ms = _mean(first_values)
        first_token_p50_ms = _p50(first_values)
        first_token_p95_ms = _p95(first_values)

        model_buckets: dict[str, dict[str, float | int]] = {}
        all_models = set((_chat_ms_by_model or {}).keys()) | set((_first_token_ms_by_model or {}).keys())
        for model in sorted(all_models):
            chat_model = list((_chat_ms_by_model or {}).get(model, []))
            first_model = list((_first_token_ms_by_model or {}).get(model, []))
            model_buckets[model] = {
                "chat_avg_ms": _mean(chat_model),
                "chat_p50_ms": _p50(chat_model),
                "chat_p95_ms": _p95(chat_model),
                "chat_sample_count": len(chat_model),
                "first_token_avg_ms": _mean(first_model),
                "first_token_p50_ms": _p50(first_model),
                "first_token_p95_ms": _p95(first_model),
                "first_token_sample_count": len(first_model),
            }

        return {
            "chat_avg_ms": chat_avg_ms,
            "chat_sample_count": chat_sample_count,
            "chat_p50_ms": chat_p50_ms,
            "chat_p95_ms": chat_p95_ms,
            "first_token_avg_ms": first_token_avg_ms,
            "first_token_sample_count": first_token_sample_count,
            "first_token_p50_ms": first_token_p50_ms,
            "first_token_p95_ms": first_token_p95_ms,
            "model_buckets": model_buckets,
        }
