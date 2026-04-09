"""Pytest fixtures shared across backend unit tests."""

from __future__ import annotations

import pytest

from goat_ai.latency_metrics import init_latency_metrics


@pytest.fixture(autouse=True)
def _reset_latency_metrics_window() -> None:
    """Deterministic rolling window for tests that touch inference metrics."""
    init_latency_metrics(20)
    yield
