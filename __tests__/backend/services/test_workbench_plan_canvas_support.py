from __future__ import annotations

from backend.services.knowledge_service import KnowledgeChatContext
from backend.services.workbench_plan_canvas_support import execute_canvas_task
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputCreatePayload,
)


class _FakeLLM:
    def list_model_names(self) -> list[str]:
        return ["gemma4:26b"]

    def generate_completion(self, model: str, prompt: str, **_: object) -> str:
        _ = model, prompt
        return "# Draft Title\n\nBody"


class _FakeRepository:
    def __init__(self) -> None:
        self.created_output: WorkbenchWorkspaceOutputCreatePayload | None = None
        self.completed_result_text: str | None = None

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> None:
        self.created_output = payload

    def mark_task_completed(
        self,
        task_id: str,
        *,
        updated_at: str,
        result_text: str,
        workspace_output_count: int,
    ) -> None:
        _ = task_id, updated_at, workspace_output_count
        self.completed_result_text = result_text

    def mark_task_failed(
        self,
        task_id: str,
        *,
        updated_at: str,
        error_detail: str,
    ) -> None:
        raise AssertionError(
            f"unexpected failure: {task_id} {updated_at} {error_detail}"
        )


def _task() -> WorkbenchTaskRecord:
    return WorkbenchTaskRecord(
        id="wb-canvas-1",
        task_kind="canvas",
        status="running",
        prompt="Draft the proposal",
        session_id="session-1",
        project_id="project-1",
        knowledge_document_ids=[],
        connector_ids=[],
        source_ids=[],
        created_at="2026-04-13T00:00:00Z",
        updated_at="2026-04-13T00:00:00Z",
        owner_id="owner-1",
        tenant_id="tenant-1",
        principal_id="principal-1",
    )


def test_execute_canvas_task_creates_workspace_output_from_extracted_module() -> None:
    repository = _FakeRepository()

    execute_canvas_task(
        task=_task(),
        repository=repository,
        llm=_FakeLLM(),
        settings=object(),
        auth_context=object(),
        request_id="req-1",
        now_iso=lambda: "2026-04-13T00:00:01Z",
        context_builder=lambda **_: KnowledgeChatContext(
            context_block="", citations=[]
        ),
        empty_result_error="Canvas generation returned an empty result.",
    )

    assert repository.created_output is not None
    assert repository.created_output.title == "Draft Title"
    assert repository.completed_result_text == "# Draft Title\n\nBody"
