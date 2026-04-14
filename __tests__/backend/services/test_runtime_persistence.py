from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.account_repository import (
    PostgresAccountRepository,
    SQLiteAccountRepository,
)
from backend.services.chat_runtime import (
    PostgresConversationLogger,
    PostgresSessionRepository,
    SQLiteConversationLogger,
    SQLiteSessionRepository,
)
from backend.services.code_sandbox_runtime import (
    PostgresCodeSandboxExecutionRepository,
    SQLiteCodeSandboxExecutionRepository,
)
from backend.services.idempotency_service import (
    PostgresIdempotencyStore,
    SQLiteIdempotencyStore,
)
from backend.services.knowledge_repository import (
    PostgresKnowledgeRepository,
    SQLiteKnowledgeRepository,
)
from backend.services.media_service import (
    PostgresMediaRepository,
    SQLiteMediaRepository,
)
from backend.services.runtime_persistence import (
    build_account_repository,
    build_code_sandbox_execution_repository,
    build_conversation_logger,
    build_idempotency_store,
    build_knowledge_repository,
    build_media_repository,
    build_session_repository,
    build_workbench_task_repository,
    ensure_supported_runtime_metadata_backend,
    initialize_runtime_metadata_store,
    runtime_storage_model_label,
)
from backend.services.workbench_runtime import (
    PostgresWorkbenchTaskRepository,
    SQLiteWorkbenchTaskRepository,
)
from goat_ai.config.settings import Settings


def _settings(*, backend: str = "sqlite") -> Settings:
    root = Path(tempfile.gettempdir()) / "goat-ai-runtime-persistence-tests"
    kwargs: dict[str, object] = {
        "ollama_base_url": "http://127.0.0.1:11434",
        "generate_timeout": 120,
        "max_upload_mb": 20,
        "max_upload_bytes": 20 * 1024 * 1024,
        "max_dataframe_rows": 50000,
        "use_chat_api": True,
        "system_prompt": "test",
        "app_root": root,
        "logo_svg": root / "logo.svg",
        "log_db_path": root / "chat_logs.db",
        "runtime_metadata_backend": backend,
    }
    if backend == "postgres":
        kwargs["runtime_postgres_dsn"] = (
            "postgresql://goat:secret@db.example.com:5432/goat"
        )
        kwargs["deploy_target"] = "server"
    return Settings(**kwargs)


class RuntimePersistenceFactoryTests(unittest.TestCase):
    def test_sqlite_backend_builders_return_sqlite_implementations(self) -> None:
        settings = _settings()

        self.assertIsInstance(
            build_conversation_logger(settings), SQLiteConversationLogger
        )
        self.assertIsInstance(
            build_session_repository(settings), SQLiteSessionRepository
        )
        self.assertIsInstance(
            build_workbench_task_repository(settings),
            SQLiteWorkbenchTaskRepository,
        )
        self.assertIsInstance(
            build_code_sandbox_execution_repository(settings),
            SQLiteCodeSandboxExecutionRepository,
        )
        self.assertIsInstance(
            build_knowledge_repository(settings), SQLiteKnowledgeRepository
        )
        self.assertIsInstance(build_media_repository(settings), SQLiteMediaRepository)
        self.assertIsInstance(
            build_account_repository(settings), SQLiteAccountRepository
        )
        self.assertIsInstance(build_idempotency_store(settings), SQLiteIdempotencyStore)
        self.assertEqual("sqlite-first", runtime_storage_model_label(settings))

    def test_postgres_backend_builders_return_postgres_implementations(self) -> None:
        settings = _settings(backend="postgres")

        ensure_supported_runtime_metadata_backend(settings)
        self.assertIsInstance(
            build_conversation_logger(settings), PostgresConversationLogger
        )
        self.assertIsInstance(
            build_session_repository(settings), PostgresSessionRepository
        )
        self.assertIsInstance(
            build_workbench_task_repository(settings), PostgresWorkbenchTaskRepository
        )
        self.assertIsInstance(
            build_code_sandbox_execution_repository(settings),
            PostgresCodeSandboxExecutionRepository,
        )
        self.assertIsInstance(
            build_knowledge_repository(settings), PostgresKnowledgeRepository
        )
        self.assertIsInstance(build_media_repository(settings), PostgresMediaRepository)
        self.assertIsInstance(
            build_account_repository(settings), PostgresAccountRepository
        )
        self.assertIsInstance(
            build_idempotency_store(settings), PostgresIdempotencyStore
        )
        self.assertEqual("postgres-hosted", runtime_storage_model_label(settings))

    def test_initialize_postgres_backend_runs_migrations(self) -> None:
        settings = _settings(backend="postgres")

        with patch(
            "backend.services.postgres_runtime_support.run_postgres_runtime_migrations"
        ) as run_postgres_runtime_migrations:
            initialize_runtime_metadata_store(settings)

        run_postgres_runtime_migrations.assert_called_once_with(
            settings.runtime_postgres_dsn
        )


if __name__ == "__main__":
    unittest.main()
