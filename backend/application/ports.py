"""Application-layer contract face for routers and use-case wiring."""

from __future__ import annotations

from backend.services.chat_capacity_service import (
    ChatCapacityError,
    validate_chat_capacity,
)
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)  # noqa: F401
from backend.services.exceptions import (  # noqa: F401
    PersistenceReadError,
    PersistenceWriteError,
    FeatureNotAvailable,
    InferenceBackendUnavailable,
    ArtifactNotFound,
    KnowledgeDocumentNotFound,
    KnowledgeValidationError,
    MediaNotFound,
    MediaValidationError,
    SessionNotFoundError,
    VisionNotSupported,
)
from backend.services.safeguard_service import SafeguardService  # noqa: F401
from backend.services.tabular_context import TabularContextExtractor  # noqa: F401
from backend.types import LLMClient, OllamaUnavailable, Settings  # noqa: F401

__all__ = [
    "ChatCapacityError",
    "ConversationLogger",
    "ArtifactNotFound",
    "FeatureNotAvailable",
    "InferenceBackendUnavailable",
    "KnowledgeDocumentNotFound",
    "KnowledgeValidationError",
    "LLMClient",
    "MediaNotFound",
    "MediaValidationError",
    "PersistenceReadError",
    "PersistenceWriteError",
    "SafeguardService",
    "SessionNotFoundError",
    "SessionRepository",
    "Settings",
    "TabularContextExtractor",
    "TitleGenerator",
    "validate_chat_capacity",
    "VisionNotSupported",
]
