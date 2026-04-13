"""Read-only project-memory and connector retrieval helpers for workbench tasks."""

from __future__ import annotations

import re
from collections.abc import Iterable

from backend.domain.authz_types import AuthorizationContext
from backend.models.knowledge import KnowledgeCitation
from backend.services.authorizer import authorize_workbench_output_read
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchTaskRepository,
    WorkbenchWorkspaceOutputRecord,
)
from backend.types import Settings
from goat_ai.shared.workbench_connector_bindings import (
    WorkbenchConnectorBinding,
    WorkbenchConnectorDocument,
    parse_workbench_connector_bindings_json,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{2,}")


class WorkbenchConnectorBindingNotFound(KeyError):
    """Raised when a configured connector binding cannot be found at runtime."""


def search_project_memory(
    *,
    task: WorkbenchTaskRecord,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    query: str,
) -> list[KnowledgeCitation]:
    """Search visible durable workspace outputs for the requested project scope."""
    project_id = (task.project_id or "").strip()
    if not project_id:
        return []
    ranked: list[KnowledgeCitation] = []
    for output in repository.list_workspace_outputs_for_project(project_id):
        decision = authorize_workbench_output_read(
            ctx=auth_context,
            output=output,
            require_owner_header=settings.require_session_owner,
        )
        if not decision.allowed:
            continue
        citation = _workspace_output_to_citation(query=query, output=output)
        if citation is not None:
            ranked.append(citation)
    return sorted(ranked, key=lambda item: (-item.score, item.filename))[
        : _resolve_result_limit(task.task_kind)
    ]


def search_connector_binding(
    *,
    source_id: str,
    task_kind: str,
    settings: Settings,
    query: str,
) -> list[KnowledgeCitation]:
    """Search one configured read-only connector binding."""
    binding = _connector_binding_by_source_id(settings, source_id)
    ranked: list[KnowledgeCitation] = []
    for document in binding.documents:
        citation = _connector_document_to_citation(
            binding=binding,
            document=document,
            query=query,
        )
        if citation is not None:
            ranked.append(citation)
    return sorted(ranked, key=lambda item: (-item.score, item.filename))[
        : _resolve_result_limit(task_kind)
    ]


def _connector_binding_by_source_id(
    settings: Settings, source_id: str
) -> WorkbenchConnectorBinding:
    for binding in parse_workbench_connector_bindings_json(
        settings.workbench_connector_bindings_json
    ):
        if binding.source_id == source_id:
            return binding
    raise WorkbenchConnectorBindingNotFound(source_id)


def _workspace_output_to_citation(
    *,
    query: str,
    output: WorkbenchWorkspaceOutputRecord,
) -> KnowledgeCitation | None:
    score, snippet = _score_match(
        query=query,
        title=output.title,
        content=output.content_text,
        snippet_seed=output.content_text,
    )
    if score <= 0:
        return None
    return KnowledgeCitation(
        document_id=f"workbench-output:{output.id}",
        chunk_id=output.id,
        filename=output.title,
        snippet=snippet,
        score=score,
    )


def _connector_document_to_citation(
    *,
    binding: WorkbenchConnectorBinding,
    document: WorkbenchConnectorDocument,
    query: str,
) -> KnowledgeCitation | None:
    score, snippet = _score_match(
        query=query,
        title=f"{binding.display_name} {document.title}",
        content=document.content,
        snippet_seed=document.snippet or document.content,
    )
    if score <= 0:
        return None
    return KnowledgeCitation(
        document_id=document.document_id,
        chunk_id=f"{binding.source_id}:{document.document_id}",
        filename=document.title,
        snippet=snippet,
        score=score,
    )


def _score_match(
    *,
    query: str,
    title: str,
    content: str,
    snippet_seed: str,
) -> tuple[float, str]:
    tokens = list(_query_tokens(query))
    if not tokens:
        return 0.1, _build_snippet(snippet_seed, ())
    title_text = title.casefold()
    content_text = content.casefold()
    hits = 0
    matched_tokens: list[str] = []
    for token in tokens:
        matched = False
        if token in title_text:
            hits += 3
            matched = True
        if token in content_text:
            hits += 1
            matched = True
        if matched:
            matched_tokens.append(token)
    if hits == 0:
        return 0.0, ""
    denominator = max(len(tokens) * 4, 1)
    score = min(0.99, round(hits / denominator, 4))
    return score, _build_snippet(snippet_seed, matched_tokens)


def _build_snippet(text: str, tokens: Iterable[str]) -> str:
    collapsed = " ".join(text.split()).strip()
    if not collapsed:
        return ""
    lowered = collapsed.casefold()
    for token in tokens:
        position = lowered.find(token)
        if position >= 0:
            start = max(0, position - 80)
            end = min(len(collapsed), position + 200)
            return collapsed[start:end].strip()
    return collapsed[:240].strip()


def _query_tokens(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_TOKEN_PATTERN.findall(query.casefold())))


def _resolve_result_limit(task_kind: str) -> int:
    return 8 if task_kind == "deep_research" else 5
