"""In-process executor for minimal Phase 17B/17C workbench tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, Scope, TenantId
from backend.services.knowledge_service import (
    build_chat_knowledge_context,
    search_knowledge,
)
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.workbench_legacy_retrieval_executor import (
    execute_legacy_retrieval_task as _execute_retrieval_task,
)
from backend.services.workbench_plan_canvas_support import (
    build_plan_or_canvas_context as _build_plan_or_canvas_context,
    compose_plan_prompt as _compose_plan_prompt,
    execute_canvas_task as _execute_canvas_task,
    resolve_plan_model as _resolve_plan_model,
)
from backend.services.workbench_readonly_retrieval import (
    search_connector_binding,
    search_project_memory,
)
from backend.services.workbench_research_runtime import (
    WorkbenchResearchExecutionFailed,
    WorkbenchResearchNoRunnableSources,
    execute_langgraph_research_task,
    langgraph_runtime_available,
)
from backend.services.workbench_source_registry import resolve_requested_sources
from backend.services.workbench_web_search import (
    search_public_web,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
)
from backend.types import LLMClient, Settings
from goat_ai.shared.exceptions import OllamaUnavailable

logger = logging.getLogger(__name__)

_PLAN_NOT_IMPLEMENTED = "Task kind is not implemented yet."
_PLAN_EMPTY_RESULT = "Plan execution returned an empty result."
_PLAN_EXECUTION_FAILED = "Plan execution failed."
_PLAN_AI_UNAVAILABLE = "AI backend unavailable."
_PLAN_KNOWLEDGE_NOT_FOUND = "Knowledge document not found."
_PLAN_KNOWLEDGE_FAILED = "Knowledge retrieval failed."
_TASK_NOT_IMPLEMENTED = "Task kind is not implemented yet."
_CANVAS_EMPTY_RESULT = "Canvas generation returned an empty result."
_CANVAS_EXECUTION_FAILED = "Canvas generation failed."
_RETRIEVAL_NO_RUNNABLE_SOURCES = (
    "No runnable retrieval sources are currently available."
)
_RETRIEVAL_EXECUTION_FAILED = "Retrieval execution failed."
_TASK_INTERRUPTED = "Task execution was interrupted during a previous process lifetime."


@dataclass(frozen=True)
class WorkbenchRecoveryResult:
    replayed_task_ids: list[str]
    interrupted_task_ids: list[str]


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _append_task_event(
    *,
    repository: WorkbenchTaskRepository,
    task_id: str,
    event_type: str,
    status: str | None,
    message: str,
    metadata: dict[str, object] | None = None,
) -> None:
    repository.append_task_event(
        task_id,
        event_type=event_type,
        created_at=_now_iso(),
        status=status,
        message=message,
        metadata=metadata,
    )


def _build_execution_auth_context(task: WorkbenchTaskRecord) -> AuthorizationContext:
    scopes = cast(frozenset[Scope], frozenset(task.auth_scopes or []))
    return AuthorizationContext(
        principal_id=PrincipalId(task.principal_id),
        tenant_id=TenantId(task.tenant_id),
        scopes=scopes,
        credential_id=task.credential_id,
        legacy_owner_id=task.owner_id,
        auth_mode=task.auth_mode or "api_key",
    )


def execute_workbench_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
    request_id: str = "",
) -> None:
    """Execute one queued workbench task in-process."""
    claimed = repository.claim_task_for_execution(task_id, updated_at=_now_iso())
    if claimed is None:
        return
    auth_context = _build_execution_auth_context(claimed)

    try:
        if claimed.task_kind in {"browse", "deep_research"}:
            if settings.workbench_langgraph_enabled and langgraph_runtime_available():
                try:
                    research_result = execute_langgraph_research_task(
                        task=claimed,
                        repository=repository,
                        llm=llm,
                        settings=settings,
                        auth_context=auth_context,
                        request_id=request_id,
                        source_resolver=resolve_requested_sources,
                        knowledge_search=search_knowledge,
                        web_search=search_public_web,
                        project_memory_search=search_project_memory,
                        connector_search=search_connector_binding,
                    )
                except WorkbenchResearchNoRunnableSources:
                    repository.mark_task_failed(
                        task_id,
                        updated_at=_now_iso(),
                        error_detail=_RETRIEVAL_NO_RUNNABLE_SOURCES,
                    )
                    return
                except WorkbenchResearchExecutionFailed:
                    repository.mark_task_failed(
                        task_id,
                        updated_at=_now_iso(),
                        error_detail=_RETRIEVAL_EXECUTION_FAILED,
                    )
                    return
                repository.mark_task_completed(
                    task_id,
                    updated_at=_now_iso(),
                    result_text=research_result.result_text,
                    result_citations=[
                        citation.model_dump(mode="python")
                        for citation in research_result.citations
                    ],
                    workspace_output_count=0,
                )
                return
            if settings.workbench_langgraph_enabled:
                logger.warning(
                    "LangGraph runtime is enabled in config but unavailable; "
                    "falling back to legacy workbench retrieval.",
                    extra={"task_id": task_id},
                )
            _execute_retrieval_task(
                task=claimed,
                repository=repository,
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
                now_iso=_now_iso,
                append_task_event=_append_task_event,
                source_resolver=resolve_requested_sources,
                knowledge_search=search_knowledge,
                web_search=search_public_web,
                no_runnable_sources_error=_RETRIEVAL_NO_RUNNABLE_SOURCES,
                execution_failed_error=_RETRIEVAL_EXECUTION_FAILED,
            )
            return
        if claimed.task_kind == "canvas":
            _execute_canvas_task(
                task=claimed,
                repository=repository,
                llm=llm,
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
                now_iso=_now_iso,
                context_builder=build_chat_knowledge_context,
                empty_result_error=_CANVAS_EMPTY_RESULT,
            )
            return
        if claimed.task_kind != "plan":
            repository.mark_task_failed(
                task_id,
                updated_at=_now_iso(),
                error_detail=_TASK_NOT_IMPLEMENTED,
            )
            return
        context_block, has_context = _build_plan_or_canvas_context(
            task=claimed,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
            context_builder=build_chat_knowledge_context,
        )

        prompt = _compose_plan_prompt(
            task=claimed,
            context_block=context_block,
            has_context=has_context,
        )
        result_text = llm.generate_completion(_resolve_plan_model(llm), prompt).strip()
        if not result_text:
            repository.mark_task_failed(
                task_id,
                updated_at=_now_iso(),
                error_detail=_PLAN_EMPTY_RESULT,
            )
            return
        repository.mark_task_completed(
            task_id,
            updated_at=_now_iso(),
            result_text=result_text,
            workspace_output_count=0,
        )
    except OllamaUnavailable:
        repository.mark_task_failed(
            task_id,
            updated_at=_now_iso(),
            error_detail=_PLAN_AI_UNAVAILABLE,
        )
    except KnowledgeDocumentNotFound:
        repository.mark_task_failed(
            task_id,
            updated_at=_now_iso(),
            error_detail=_PLAN_KNOWLEDGE_NOT_FOUND,
        )
    except Exception:
        logger.exception("Workbench task execution failed", extra={"task_id": task_id})
        error_detail = _PLAN_EXECUTION_FAILED
        if claimed.task_kind in {"browse", "deep_research"}:
            error_detail = _RETRIEVAL_EXECUTION_FAILED
        elif claimed.task_kind == "canvas":
            error_detail = _CANVAS_EXECUTION_FAILED
        elif claimed.knowledge_document_ids:
            error_detail = _PLAN_KNOWLEDGE_FAILED
        repository.mark_task_failed(
            task_id,
            updated_at=_now_iso(),
            error_detail=error_detail,
        )


def recover_workbench_tasks(
    *,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
) -> WorkbenchRecoveryResult:
    """Recover persisted workbench tasks left behind by a prior process."""

    replayed_task_ids: list[str] = []
    interrupted_task_ids: list[str] = []

    for task_id in repository.list_task_ids_by_status(["running"]):
        repository.mark_task_failed(
            task_id,
            updated_at=_now_iso(),
            error_detail=_TASK_INTERRUPTED,
        )
        interrupted_task_ids.append(task_id)

    for task_id in repository.list_task_ids_by_status(["queued"]):
        execute_workbench_task(
            task_id=task_id,
            repository=repository,
            llm=llm,
            settings=settings,
            request_id="startup-recovery",
        )
        replayed_task_ids.append(task_id)

    return WorkbenchRecoveryResult(
        replayed_task_ids=replayed_task_ids,
        interrupted_task_ids=interrupted_task_ids,
    )
