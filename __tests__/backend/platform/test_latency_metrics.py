"""Unit tests for goat_ai.latency_metrics."""

from __future__ import annotations

from goat_ai.latency_metrics import (
    get_inference_snapshot,
    init_latency_metrics,
    record_chat_first_token_ms,
    record_chat_inference_ms,
)


def test_snapshot_empty_before_records() -> None:
    init_latency_metrics(5)
    snap = get_inference_snapshot()
    assert snap["chat_sample_count"] == 0
    assert snap["chat_avg_ms"] == 0.0
    assert snap["chat_p50_ms"] == 0.0
    assert snap["chat_p95_ms"] == 0.0
    assert snap["first_token_sample_count"] == 0
    assert snap["first_token_avg_ms"] == 0.0
    assert snap["first_token_p50_ms"] == 0.0
    assert snap["first_token_p95_ms"] == 0.0
    assert snap["model_buckets"] == {}


def test_rolling_average_respects_maxlen() -> None:
    init_latency_metrics(3)
    record_chat_inference_ms(100.0)
    record_chat_inference_ms(200.0)
    record_chat_inference_ms(300.0)
    record_chat_inference_ms(400.0)
    record_chat_first_token_ms(10.0)
    record_chat_first_token_ms(20.0)
    record_chat_first_token_ms(30.0)
    record_chat_first_token_ms(40.0)
    snap = get_inference_snapshot()
    assert snap["chat_sample_count"] == 3
    assert snap["chat_avg_ms"] == 300.0
    assert snap["chat_p50_ms"] == 300.0
    assert snap["chat_p95_ms"] == 390.0
    assert snap["first_token_sample_count"] == 3
    assert snap["first_token_avg_ms"] == 30.0
    assert snap["first_token_p50_ms"] == 30.0
    assert snap["first_token_p95_ms"] == 39.0


def test_latency_snapshot_includes_model_buckets() -> None:
    init_latency_metrics(5)
    record_chat_inference_ms(100.0, model="m1")
    record_chat_inference_ms(200.0, model="m1")
    record_chat_first_token_ms(20.0, model="m1")
    record_chat_first_token_ms(40.0, model="m1")
    snap = get_inference_snapshot()
    buckets = snap["model_buckets"]
    assert isinstance(buckets, dict)
    assert "m1" in buckets
    m1 = buckets["m1"]
    assert m1["chat_sample_count"] == 2
    assert m1["chat_avg_ms"] == 150.0
    assert m1["first_token_sample_count"] == 2
    assert m1["first_token_avg_ms"] == 30.0
