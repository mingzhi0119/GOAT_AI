"""Domain exceptions raised by application services (mapped to HTTP in ``main``)."""

from __future__ import annotations

from typing import Literal


class InferenceBackendUnavailable(Exception):
    """Raised when the configured LLM inference endpoint (e.g. Ollama) is unreachable."""


class KnowledgeFeatureNotImplemented(Exception):
    """Raised for contract-first knowledge endpoints that are defined before implementation lands."""

    def __init__(self) -> None:
        super().__init__(
            "Knowledge API contract is defined, but the RAG implementation has not landed yet."
        )


class KnowledgeDocumentNotFound(Exception):
    """Raised when a requested knowledge document or ingestion record does not exist."""


class KnowledgeValidationError(Exception):
    """Raised when a knowledge request fails domain validation."""


class MediaNotFound(Exception):
    """Raised when a requested image attachment id does not exist on disk."""


class MediaValidationError(Exception):
    """Raised when an uploaded image fails format, size, or normalization checks."""


class ArtifactNotFound(Exception):
    """Raised when a requested generated chat artifact does not exist."""


class SessionNotFoundError(LookupError):
    """Raised when a targeted persisted session row does not exist."""


class PersistenceReadError(RuntimeError):
    """Raised when persisted session state cannot be read reliably."""


class PersistenceWriteError(RuntimeError):
    """Raised when a persisted session write cannot be completed reliably."""


class VisionNotSupported(Exception):
    """Raised when the selected model lacks Ollama-reported vision capability."""

    def __init__(
        self, message: str = "Selected model does not support vision."
    ) -> None:
        super().__init__(message)


class FeatureNotAvailable(Exception):
    """Raised when a feature gate denies access (§15).

    ``gate_kind`` distinguishes **policy** (AuthZ / caller not allowed → 403) from
    **runtime** (deployment or dependency not ready → 503).
    """

    def __init__(
        self,
        *,
        feature_id: str,
        deny_reason: str,
        gate_kind: Literal["policy", "runtime"] = "runtime",
    ) -> None:
        self.feature_id = feature_id
        self.deny_reason = deny_reason
        self.gate_kind = gate_kind
        super().__init__(f"Feature {feature_id} denied ({gate_kind}, {deny_reason}).")
