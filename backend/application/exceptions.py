"""Application-layer exceptions used to keep routers thin."""

from __future__ import annotations

from backend.application.ports import (  # noqa: F401
    ChatCapacityError,
    FeatureNotAvailable,
    InferenceBackendUnavailable,
    KnowledgeDocumentNotFound,
    KnowledgeValidationError,
    MediaNotFound,
    MediaValidationError,
    VisionNotSupported,
)


class HistoryOwnerRequiredError(ValueError):
    """Raised when a history endpoint requires an owner header and none was supplied."""


class HistorySessionNotFoundError(LookupError):
    """Raised when a history session cannot be found or is not visible to the caller."""


class HistoryValidationError(ValueError):
    """Raised when a history request violates application-level input rules."""


class UploadIdempotencyConflictError(ValueError):
    """Raised when an upload idempotency key is reused with a different payload."""


class UploadIdempotencyInProgressError(RuntimeError):
    """Raised when an upload idempotency key is already pending."""


class ChatOwnerRequiredError(ValueError):
    """Raised when chat/session scoping requires X-GOAT-Owner-Id and it is missing."""


class ChatKnowledgeImageConflictError(ValueError):
    """Raised when a chat request mixes retrieval documents and image attachments."""


class ChatIdempotencyConflictError(ValueError):
    """Raised when a chat idempotency key is reused with a different payload."""


class ChatIdempotencyInProgressError(RuntimeError):
    """Raised when a chat idempotency key is already pending."""


__all__ = [
    "ChatCapacityError",
    "ChatIdempotencyConflictError",
    "ChatIdempotencyInProgressError",
    "ChatKnowledgeImageConflictError",
    "ChatOwnerRequiredError",
    "FeatureNotAvailable",
    "HistoryOwnerRequiredError",
    "HistorySessionNotFoundError",
    "HistoryValidationError",
    "InferenceBackendUnavailable",
    "KnowledgeDocumentNotFound",
    "KnowledgeValidationError",
    "MediaNotFound",
    "MediaValidationError",
    "UploadIdempotencyConflictError",
    "UploadIdempotencyInProgressError",
    "VisionNotSupported",
]
