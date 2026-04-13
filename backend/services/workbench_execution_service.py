"""In-process executor for minimal Phase 17B/17C workbench tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, Scope, TenantId
from backend.models.knowledge import KnowledgeCitation, KnowledgeSearchRequest
from backend.services.knowledge_service import (
    build_chat_knowledge_context,
    search_knowledge,
)
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.workbench_research_runtime import (
    WorkbenchResearchExecutionFailed,
    WorkbenchResearchNoRunnableSources,
    execute_langgraph_research_task,
    langgraph_runtime_available,
)
from backend.services.workbench_source_registry import resolve_requested_sources
from backend.services.workbench_web_search import (
    WorkbenchWebSearchHit,
    WorkbenchWebSearchError,
    search_public_web,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputCreatePayload,
    WorkbenchTaskRepository,
)
from backend.types import LLMClient, Settings
from goat_ai.shared.exceptions import OllamaUnavailable

logger = logging.getLogger(__name__)

_DEFAULT_PLAN_MODEL = "gemma4:26b"
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


def _resolve_plan_model(llm: LLMClient) -> str:
    names = llm.list_model_names()
    return names[0] if names else _DEFAULT_PLAN_MODEL


def _compose_plan_prompt(
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


def _compose_canvas_prompt(
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


def _dedupe_citations(citations: list[KnowledgeCitation]) -> list[KnowledgeCitation]:
    seen: set[tuple[str, str]] = set()
    out: list[KnowledgeCitation] = []
    for citation in citations:
        key = (citation.document_id, citation.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(citation)
    return out


def _compose_retrieval_result(
    *,
    task: WorkbenchTaskRecord,
    citations: list[KnowledgeCitation],
    runnable_source_ids: list[str],
    skipped_sources: list[dict[str, str]],
) -> str:
    heading = "Browse Summary" if task.task_kind == "browse" else "Research Brief"
    lines = [
        f"## {heading}",
        f"- Query: {task.prompt}",
        "- Runnable sources: " + (", ".join(runnable_source_ids) or "none"),
    ]
    if skipped_sources:
        skipped = ", ".join(
            f"{item['source_id']} ({item['deny_reason']})" for item in skipped_sources
        )
        lines.append(f"- Deferred sources: {skipped}")
    if not citations:
        lines.extend(
            [
                "",
                "## Evidence",
                "- No relevant context was found in the currently runnable sources.",
            ]
        )
        return "\n".join(lines)

    lines.extend(["", "## Evidence"])
    for citation in citations:
        snippet = citation.snippet.strip().replace("\n", " ")
        bounded = snippet[:220].strip()
        if citation.document_id.startswith(("http://", "https://")):
            lines.append(f"- [{citation.filename}]({citation.document_id}): {bounded}")
        else:
            lines.append(f"- {citation.filename}: {bounded}")
    if task.task_kind == "deep_research":
        lines.extend(
            [
                "",
                "## Gaps",
                "- Current runtime performs one bounded retrieval pass rather than iterative agentic research.",
                "- Treat this as an evidence brief, not a full autonomous long-horizon investigation.",
            ]
        )
    return "\n".join(lines)


def _web_hit_to_citation(hit: WorkbenchWebSearchHit) -> KnowledgeCitation:
    return KnowledgeCitation(
        document_id=hit.url,
        chunk_id=hit.url,
        filename=hit.title,
        snippet=hit.snippet,
        score=max(0.0, 1.0 - ((hit.rank - 1) * 0.01)),
    )


def _resolve_web_result_limit(*, task_kind: str, settings: Settings) -> int:
    default_limit = 8 if task_kind == "deep_research" else 5
    return min(default_limit, settings.workbench_web_max_results)


def _execute_retrieval_task(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> None:
    resolved_sources = resolve_requested_sources(
        source_ids=task.source_ids,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    runnable = [source for source in resolved_sources if source.runtime_ready]
    skipped = [
        {
            "source_id": source.source_id,
            "deny_reason": source.deny_reason or "not_runtime_ready",
        }
        for source in resolved_sources
        if not source.runtime_ready
    ]
    _append_task_event(
        repository=repository,
        task_id=task.id,
        event_type="retrieval.sources_resolved",
        status="running",
        message="Retrieval sources resolved.",
        metadata={
            "requested_source_ids": list(task.source_ids),
            "runnable_source_ids": [source.source_id for source in runnable],
            "skipped_sources": skipped,
        },
    )
    for skipped_source in skipped:
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="retrieval.step.skipped",
            status="running",
            message=(
                f"Skipped source {skipped_source['source_id']} "
                f"({skipped_source['deny_reason']})."
            ),
            metadata=dict(skipped_source),
        )
    if not runnable:
        repository.mark_task_failed(
            task.id,
            updated_at=_now_iso(),
            error_detail=_RETRIEVAL_NO_RUNNABLE_SOURCES,
        )
        return

    all_citations: list[KnowledgeCitation] = []
    completed_sources: list[str] = []
    for source in runnable:
        if source.source_id == "knowledge":
            top_k = 8 if task.task_kind == "deep_research" else 5
            retrieval_profile = (
                "rag3_quality" if task.task_kind == "deep_research" else "default"
            )
            response = search_knowledge(
                request=KnowledgeSearchRequest(
                    query=task.prompt,
                    document_ids=task.knowledge_document_ids,
                    top_k=top_k,
                    retrieval_profile=retrieval_profile,
                ),
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
            )
            all_citations.extend(response.hits)
            completed_sources.append("knowledge")
            _append_task_event(
                repository=repository,
                task_id=task.id,
                event_type="retrieval.step.completed",
                status="running",
                message=f"Source knowledge returned {len(response.hits)} citations.",
                metadata={
                    "source_id": "knowledge",
                    "citation_count": len(response.hits),
                    "retrieval_profile": retrieval_profile,
                    "effective_query": response.effective_query or task.prompt,
                },
            )
            continue
        if source.source_id == "web":
            try:
                web_hits = search_public_web(
                    query=task.prompt,
                    settings=settings,
                    max_results=_resolve_web_result_limit(
                        task_kind=task.task_kind,
                        settings=settings,
                    ),
                )
            except WorkbenchWebSearchError:
                _append_task_event(
                    repository=repository,
                    task_id=task.id,
                    event_type="retrieval.step.skipped",
                    status="running",
                    message="Source web failed to return results.",
                    metadata={
                        "source_id": "web",
                        "deny_reason": "provider_error",
                        "provider": settings.workbench_web_provider,
                    },
                )
                continue
            all_citations.extend(_web_hit_to_citation(hit) for hit in web_hits)
            completed_sources.append("web")
            _append_task_event(
                repository=repository,
                task_id=task.id,
                event_type="retrieval.step.completed",
                status="running",
                message=f"Source web returned {len(web_hits)} citations.",
                metadata={
                    "source_id": "web",
                    "citation_count": len(web_hits),
                    "provider": settings.workbench_web_provider,
                    "max_results": _resolve_web_result_limit(
                        task_kind=task.task_kind,
                        settings=settings,
                    ),
                    "urls": [hit.url for hit in web_hits[:5]],
                },
            )
            continue
        _append_task_event(
            repository=repository,
            task_id=task.id,
            event_type="retrieval.step.skipped",
            status="running",
            message=f"Source {source.source_id} is registered but has no executor yet.",
            metadata={"source_id": source.source_id, "deny_reason": "no_executor"},
        )

    if not completed_sources:
        repository.mark_task_failed(
            task.id,
            updated_at=_now_iso(),
            error_detail=_RETRIEVAL_EXECUTION_FAILED,
        )
        return

    deduped = _dedupe_citations(all_citations)
    result_text = _compose_retrieval_result(
        task=task,
        citations=deduped,
        runnable_source_ids=[source.source_id for source in runnable],
        skipped_sources=skipped,
    )
    repository.mark_task_completed(
        task.id,
        updated_at=_now_iso(),
        result_text=result_text,
        result_citations=[citation.model_dump(mode="python") for citation in deduped],
        workspace_output_count=0,
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


def _derive_canvas_title(*, task: WorkbenchTaskRecord, content: str) -> str:
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


def _build_plan_or_canvas_context(
    *,
    task: WorkbenchTaskRecord,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> tuple[str, bool]:
    if not task.knowledge_document_ids:
        return "", False
    context = build_chat_knowledge_context(
        query=task.prompt,
        document_ids=task.knowledge_document_ids,
        top_k=5,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    return context.context_block, bool(context.citations)


def _execute_canvas_task(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    llm: LLMClient,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> None:
    context_block, has_context = _build_plan_or_canvas_context(
        task=task,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    prompt = _compose_canvas_prompt(
        task=task,
        context_block=context_block,
        has_context=has_context,
    )
    content = llm.generate_completion(_resolve_plan_model(llm), prompt).strip()
    if not content:
        repository.mark_task_failed(
            task.id,
            updated_at=_now_iso(),
            error_detail=_CANVAS_EMPTY_RESULT,
        )
        return
    now = _now_iso()
    repository.create_workspace_output(
        WorkbenchWorkspaceOutputCreatePayload(
            output_id=f"wbo-{uuid4().hex}",
            task_id=task.id,
            output_kind="canvas_document",
            title=_derive_canvas_title(task=task, content=content),
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
        updated_at=_now_iso(),
        result_text=content,
        workspace_output_count=1,
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
