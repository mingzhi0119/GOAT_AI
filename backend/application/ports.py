"""Application-layer contract face for routers and use-case wiring."""
from __future__ import annotations

from backend.services.chat_capacity_service import ChatCapacityError, validate_chat_capacity  # noqa: F401
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator  # noqa: F401
from backend.services.exceptions import (  # noqa: F401
    FeatureNotAvailable,
    InferenceBackendUnavailable,
    KnowledgeDocumentNotFound,
    KnowledgeValidationError,
    MediaNotFound,
    MediaValidationError,
    VisionNotSupported,
)
from backend.services.safeguard_service import SafeguardService  # noqa: F401
from backend.services.tabular_context import TabularContextExtractor  # noqa: F401
from backend.types import LLMClient, OllamaUnavailable, Settings  # noqa: F401

__all__ = [
    "ChatCapacityError",
    "ConversationLogger",
    "FeatureNotAvailable",
    "InferenceBackendUnavailable",
    "KnowledgeDocumentNotFound",
    "KnowledgeValidationError",
    "LLMClient",
    "MediaNotFound",
    "MediaValidationError",
    "SafeguardService",
    "SessionRepository",
    "Settings",
    "TabularContextExtractor",
    "TitleGenerator",
    "VisionNotSupported",
]
