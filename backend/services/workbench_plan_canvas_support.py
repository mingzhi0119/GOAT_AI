"""Helpers and executors for plan and canvas workbench tasks."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from backend.domain.authz_types import AuthorizationContext
from backend.services.knowledge_service import KnowledgeChatContext
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
    WorkbenchWorkspaceOutputCreatePayload,
)
from backend.types import LLMClient, Settings


_DEFAULT_PLAN_MODEL = "gemma4:26b"


def resolve_plan_model(llm: LLMClient) -> str:
    names = llm.list_model_names()
    return names[0] if names else _DEFAULT_PLAN_MODEL


def compose_plan_prompt(
    *,
    task: WorkbenchTaskRecord,
    context_block: str,
    has_context: bool,
) -> str:
    parts = [
        "You are generating a concise, actionable markdown plan for a long-running workbench task.",
        "Return markdown only. Use short sections with bullet points where helpful.",
        "Include these sections in order: Goal, Key Questions, Proposed Steps, Risks, Deliverables.",
        f"Task kind: {task.task_kind}",
        f"User request:\n{task.prompt}",
    ]
    if task.project_id:
        parts.append(f"Project scope: {task.project_id}")
    if task.session_id:
        parts.append(f"Session affinity: {task.session_id}")
    if task.source_ids:
        parts.append(
            "Requested retrieval sources (not fully executed in this phase): "
            + ", ".join(task.source_ids)
        )
    if task.knowledge_document_ids:
        parts.append(
            "Attached knowledge documents: " + ", ".join(task.knowledge_document_ids)
        )
    if has_context:
        parts.append(
            "Use the retrieved context below as the primary evidence for the plan.\n\n"
            f"{context_block}"
        )
    elif task.knowledge_document_ids:
        parts.append(
            "No relevant retrieved context was found in the attached knowledge documents. "
            "Acknowledge that constraint in the plan."
        )
    return "\n\n".join(parts)


def compose_canvas_prompt(
    *,
    task: WorkbenchTaskRecord,
    context_block: str,
    has_context: bool,
) -> str:
    parts = [
        "You are drafting an initial editable canvas document for a long-running workbench task.",
        "Return markdown only.",
        "Start with a level-1 heading title.",
        "Then include these sections in order: Objective, Working Draft, Open Questions, Next Steps.",
        "Keep the document concise but useful as a starting point for later editing.",
        f"User request:\n{task.prompt}",
    ]
    if task.project_id:
        parts.append(f"Project scope: {task.project_id}")
    if task.session_id:
        parts.append(f"Session affinity: {task.session_id}")
    if has_context:
        parts.append(
            "Use the retrieved context below as the primary evidence for the document.\n\n"
            f"{context_block}"
        )
    elif task.knowledge_document_ids:
        parts.append(
            "No relevant retrieved context was found in the attached knowledge documents. "
            "Acknowledge that constraint in the document."
        )
    return "\n\n".join(parts)


def build_plan_or_canvas_context(
    *,
    task: WorkbenchTaskRecord,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    context_builder: Callable[..., KnowledgeChatContext],
) -> tuple[str, bool]:
    if not task.knowledge_document_ids:
        return "", False
    context = context_builder(
        query=task.prompt,
        document_ids=task.knowledge_document_ids,
        top_k=5,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    return context.context_block, bool(context.citations)


def derive_canvas_title(*, task: WorkbenchTaskRecord, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title[:120]
    prompt = task.prompt.strip()
    if prompt:
        return prompt[:120]
    return "Untitled canvas"


def execute_canvas_task(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    now_iso: Callable[[], str],
    context_builder: Callable[..., KnowledgeChatContext],
    empty_result_error: str,
) -> None:
    context_block, has_context = build_plan_or_canvas_context(
        task=task,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
        context_builder=context_builder,
    )
    prompt = compose_canvas_prompt(
        task=task,
        context_block=context_block,
        has_context=has_context,
    )
    content = llm.generate_completion(resolve_plan_model(llm), prompt).strip()
    if not content:
        repository.mark_task_failed(
            task.id,
            updated_at=now_iso(),
            error_detail=empty_result_error,
        )
        return
    now = now_iso()
    repository.create_workspace_output(
        WorkbenchWorkspaceOutputCreatePayload(
            output_id=f"wbo-{uuid4().hex}",
            task_id=task.id,
            output_kind="canvas_document",
            title=derive_canvas_title(task=task, content=content),
            content_format="markdown",
            content_text=content,
            created_at=now,
            updated_at=now,
            metadata={
                "task_kind": task.task_kind,
                "session_id": task.session_id,
                "project_id": task.project_id,
                "editable": True,
            },
            owner_id=task.owner_id,
            tenant_id=task.tenant_id,
            principal_id=task.principal_id,
        )
    )
    repository.mark_task_completed(
        task.id,
        updated_at=now_iso(),
        result_text=content,
        workspace_output_count=1,
    )
