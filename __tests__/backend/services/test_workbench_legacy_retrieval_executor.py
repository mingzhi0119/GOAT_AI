from __future__ import annotations

from backend.models.knowledge import KnowledgeCitation, KnowledgeSearchResponse
from backend.services.workbench_legacy_retrieval_executor import (
    execute_legacy_retrieval_task,
)
from backend.services.workbench_runtime import WorkbenchTaskRecord
from backend.services.workbench_source_registry import WorkbenchSourceDescriptor


class _FakeRepository:
    def __init__(self) -> None:
        self.completed_result_text: str | None = None
        self.completed_citations: list[dict[str, object]] | None = None
        self.failed_error_detail: str | None = None

    def mark_task_completed(
        self,
        task_id: str,
        *,
        updated_at: str,
        result_text: str,
        result_citations: list[dict[str, object]],
        workspace_output_count: int,
    ) -> None:
        _ = task_id, updated_at, workspace_output_count
        self.completed_result_text = result_text
        self.completed_citations = result_citations

    def mark_task_failed(
        self,
        task_id: str,
        *,
        updated_at: str,
        error_detail: str,
    ) -> None:
        _ = task_id, updated_at
        self.failed_error_detail = error_detail


def _task() -> WorkbenchTaskRecord:
    return WorkbenchTaskRecord(
        id="wb-browse-1",
        task_kind="browse",
        status="running",
        prompt="Investigate the docs",
        session_id=None,
        project_id=None,
        knowledge_document_ids=["doc-1"],
        connector_ids=[],
        source_ids=["knowledge"],
        created_at="2026-04-13T00:00:00Z",
        updated_at="2026-04-13T00:00:00Z",
        owner_id="owner-1",
        tenant_id="tenant-1",
        principal_id="principal-1",
    )


def test_execute_legacy_retrieval_task_completes_from_extracted_module() -> None:
    repository = _FakeRepository()
    seen_events: list[str] = []

    execute_legacy_retrieval_task(
        task=_task(),
        repository=repository,
        settings=object(),
        auth_context=object(),
        request_id="req-1",
        now_iso=lambda: "2026-04-13T00:00:01Z",
        append_task_event=lambda **kwargs: seen_events.append(
            str(kwargs["event_type"])
        ),
        source_resolver=lambda **_: [
            WorkbenchSourceDescriptor(
                source_id="knowledge",
                display_name="Knowledge Base",
                kind="knowledge",
                scope_kind="knowledge_documents",
                capabilities=("search",),
                task_kinds=("browse", "deep_research"),
                read_only=True,
                runtime_ready=True,
                deny_reason=None,
                description="knowledge",
            )
        ],
        knowledge_search=lambda **_: KnowledgeSearchResponse(
            query="Investigate the docs",
            hits=[
                KnowledgeCitation(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    filename="notes.md",
                    snippet="alpha",
                    score=0.9,
                )
            ],
        ),
        web_search=lambda **_: [],
        no_runnable_sources_error="No runnable retrieval sources are currently available.",
        execution_failed_error="Retrieval execution failed.",
    )

    assert repository.failed_error_detail is None
    assert repository.completed_result_text is not None
    assert "Browse Summary" in repository.completed_result_text
    assert repository.completed_citations is not None
    assert len(repository.completed_citations) == 1
    assert seen_events == ["retrieval.sources_resolved", "retrieval.step.completed"]
