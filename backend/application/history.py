"""History sidebar use cases over SessionRepository."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend.domain.authz_types import AuthorizationContext
from backend.services.authorizer import authorize_session_read, authorize_session_write
from backend.services.exceptions import SessionNotFoundError
from backend.application.exceptions import (
    HistoryOwnerRequiredError,
    HistorySessionNotFoundError,
)
from backend.application.ports import SessionRepository, Settings
from backend.domain.authorization import ResourceRef
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionFileContext,
    HistorySessionKnowledgeDocument,
    HistorySessionListResponse,
)
from backend.services.authz_audit import emit_authorization_audit


def _session_summary_as_dict(session: Any) -> dict[str, object]:
    return asdict(session)


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
    auth_context: AuthorizationContext,
) -> HistorySessionListResponse:
    """Return persisted session metadata rows for the history sidebar."""
    owner_filter = resolve_owner_filter(
        settings=settings,
        request_owner=auth_context.legacy_owner_id,
    )
    sessions = [
        _session_summary_as_dict(session)
        for session in repository.list_sessions(
            owner_filter=owner_filter,
            tenant_filter=auth_context.tenant_id.value,
        )
        if authorize_session_read(
            ctx=auth_context,
            session=session,
            require_owner_header=settings.require_session_owner,
        ).allowed
    ]
    return HistorySessionListResponse.model_validate({"sessions": sessions})


def delete_all_history_sessions(
    *,
    repository: SessionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> None:
    """Delete sessions scoped to one owner when filtering is enabled."""
    owner_filter = resolve_owner_filter(
        settings=settings,
        request_owner=auth_context.legacy_owner_id,
    )
    repository.delete_all_sessions(
        owner_filter=owner_filter,
        tenant_filter=auth_context.tenant_id.value,
    )


def delete_history_session(
    *,
    repository: SessionRepository,
    session_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> None:
    """Delete one session, enforcing owner visibility rules."""
    get_history_session_detail(
        repository=repository,
        session_id=session_id,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    try:
        repository.delete_session(session_id)
    except SessionNotFoundError as exc:
        raise HistorySessionNotFoundError("Session not found") from exc


def rename_history_session(
    *,
    repository: SessionRepository,
    session_id: str,
    title: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> None:
    """Rename one session, enforcing owner visibility rules."""
    session = repository.get_session(session_id)
    if session is None:
        raise HistorySessionNotFoundError("Session not found")

    decision = authorize_session_write(
        ctx=auth_context,
        session=session,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="history.session.write",
        resource=ResourceRef(resource_type="session", resource_id=session_id),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise HistorySessionNotFoundError("Session not found")

    try:
        repository.rename_session(session_id, title)
    except SessionNotFoundError as exc:
        raise HistorySessionNotFoundError("Session not found") from exc


def get_history_session_detail(
    *,
    repository: SessionRepository,
    session_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> HistorySessionDetailResponse:
    """Return one full persisted session including all messages."""
    session = repository.get_session(session_id)
    if session is None:
        raise HistorySessionNotFoundError("Session not found")

    decision = authorize_session_read(
        ctx=auth_context,
        session=session,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="history.session.read",
        resource=ResourceRef(resource_type="session", resource_id=session_id),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
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
