"""Application-layer contract face for routers and use-case wiring."""

from __future__ import annotations

from typing import Protocol

from backend.services.chat_capacity_service import (
    ChatCapacityError,
    validate_chat_capacity,
)
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)  # noqa: F401
from backend.services.workbench_runtime import WorkbenchTaskRepository  # noqa: F401
from backend.services.code_sandbox_runtime import (  # noqa: F401
    CodeSandboxExecutionRepository,
)
from backend.services.code_sandbox_provider import SandboxProvider  # noqa: F401
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


class WorkbenchTaskDispatcher(Protocol):
    """Application-facing boundary for scheduling durable workbench execution."""

    def dispatch_task(self, *, task_id: str, request_id: str = "") -> None: ...


__all__ = [
    "ChatCapacityError",
    "ConversationLogger",
    "ArtifactNotFound",
    "CodeSandboxExecutionRepository",
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
    "SandboxProvider",
    "TabularContextExtractor",
    "TitleGenerator",
    "validate_chat_capacity",
    "VisionNotSupported",
    "WorkbenchTaskDispatcher",
    "WorkbenchTaskRepository",
]
