"""History router - exposes sidebar conversation session APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api_errors import AUTH_SESSION_OWNER_REQUIRED, build_error_body
from backend.application.exceptions import (
    HistoryOwnerRequiredError,
    HistorySessionNotFoundError,
)
from backend.application.history import (
    delete_all_history_sessions,
    delete_history_session as delete_history_session_use_case,
    get_history_session_detail,
    list_history_sessions,
)
from backend.application.ports import SessionRepository, Settings
from backend.config import get_settings
from backend.dependencies import get_session_repository
from backend.models.common import ErrorResponse
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionListResponse,
)

router = APIRouter()


def _owner_header_value(request: Request) -> str:
    return (request.headers.get("x-goat-owner-id") or "").strip()


def _raise_owner_required(exc: HistoryOwnerRequiredError) -> None:
    raise HTTPException(
        status_code=403,
        detail=build_error_body(
            detail=str(exc),
            code=AUTH_SESSION_OWNER_REQUIRED,
            status_code=403,
        ),
    ) from exc


@router.get(
    "/history",
    response_model=HistorySessionListResponse,
    summary="List persisted chat sessions",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def list_history(
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> HistorySessionListResponse:
    """Return session metadata rows for the history sidebar."""
    owner = _owner_header_value(request)
    try:
        return list_history_sessions(
            repository=session_repository,
            settings=settings,
            request_owner=owner,
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)


@router.delete(
    "/history",
    status_code=204,
    summary="Delete all persisted chat sessions",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def delete_all_history(
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Delete all persisted sessions and related conversation rows."""
    owner = _owner_header_value(request)
    try:
        delete_all_history_sessions(
            repository=session_repository,
            settings=settings,
            request_owner=owner,
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
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
    request_owner = _owner_header_value(request)
    try:
        return get_history_session_detail(
            repository=session_repository,
            session_id=session_id,
            settings=settings,
            request_owner=request_owner,
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except HistorySessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
    request_owner = _owner_header_value(request)
    try:
        delete_history_session_use_case(
            repository=session_repository,
            session_id=session_id,
            settings=settings,
            request_owner=request_owner,
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except HistorySessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
