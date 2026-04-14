"""Runtime-metadata backend selection and repository factories for Phase 16D."""

from __future__ import annotations

from goat_ai.shared.clocks import Clock

from backend.types import Settings


class UnsupportedRuntimeMetadataBackend(RuntimeError):
    """Raised when the configured runtime-metadata backend cannot be served."""


def _raise_unsupported_backend(settings: Settings) -> None:
    backend = settings.runtime_metadata_backend
    raise UnsupportedRuntimeMetadataBackend(
        f"Unsupported runtime metadata backend: {backend!r}"
    )


def ensure_supported_runtime_metadata_backend(settings: Settings) -> None:
    """Fail fast when runtime metadata is configured for an unsupported backend."""
    if settings.runtime_metadata_backend in {"sqlite", "postgres"}:
        return
    _raise_unsupported_backend(settings)


def initialize_runtime_metadata_store(settings: Settings) -> None:
    """Initialize the active runtime-metadata store for application startup."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services import db_migrations

        db_migrations.apply_migrations(settings.log_db_path)
        return
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.postgres_runtime_support import (
            run_postgres_runtime_migrations,
        )

        run_postgres_runtime_migrations(settings.runtime_postgres_dsn)
        return
    _raise_unsupported_backend(settings)


def build_conversation_logger(settings: Settings):
    """Return the active conversation logger implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.chat_runtime import SQLiteConversationLogger

        return SQLiteConversationLogger(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.chat_runtime import PostgresConversationLogger

        return PostgresConversationLogger(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_session_repository(settings: Settings):
    """Return the active chat-session repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.chat_runtime import SQLiteSessionRepository

        return SQLiteSessionRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.chat_runtime import PostgresSessionRepository

        return PostgresSessionRepository(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_workbench_task_repository(settings: Settings):
    """Return the active workbench-task repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.workbench_runtime import SQLiteWorkbenchTaskRepository

        return SQLiteWorkbenchTaskRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.workbench_runtime import PostgresWorkbenchTaskRepository

        return PostgresWorkbenchTaskRepository(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_code_sandbox_execution_repository(settings: Settings):
    """Return the active sandbox-execution repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.code_sandbox_runtime import (
            SQLiteCodeSandboxExecutionRepository,
        )

        return SQLiteCodeSandboxExecutionRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.code_sandbox_runtime import (
            PostgresCodeSandboxExecutionRepository,
        )

        return PostgresCodeSandboxExecutionRepository(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_knowledge_repository(settings: Settings):
    """Return the active knowledge metadata repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.knowledge_repository import SQLiteKnowledgeRepository

        return SQLiteKnowledgeRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.knowledge_repository import PostgresKnowledgeRepository

        return PostgresKnowledgeRepository(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_media_repository(settings: Settings):
    """Return the active media metadata repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.media_service import SQLiteMediaRepository

        return SQLiteMediaRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.media_service import PostgresMediaRepository

        return PostgresMediaRepository(settings.runtime_postgres_dsn)
    _raise_unsupported_backend(settings)


def build_account_repository(settings: Settings):
    """Return the active account metadata repository implementation."""
    if settings.runtime_metadata_backend == "sqlite":
        from backend.services.account_repository import SQLiteAccountRepository

        return SQLiteAccountRepository(settings.log_db_path)
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.account_repository import PostgresAccountRepository

        return PostgresAccountRepository(settings.runtime_postgres_dsn)
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
    if settings.runtime_metadata_backend == "postgres":
        from backend.services.idempotency_service import PostgresIdempotencyStore

        return PostgresIdempotencyStore(
            dsn=settings.runtime_postgres_dsn,
            ttl_sec=settings.idempotency_ttl_sec,
            clock=clock,
        )
    _raise_unsupported_backend(settings)


def runtime_storage_model_label(settings: Settings) -> str:
    """Describe the configured runtime-metadata posture for telemetry."""
    if settings.runtime_metadata_backend == "sqlite":
        return "sqlite-first"
    if settings.runtime_metadata_backend == "postgres":
        return "postgres-hosted"
    return str(settings.runtime_metadata_backend)
