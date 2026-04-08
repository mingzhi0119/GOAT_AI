"""History router — exposes sidebar conversation session APIs."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.dependencies import get_session_repository
from backend.models.common import ErrorResponse
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionFileContext,
    HistorySessionKnowledgeDocument,
    HistorySessionListResponse,
)
from backend.services.chat_runtime import SessionRepository

router = APIRouter()


@router.get(
    "/history",
    response_model=HistorySessionListResponse,
    summary="List persisted chat sessions",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def list_history(
    session_repository: SessionRepository = Depends(get_session_repository),
) -> HistorySessionListResponse:
    """Return session metadata rows for the history sidebar."""
    sessions = [asdict(session) for session in session_repository.list_sessions()]
    return HistorySessionListResponse.model_validate({"sessions": sessions})


@router.delete(
    "/history",
    status_code=204,
    summary="Delete all persisted chat sessions",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def delete_all_history(
    session_repository: SessionRepository = Depends(get_session_repository),
) -> Response:
    """Delete all persisted sessions and related conversation rows."""
    session_repository.delete_all_sessions()
    return Response(status_code=204)


@router.get(
    "/history/{session_id}",
    response_model=HistorySessionDetailResponse,
    summary="Get one persisted chat session",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_history_session(
    session_id: str,
    session_repository: SessionRepository = Depends(get_session_repository),
) -> HistorySessionDetailResponse:
    """Return one full persisted session including all messages."""
    session = session_repository.get_session(session_id)
    if session is None:
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
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def delete_history_session(
    session_id: str,
    session_repository: SessionRepository = Depends(get_session_repository),
) -> Response:
    """Delete one persisted session."""
    session_repository.delete_session(session_id)
    return Response(status_code=204)
