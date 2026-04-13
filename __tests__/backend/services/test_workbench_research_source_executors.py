from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.workbench_readonly_retrieval import (
    WorkbenchConnectorBindingNotFound,
)
from backend.services.workbench_research_source_executors import (
    WorkbenchResearchSourceExecutionContext,
    resolve_workbench_research_source_executor,
)
from backend.services.workbench_runtime import WorkbenchTaskRecord
from goat_ai.config.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test system prompt",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        data_dir=root / "data",
        ready_skip_ollama_probe=True,
    )


def _task(*, project_id: str | None = None) -> WorkbenchTaskRecord:
    return WorkbenchTaskRecord(
        id="task-1",
        task_kind="browse",
        status="running",
        prompt="Investigate the docs",
        session_id=None,
        project_id=project_id,
        knowledge_document_ids=[],
        connector_ids=[],
        source_ids=[],
        created_at="2026-04-13T00:00:00Z",
        updated_at="2026-04-13T00:00:00Z",
    )


class WorkbenchResearchSourceExecutorsTests(unittest.TestCase):
    def test_project_memory_executor_requires_project_scope(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            context = WorkbenchResearchSourceExecutionContext(
                task=_task(project_id=None),
                repository=object(),  # type: ignore[arg-type]
                settings=_settings(Path(tmp)),
                auth_context=object(),  # type: ignore[arg-type]
                request_id="req-1",
                query="roadmap",
                knowledge_search=lambda **_: None,
                web_search=lambda **_: [],
                project_memory_search=lambda **_: [],
                connector_search=lambda **_: [],
            )
            executor = resolve_workbench_research_source_executor("project_memory")

        assert executor is not None
        result = executor(context)
        self.assertEqual("project_memory", result.source_id)
        self.assertEqual("project_scope_missing", result.failure_reason)
        self.assertEqual([], result.citations)

    def test_connector_executor_reports_missing_binding(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            context = WorkbenchResearchSourceExecutionContext(
                task=_task(project_id="project-1"),
                repository=object(),  # type: ignore[arg-type]
                settings=_settings(Path(tmp)),
                auth_context=object(),  # type: ignore[arg-type]
                request_id="req-1",
                query="roadmap",
                knowledge_search=lambda **_: None,
                web_search=lambda **_: [],
                project_memory_search=lambda **_: [],
                connector_search=lambda **_: (_ for _ in ()).throw(
                    WorkbenchConnectorBindingNotFound("connector:ops")
                ),
            )
            executor = resolve_workbench_research_source_executor("connector:ops")

        assert executor is not None
        result = executor(context)
        self.assertEqual("connector:ops", result.source_id)
        self.assertEqual("binding_unavailable", result.failure_reason)
        self.assertEqual([], result.citations)


if __name__ == "__main__":
    unittest.main()
