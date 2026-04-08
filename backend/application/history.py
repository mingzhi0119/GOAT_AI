"""History sidebar use cases over SessionRepository."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend.application.exceptions import HistoryOwnerRequiredError, HistorySessionNotFoundError
from backend.application.ports import SessionRepository, Settings
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionFileContext,
    HistorySessionKnowledgeDocument,
    HistorySessionListResponse,
)


def _session_summary_as_dict(session: Any) -> dict[str, object]:
    return asdict(session)


def _session_visible_to_request_owner(
    *,
    session_owner_id: str,
    request_owner: str,
    settings: Settings,
) -> bool:
    if not settings.require_session_owner and not request_owner:
        return True
    return session_owner_id == request_owner


def resolve_owner_filter(*, settings: Settings, request_owner: str) -> str | None:
    """Resolve the owner filter used for history list and delete-all operations."""
    if settings.require_session_owner and not request_owner:
        raise HistoryOwnerRequiredError(
            "X-GOAT-Owner-Id is required when GOAT_REQUIRE_SESSION_OWNER is enabled."
        )
    return request_owner if (settings.require_session_owner or request_owner) else None


def list_history_sessions(
    *,
    repository: SessionRepository,
    settings: Settings,
    request_owner: str,
) -> HistorySessionListResponse:
    """Return persisted session metadata rows for the history sidebar."""
    owner_filter = resolve_owner_filter(settings=settings, request_owner=request_owner)
    sessions = [_session_summary_as_dict(session) for session in repository.list_sessions(owner_filter=owner_filter)]
    return HistorySessionListResponse.model_validate({"sessions": sessions})


def delete_all_history_sessions(
    *,
    repository: SessionRepository,
    settings: Settings,
    request_owner: str,
) -> None:
    """Delete sessions scoped to one owner when filtering is enabled."""
    owner_filter = resolve_owner_filter(settings=settings, request_owner=request_owner)
    repository.delete_all_sessions(owner_filter=owner_filter)


def get_history_session_detail(
    *,
    repository: SessionRepository,
    session_id: str,
    settings: Settings,
    request_owner: str,
) -> HistorySessionDetailResponse:
    """Return one full persisted session including all messages."""
    session = repository.get_session(session_id)
    if session is None:
        raise HistorySessionNotFoundError("Session not found")
    if not _session_visible_to_request_owner(
        session_owner_id=session.owner_id,
        request_owner=request_owner,
        settings=settings,
    ):
        raise HistorySessionNotFoundError("Session not found")

    response_body = _session_summary_as_dict(session)
    file_context_prompt = response_body.pop("file_context_prompt", None)
    raw_knowledge_documents = response_body.pop("knowledge_documents", []) or []
    response_body["file_context"] = (
        HistorySessionFileContext(prompt=file_context_prompt)
        if isinstance(file_context_prompt, str) and file_context_prompt.strip()
        else None
    )
    response_body["knowledge_documents"] = [
        HistorySessionKnowledgeDocument.model_validate(item)
        for item in raw_knowledge_documents
        if isinstance(item, dict)
    ]
    return HistorySessionDetailResponse.model_validate(response_body)
