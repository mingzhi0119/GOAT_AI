"""Unit tests for goat_ai.latency_metrics."""
from __future__ import annotations

from goat_ai.latency_metrics import get_inference_snapshot, init_latency_metrics, record_chat_inference_ms


def test_snapshot_empty_before_records() -> None:
    init_latency_metrics(5)
    snap = get_inference_snapshot()
    assert snap["chat_sample_count"] == 0
    assert snap["chat_avg_ms"] == 0.0


def test_rolling_average_respects_maxlen() -> None:
    init_latency_metrics(3)
    record_chat_inference_ms(100.0)
    record_chat_inference_ms(200.0)
    record_chat_inference_ms(300.0)
    record_chat_inference_ms(400.0)
    snap = get_inference_snapshot()
    assert snap["chat_sample_count"] == 3
    assert snap["chat_avg_ms"] == 300.0
