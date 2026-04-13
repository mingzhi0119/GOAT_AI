"""Legacy single-pass retrieval executor for workbench browse and research tasks."""

from __future__ import annotations

from collections.abc import Callable

from backend.domain.authz_types import AuthorizationContext
from backend.models.knowledge import (
    KnowledgeCitation,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
)
from backend.services.workbench_source_registry import WorkbenchSourceDescriptor
from backend.services.workbench_web_search import (
    WorkbenchWebSearchError,
    WorkbenchWebSearchHit,
)
from backend.types import Settings


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


def execute_legacy_retrieval_task(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    now_iso: Callable[[], str],
    append_task_event: Callable[..., None],
    source_resolver: Callable[..., list[WorkbenchSourceDescriptor]],
    knowledge_search: Callable[..., KnowledgeSearchResponse],
    web_search: Callable[..., list[WorkbenchWebSearchHit]],
    no_runnable_sources_error: str,
    execution_failed_error: str,
) -> None:
    resolved_sources = source_resolver(
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
    append_task_event(
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
        append_task_event(
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
            updated_at=now_iso(),
            error_detail=no_runnable_sources_error,
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
            response = knowledge_search(
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
            append_task_event(
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
                web_hits = web_search(
                    query=task.prompt,
                    settings=settings,
                    max_results=_resolve_web_result_limit(
                        task_kind=task.task_kind,
                        settings=settings,
                    ),
                )
            except WorkbenchWebSearchError:
                append_task_event(
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
            append_task_event(
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
        append_task_event(
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
            updated_at=now_iso(),
            error_detail=execution_failed_error,
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
        updated_at=now_iso(),
        result_text=result_text,
        result_citations=[citation.model_dump(mode="python") for citation in deduped],
        workspace_output_count=0,
    )
