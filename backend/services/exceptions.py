"""Domain exceptions raised by application services (mapped to HTTP in ``main``)."""
from __future__ import annotations


class InferenceBackendUnavailable(Exception):
    """Raised when the configured LLM inference endpoint (e.g. Ollama) is unreachable."""
