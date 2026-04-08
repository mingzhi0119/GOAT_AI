"""In-process counters for shared-layer telemetry (Ollama transport failures).

Backend metrics exposition reads snapshots via ``snapshot_ollama_errors``.
"""
from __future__ import annotations

import threading
from collections import defaultdict

# Stable label value aligned with ``backend.api_errors.INFERENCE_BACKEND_UNAVAILABLE``.
OLLAMA_ERROR_API_CODE: str = "INFERENCE_BACKEND_UNAVAILABLE"

_lock = threading.Lock()
_counts: dict[tuple[str, str, str], int] = defaultdict(int)


def inc_ollama_error(*, code: str, endpoint: str, http_status: str = "none") -> None:
    """Increment Ollama transport/backend failure counter (thread-safe)."""
    key = (code, endpoint, http_status)
    with _lock:
        _counts[key] += 1


def snapshot_ollama_errors() -> dict[tuple[str, str, str], int]:
    """Return a shallow copy of Ollama error counts for metrics rendering."""
    with _lock:
        return dict(_counts)
