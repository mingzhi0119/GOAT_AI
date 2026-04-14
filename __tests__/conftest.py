"""Pytest fixtures shared across backend unit tests."""

from __future__ import annotations

import pytest

from goat_ai.telemetry.latency_metrics import init_latency_metrics


@pytest.fixture(autouse=True)
def _reset_latency_metrics_window() -> None:
    """Deterministic rolling window for tests that touch inference metrics."""
    init_latency_metrics(20)
    yield


@pytest.fixture(autouse=True)
def _set_test_model_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep legacy fake-model names usable in tests while production stays stricter."""
    monkeypatch.setenv(
        "GOAT_PUBLIC_MODEL_ALLOWLIST",
        ",".join(
            (
                "qwen3:4b",
                "llama3.2:3b",
                "gemma3:4b",
                "qwen2.5-coder:3b",
                "gemma4:26b",
                "blackbox-model",
                "viz-model",
                "test-model",
                "vision-model",
                "text-only-model",
                "qwen3",
                "qwen3:latest",
            )
        ),
    )
    yield
