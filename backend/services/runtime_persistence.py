"""Runtime-metadata backend selection and repository factories for Phase 16D."""

from __future__ import annotations

from typing import NoReturn

from goat_ai.shared.clocks import Clock

from backend.types import Settings

_POSTGRES_NOT_IMPLEMENTED_MESSAGE = (
    "Phase 16D Postgres runtime persistence is not implemented yet. "
    "Keep GOAT_RUNTIME_METADATA_BACKEND=sqlite (default) until the Postgres "
    "repository adapters and migration tooling land."
)


class UnsupportedRuntimeMetadataBackend(RuntimeError):
    """Raised when the configured runtime-metadata backend cannot be served."""


def _raise_unsupported_backend(settings: Settings) -> NoReturn:
    backend = settings.runtime_metadata_backend
    if backend == "postgres":
        raise UnsupportedRuntimeMetadataBackend(_POSTGRES_NOT_IMPLEMENTED_MESSAGE)
    raise UnsupportedRuntimeMetadataBackend(
        f"Unsupported runtime metadata backend: {backend!r}"
    )


def ensure_supported_runtime_metadata_backend(settings: Settings) -> None:
    """Fail fast when runtime metadata is configured for an unsupported backend."""
    if settings.runtime_metadata_backend == "sqlite":
        return
    _raise_unsupported_backend(settings)


def initialize_runtime_metadata_store(settings: Settings) -> None:
    """Initialize the active runtime-metadata store for application startup."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services import log_service

        log_service.init_db(settings.log_db_path)
        return
    _raise_unsupported_backend(settings)


def build_conversation_logger(settings: Settings):
    """Return the active conversation logger implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.chat_runtime import SQLiteConversationLogger

        return SQLiteConversationLogger(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_session_repository(settings: Settings):
    """Return the active chat-session repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.chat_runtime import SQLiteSessionRepository

        return SQLiteSessionRepository(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_workbench_task_repository(settings: Settings):
    """Return the active workbench-task repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.workbench_runtime import SQLiteWorkbenchTaskRepository

        return SQLiteWorkbenchTaskRepository(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_code_sandbox_execution_repository(settings: Settings):
    """Return the active sandbox-execution repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.code_sandbox_runtime import (
            SQLiteCodeSandboxExecutionRepository,
        )

        return SQLiteCodeSandboxExecutionRepository(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_knowledge_repository(settings: Settings):
    """Return the active knowledge metadata repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.knowledge_repository import SQLiteKnowledgeRepository

        return SQLiteKnowledgeRepository(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_media_repository(settings: Settings):
    """Return the active media metadata repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.media_service import SQLiteMediaRepository

        return SQLiteMediaRepository(settings.log_db_path)
    _raise_unsupported_backend(settings)


def build_idempotency_store(settings: Settings, *, clock: Clock | None = None):
    """Return the active idempotency store implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.idempotency_service import SQLiteIdempotencyStore

        return SQLiteIdempotencyStore(
            db_path=settings.log_db_path,
            ttl_sec=settings.idempotency_ttl_sec,
            clock=clock,
        )
    _raise_unsupported_backend(settings)


def runtime_storage_model_label(settings: Settings) -> str:
    """Describe the configured runtime-metadata posture for telemetry."""
    if settings.runtime_metadata_backend == "sqlite":
        return "sqlite-first"
    return "postgres-server-preview"
