"""Pure source-executor registry for LangGraph workbench research steps."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.domain.authz_types import AuthorizationContext
from backend.models.knowledge import (
    KnowledgeCitation,
    KnowledgeSearchRequest,
)
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.workbench_readonly_retrieval import (
    WorkbenchConnectorBindingNotFound,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
)
from backend.services.workbench_web_search import (
    WorkbenchWebSearchError,
    WorkbenchWebSearchHit,
)
from backend.types import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkbenchResearchSourceExecutionContext:
    """Per-step dependency bundle used by source executors."""

    task: WorkbenchTaskRecord
    repository: WorkbenchTaskRepository
    settings: Settings
    auth_context: AuthorizationContext
    request_id: str
    query: str
    knowledge_search: Callable[..., Any]
    web_search: Callable[..., list[WorkbenchWebSearchHit]]
    project_memory_search: Callable[..., list[KnowledgeCitation]]
    connector_search: Callable[..., list[KnowledgeCitation]]


@dataclass(frozen=True)
class WorkbenchResearchSourceExecutionResult:
    """Normalized outcome for one source run inside a research step."""

    source_id: str
    citations: list[KnowledgeCitation]
    metadata: dict[str, object]
    failure_reason: str | None = None


def resolve_workbench_research_source_executor(
    source_id: str,
) -> (
    Callable[
        [WorkbenchResearchSourceExecutionContext],
        WorkbenchResearchSourceExecutionResult,
    ]
    | None
):
    """Resolve the narrow executor for one known source id family."""
    if source_id == "knowledge":
        return _execute_knowledge_source
    if source_id == "web":
        return _execute_web_source
    if source_id == "project_memory":
        return _execute_project_memory_source
    if source_id.startswith("connector:"):
        return lambda context: execute_connector_source_by_id(
            source_id=source_id,
            context=context,
        )
    return None


def _execute_knowledge_source(
    context: WorkbenchResearchSourceExecutionContext,
) -> WorkbenchResearchSourceExecutionResult:
    try:
        response = context.knowledge_search(
            request=KnowledgeSearchRequest(
                query=context.query,
                document_ids=context.task.knowledge_document_ids,
                top_k=8 if context.task.task_kind == "deep_research" else 5,
                retrieval_profile=(
                    "rag3_quality"
                    if context.task.task_kind == "deep_research"
                    else "default"
                ),
            ),
            settings=context.settings,
            auth_context=context.auth_context,
            request_id=context.request_id,
        )
    except KnowledgeDocumentNotFound:
        raise
    except Exception as exc:
        logger.warning(
            "Workbench knowledge research step failed",
            extra={
                "task_id": context.task.id,
                "query": context.query,
            },
            exc_info=exc,
        )
        return WorkbenchResearchSourceExecutionResult(
            source_id="knowledge",
            citations=[],
            metadata={},
            failure_reason="provider_error",
        )
    return WorkbenchResearchSourceExecutionResult(
        source_id="knowledge",
        citations=list(response.hits),
        metadata={
            "effective_query": response.effective_query or context.query,
        },
    )


def _execute_web_source(
    context: WorkbenchResearchSourceExecutionContext,
) -> WorkbenchResearchSourceExecutionResult:
    try:
        web_hits = context.web_search(
            query=context.query,
            settings=context.settings,
            max_results=_resolve_web_result_limit(
                task=context.task,
                settings=context.settings,
            ),
        )
    except WorkbenchWebSearchError:
        return WorkbenchResearchSourceExecutionResult(
            source_id="web",
            citations=[],
            metadata={"provider": context.settings.workbench_web_provider},
            failure_reason="provider_error",
        )
    return WorkbenchResearchSourceExecutionResult(
        source_id="web",
        citations=[_web_hit_to_citation(hit) for hit in web_hits],
        metadata={
            "provider": context.settings.workbench_web_provider,
            "max_results": _resolve_web_result_limit(
                task=context.task,
                settings=context.settings,
            ),
            "urls": [hit.url for hit in web_hits[:5]],
        },
    )


def _execute_project_memory_source(
    context: WorkbenchResearchSourceExecutionContext,
) -> WorkbenchResearchSourceExecutionResult:
    if not context.task.project_id:
        return WorkbenchResearchSourceExecutionResult(
            source_id="project_memory",
            citations=[],
            metadata={},
            failure_reason="project_scope_missing",
        )
    try:
        project_hits = context.project_memory_search(
            task=context.task,
            repository=context.repository,
            settings=context.settings,
            auth_context=context.auth_context,
            query=context.query,
        )
    except Exception as exc:
        logger.warning(
            "Workbench project-memory research step failed",
            extra={
                "task_id": context.task.id,
                "query": context.query,
            },
            exc_info=exc,
        )
        return WorkbenchResearchSourceExecutionResult(
            source_id="project_memory",
            citations=[],
            metadata={},
            failure_reason="provider_error",
        )
    return WorkbenchResearchSourceExecutionResult(
        source_id="project_memory",
        citations=project_hits,
        metadata={"project_id": context.task.project_id},
    )


def execute_connector_source_by_id(
    *,
    source_id: str,
    context: WorkbenchResearchSourceExecutionContext,
) -> WorkbenchResearchSourceExecutionResult:
    """Run a connector search for one concrete source id."""
    try:
        connector_hits = context.connector_search(
            source_id=source_id,
            task_kind=context.task.task_kind,
            settings=context.settings,
            query=context.query,
        )
    except WorkbenchConnectorBindingNotFound:
        return WorkbenchResearchSourceExecutionResult(
            source_id=source_id,
            citations=[],
            metadata={},
            failure_reason="binding_unavailable",
        )
    except Exception as exc:
        logger.warning(
            "Workbench connector research step failed",
            extra={
                "task_id": context.task.id,
                "query": context.query,
                "source_id": source_id,
            },
            exc_info=exc,
        )
        return WorkbenchResearchSourceExecutionResult(
            source_id=source_id,
            citations=[],
            metadata={},
            failure_reason="provider_error",
        )
    return WorkbenchResearchSourceExecutionResult(
        source_id=source_id,
        citations=connector_hits,
        metadata={},
    )


def _resolve_web_result_limit(
    *,
    task: WorkbenchTaskRecord,
    settings: Settings,
) -> int:
    default_limit = 8 if task.task_kind == "deep_research" else 5
    return min(default_limit, settings.workbench_web_max_results)


def _web_hit_to_citation(hit: WorkbenchWebSearchHit) -> KnowledgeCitation:
    return KnowledgeCitation(
        document_id=hit.url,
        chunk_id=hit.url,
        filename=hit.title,
        snippet=hit.snippet,
        score=max(0.0, 1.0 - ((hit.rank - 1) * 0.01)),
    )
