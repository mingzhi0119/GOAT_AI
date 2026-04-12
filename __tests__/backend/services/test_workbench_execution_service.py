from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.models.knowledge import KnowledgeCitation, KnowledgeSearchResponse
from backend.services import log_service
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.workbench_execution_service import (
    execute_workbench_task,
    recover_workbench_tasks,
)
from backend.services.workbench_web_search import (
    WorkbenchWebSearchError,
    WorkbenchWebSearchHit,
)
from backend.services.workbench_runtime import (
    SQLiteWorkbenchTaskRepository,
    WorkbenchTaskCreatePayload,
)
from backend.services.workbench_source_registry import WorkbenchSourceDescriptor
from goat_ai.config.settings import Settings


class _FakeLLM:
    def list_model_names(self) -> list[str]:
        return ["gemma4:26b"]

    def generate_completion(self, model: str, prompt: str, **_: object) -> str:
        _ = model
        return f"## Goal\n{prompt[:40]}"


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        data_dir=root / "data",
        feature_agent_workbench_enabled=True,
    )


class WorkbenchExecutionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmpdir.name)
        self.settings = _settings(self.root)
        log_service.init_db(self.settings.log_db_path)
        self.repository = SQLiteWorkbenchTaskRepository(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _create_task(
        self,
        *,
        task_id: str,
        task_kind: str,
        source_ids: list[str] | None = None,
        knowledge_document_ids: list[str] | None = None,
    ) -> None:
        self.repository.create_task(
            WorkbenchTaskCreatePayload(
                task_id=task_id,
                task_kind=task_kind,
                prompt="Investigate the docs",
                session_id=None,
                project_id=None,
                knowledge_document_ids=list(knowledge_document_ids or []),
                connector_ids=[],
                source_ids=list(source_ids or []),
                created_at="2026-04-11T00:00:00+00:00",
                updated_at="2026-04-11T00:00:00+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
                auth_scopes=["workbench:read", "knowledge:read"],
                credential_id="cred-1",
                auth_mode="api_key",
            )
        )

    def test_browse_task_completes_with_deduped_citations(self) -> None:
        self._create_task(
            task_id="wb-browse", task_kind="browse", source_ids=["knowledge"]
        )
        knowledge_source = WorkbenchSourceDescriptor(
            source_id="knowledge",
            display_name="Knowledge Base",
            kind="knowledge",
            scope_kind="knowledge_documents",
            capabilities=("search", "fetch", "citations"),
            task_kinds=("plan", "browse", "deep_research"),
            read_only=True,
            runtime_ready=True,
            deny_reason=None,
            description="Knowledge source",
            required_scope="knowledge:read",
        )

        with (
            patch(
                "backend.services.workbench_execution_service.resolve_requested_sources",
                return_value=[knowledge_source],
            ),
            patch(
                "backend.services.workbench_execution_service.search_knowledge",
                return_value=KnowledgeSearchResponse(
                    query="Investigate the docs",
                    hits=[
                        KnowledgeCitation(
                            document_id="doc-1",
                            chunk_id="chunk-1",
                            filename="notes.md",
                            snippet="alpha",
                            score=0.9,
                        ),
                        KnowledgeCitation(
                            document_id="doc-1",
                            chunk_id="chunk-1",
                            filename="notes.md",
                            snippet="alpha",
                            score=0.8,
                        ),
                    ],
                ),
            ),
        ):
            execute_workbench_task(
                task_id="wb-browse",
                repository=self.repository,
                llm=_FakeLLM(),
                settings=self.settings,
            )

        stored = self.repository.get_task("wb-browse")
        assert stored is not None
        self.assertEqual("completed", stored.status)
        self.assertEqual(1, len(stored.result_citations or []))
        events = self.repository.list_task_events("wb-browse")
        self.assertIn(
            "retrieval.sources_resolved", [event.event_type for event in events]
        )
        self.assertIn(
            "retrieval.step.completed", [event.event_type for event in events]
        )

    def test_retrieval_task_fails_when_no_runnable_sources_exist(self) -> None:
        self._create_task(task_id="wb-empty", task_kind="browse", source_ids=["web"])
        web_source = WorkbenchSourceDescriptor(
            source_id="web",
            display_name="Public Web",
            kind="builtin",
            scope_kind="global",
            capabilities=("search",),
            task_kinds=("browse",),
            read_only=True,
            runtime_ready=False,
            deny_reason="not_implemented",
            description="Web source",
        )

        with patch(
            "backend.services.workbench_execution_service.resolve_requested_sources",
            return_value=[web_source],
        ):
            execute_workbench_task(
                task_id="wb-empty",
                repository=self.repository,
                llm=_FakeLLM(),
                settings=self.settings,
            )

        stored = self.repository.get_task("wb-empty")
        assert stored is not None
        self.assertEqual("failed", stored.status)
        self.assertIn("No runnable retrieval sources", stored.error_detail or "")

    def test_browse_task_completes_with_web_citations(self) -> None:
        self._create_task(task_id="wb-web", task_kind="browse", source_ids=["web"])
        web_source = WorkbenchSourceDescriptor(
            source_id="web",
            display_name="Public Web",
            kind="builtin",
            scope_kind="global",
            capabilities=("search", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=True,
            deny_reason=None,
            description="Web source",
        )

        with (
            patch(
                "backend.services.workbench_execution_service.resolve_requested_sources",
                return_value=[web_source],
            ),
            patch(
                "backend.services.workbench_execution_service.search_public_web",
                return_value=[
                    WorkbenchWebSearchHit(
                        title="Example result",
                        url="https://example.com/report",
                        snippet="Web evidence snippet",
                        rank=1,
                    )
                ],
            ),
        ):
            execute_workbench_task(
                task_id="wb-web",
                repository=self.repository,
                llm=_FakeLLM(),
                settings=self.settings,
            )

        stored = self.repository.get_task("wb-web")
        assert stored is not None
        self.assertEqual("completed", stored.status)
        self.assertEqual(
            "https://example.com/report", stored.result_citations[0]["document_id"]
        )
        self.assertIn(
            "[Example result](https://example.com/report)", stored.result_text or ""
        )
        events = self.repository.list_task_events("wb-web")
        self.assertEqual("web", events[3].metadata["source_id"])
        self.assertEqual("duckduckgo", events[3].metadata["provider"])

    def test_retrieval_task_fails_when_web_provider_errors_without_fallback(
        self,
    ) -> None:
        self._create_task(task_id="wb-web-fail", task_kind="browse", source_ids=["web"])
        web_source = WorkbenchSourceDescriptor(
            source_id="web",
            display_name="Public Web",
            kind="builtin",
            scope_kind="global",
            capabilities=("search", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=True,
            deny_reason=None,
            description="Web source",
        )

        with (
            patch(
                "backend.services.workbench_execution_service.resolve_requested_sources",
                return_value=[web_source],
            ),
            patch(
                "backend.services.workbench_execution_service.search_public_web",
                side_effect=WorkbenchWebSearchError("boom"),
            ),
        ):
            execute_workbench_task(
                task_id="wb-web-fail",
                repository=self.repository,
                llm=_FakeLLM(),
                settings=self.settings,
            )

        stored = self.repository.get_task("wb-web-fail")
        assert stored is not None
        self.assertEqual("failed", stored.status)
        self.assertEqual("Retrieval execution failed.", stored.error_detail)
        events = self.repository.list_task_events("wb-web-fail")
        self.assertEqual("provider_error", events[3].metadata["deny_reason"])
        self.assertEqual("task.failed", events[4].event_type)

    def test_plan_task_marks_knowledge_not_found_when_context_resolution_fails(
        self,
    ) -> None:
        self._create_task(
            task_id="wb-plan",
            task_kind="plan",
            knowledge_document_ids=["doc-missing"],
        )

        with patch(
            "backend.services.workbench_execution_service.build_chat_knowledge_context",
            side_effect=KnowledgeDocumentNotFound("missing"),
        ):
            execute_workbench_task(
                task_id="wb-plan",
                repository=self.repository,
                llm=_FakeLLM(),
                settings=self.settings,
            )

        stored = self.repository.get_task("wb-plan")
        assert stored is not None
        self.assertEqual("failed", stored.status)
        self.assertEqual("Knowledge document not found.", stored.error_detail)

    def test_canvas_task_completes_with_workspace_output(self) -> None:
        self._create_task(task_id="wb-canvas", task_kind="canvas")

        execute_workbench_task(
            task_id="wb-canvas",
            repository=self.repository,
            llm=_FakeLLM(),
            settings=self.settings,
        )

        stored = self.repository.get_task("wb-canvas")
        assert stored is not None
        self.assertEqual("completed", stored.status)
        self.assertTrue((stored.result_text or "").startswith("## Goal"))

        outputs = self.repository.list_workspace_outputs("wb-canvas")
        self.assertEqual(1, len(outputs))
        self.assertEqual("canvas_document", outputs[0].output_kind)
        self.assertEqual("markdown", outputs[0].content_format)
        self.assertEqual(stored.result_text, outputs[0].content_text)

        events = self.repository.list_task_events("wb-canvas")
        self.assertEqual(
            [
                "task.queued",
                "task.started",
                "workspace_output.created",
                "task.completed",
            ],
            [event.event_type for event in events],
        )
        self.assertEqual(1, events[-1].metadata["workspace_output_count"])

    def test_recover_workbench_tasks_replays_queued_and_fails_interrupted_running(
        self,
    ) -> None:
        self._create_task(task_id="wb-recover-queued", task_kind="plan")
        self._create_task(task_id="wb-recover-running", task_kind="plan")
        claimed = self.repository.claim_task_for_execution(
            "wb-recover-running",
            updated_at="2026-04-11T00:00:01+00:00",
        )
        assert claimed is not None

        recovered = recover_workbench_tasks(
            repository=self.repository,
            llm=_FakeLLM(),
            settings=self.settings,
        )

        self.assertEqual(["wb-recover-queued"], recovered.replayed_task_ids)
        self.assertEqual(["wb-recover-running"], recovered.interrupted_task_ids)

        queued = self.repository.get_task("wb-recover-queued")
        running = self.repository.get_task("wb-recover-running")
        assert queued is not None
        assert running is not None
        self.assertEqual("completed", queued.status)
        self.assertEqual("failed", running.status)
        self.assertEqual(
            "Task execution was interrupted during a previous process lifetime.",
            running.error_detail,
        )

    def test_recover_workbench_tasks_skips_cancelled_tasks(self) -> None:
        self._create_task(task_id="wb-recover-cancelled", task_kind="plan")
        self.repository.mark_task_cancelled(
            "wb-recover-cancelled",
            updated_at="2026-04-11T00:00:01+00:00",
            error_detail="Task cancelled before execution.",
        )

        recovered = recover_workbench_tasks(
            repository=self.repository,
            llm=_FakeLLM(),
            settings=self.settings,
        )

        self.assertEqual([], recovered.replayed_task_ids)
        self.assertEqual([], recovered.interrupted_task_ids)
        cancelled = self.repository.get_task("wb-recover-cancelled")
        assert cancelled is not None
        self.assertEqual("cancelled", cancelled.status)
