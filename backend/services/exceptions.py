"""Domain exceptions raised by application services (mapped to HTTP in ``main``)."""
from __future__ import annotations


class InferenceBackendUnavailable(Exception):
    """Raised when the configured LLM inference endpoint (e.g. Ollama) is unreachable."""


class KnowledgeFeatureNotImplemented(Exception):
    """Raised for contract-first knowledge endpoints that are defined before implementation lands."""

    def __init__(self) -> None:
        super().__init__("Knowledge API contract is defined, but the RAG implementation has not landed yet.")


class KnowledgeDocumentNotFound(Exception):
    """Raised when a requested knowledge document or ingestion record does not exist."""


class KnowledgeValidationError(Exception):
    """Raised when a knowledge request fails domain validation."""
