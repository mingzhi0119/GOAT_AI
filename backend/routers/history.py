"""History router — exposes sidebar conversation session APIs."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api_errors import AUTH_SESSION_OWNER_REQUIRED, build_error_body
from backend.application.history import delete_all_sessions_for_owner, list_session_summaries
from backend.config import get_settings
from backend.dependencies import get_session_repository
from backend.types import Settings
from backend.models.common import ErrorResponse
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionFileContext,
    HistorySessionKnowledgeDocument,
    HistorySessionListResponse,
)
from backend.services.chat_runtime import SessionDetailRecord, SessionRepository

router = APIRouter()


def _owner_header_value(request: Request) -> str:
    return (request.headers.get("x-goat-owner-id") or "").strip()


def _ensure_owner_when_required(settings: Settings, request: Request) -> str:
    owner = _owner_header_value(request)
    if settings.require_session_owner and not owner:
        raise HTTPException(
            status_code=403,
            detail=build_error_body(
                detail="X-GOAT-Owner-Id is required when GOAT_REQUIRE_SESSION_OWNER is enabled.",
                code=AUTH_SESSION_OWNER_REQUIRED,
                status_code=403,
            ),
        )
    return owner


def _list_owner_filter(settings: Settings, owner: str) -> str | None:
    return owner if (settings.require_session_owner or owner) else None


def _session_visible_to_request_owner(
    session: SessionDetailRecord,
    *,
    request_owner: str,
    settings: Settings,
) -> bool:
    if not settings.require_session_owner and not request_owner:
        return True
    return session.owner_id == request_owner


@router.get(
    "/history",
    response_model=HistorySessionListResponse,
    summary="List persisted chat sessions",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def list_history(
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> HistorySessionListResponse:
    """Return session metadata rows for the history sidebar."""
    owner = _ensure_owner_when_required(settings, request)
    owner_filter = _list_owner_filter(settings, owner)
    sessions = [asdict(session) for session in list_session_summaries(session_repository, owner_filter)]
    return HistorySessionListResponse.model_validate({"sessions": sessions})


@router.delete(
    "/history",
    status_code=204,
    summary="Delete all persisted chat sessions",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def delete_all_history(
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Delete all persisted sessions and related conversation rows."""
    owner = _ensure_owner_when_required(settings, request)
    owner_filter = _list_owner_filter(settings, owner)
    delete_all_sessions_for_owner(session_repository, owner_filter)
    return Response(status_code=204)


@router.get(
    "/history/{session_id}",
    response_model=HistorySessionDetailResponse,
    summary="Get one persisted chat session",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def get_history_session(
    session_id: str,
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> HistorySessionDetailResponse:
    """Return one full persisted session including all messages."""
    request_owner = _ensure_owner_when_required(settings, request)
    session = session_repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _session_visible_to_request_owner(
        session,
        request_owner=request_owner,
        settings=settings,
    ):
        raise HTTPException(status_code=404, detail="Session not found")
    response_body = asdict(session)
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


@router.delete(
    "/history/{session_id}",
    status_code=204,
    summary="Delete one persisted chat session",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def delete_history_session(
    session_id: str,
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Delete one persisted session."""
    request_owner = _ensure_owner_when_required(settings, request)
    session = session_repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _session_visible_to_request_owner(
        session,
        request_owner=request_owner,
        settings=settings,
    ):
        raise HTTPException(status_code=404, detail="Session not found")
    session_repository.delete_session(session_id)
    return Response(status_code=204)
