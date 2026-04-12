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


class WorkbenchTaskNotFoundError(LookupError):
    """Raised when a durable workbench task cannot be found or is not visible."""


class WorkbenchWorkspaceOutputNotFoundError(LookupError):
    """Raised when a durable workspace output cannot be found or is not visible."""


class WorkbenchSourceValidationError(ValueError):
    """Raised when a workbench task references unknown or unavailable sources."""


class WorkbenchPermissionDeniedError(PermissionError):
    """Raised when a caller lacks the scopes required for a workbench operation."""


class WorkbenchTaskConflictError(RuntimeError):
    """Raised when a workbench task transition is invalid for its current state."""


class CodeSandboxExecutionNotFoundError(LookupError):
    """Raised when a durable code sandbox execution cannot be found or is not visible."""


class CodeSandboxValidationError(ValueError):
    """Raised when a code sandbox request violates application-level validation."""


class CodeSandboxExecutionConflictError(RuntimeError):
    """Raised when a code sandbox execution transition is invalid for its state."""


__all__ = [
    "CodeSandboxExecutionNotFoundError",
    "CodeSandboxExecutionConflictError",
    "CodeSandboxValidationError",
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
    "WorkbenchSourceValidationError",
    "WorkbenchPermissionDeniedError",
    "WorkbenchTaskConflictError",
    "WorkbenchTaskNotFoundError",
    "WorkbenchWorkspaceOutputNotFoundError",
]
