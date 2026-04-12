"""History router - exposes sidebar conversation session APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api_errors import AUTH_SESSION_OWNER_REQUIRED, build_error_body
from backend.domain.authz_types import AuthorizationContext
from backend.application.exceptions import (
    HistoryOwnerRequiredError,
    HistorySessionNotFoundError,
    HistoryValidationError,
)
from backend.application.history import (
    delete_all_history_sessions,
    delete_history_session as delete_history_session_use_case,
    get_history_session_detail,
    list_history_sessions,
    rename_history_session,
)
from backend.application.ports import SessionRepository, Settings
from backend.config import get_settings
from backend.dependencies import (
    get_authorization_context,
    get_session_repository,
    get_workbench_task_repository,
)
from backend.models.common import ErrorResponse
from backend.models.history import (
    HistorySessionDetailResponse,
    HistorySessionListResponse,
    HistorySessionRenameRequest,
)
from backend.services.workbench_runtime import WorkbenchTaskRepository

router = APIRouter()


def _raise_owner_required(exc: HistoryOwnerRequiredError) -> None:
    raise HTTPException(
        status_code=403,
        detail=build_error_body(
            detail=str(exc),
            code=AUTH_SESSION_OWNER_REQUIRED,
            status_code=403,
        ),
    ) from exc


def _raise_not_found(exc: HistorySessionNotFoundError) -> None:
    raise HTTPException(
        status_code=404,
        detail=build_error_body(
            detail=str(exc),
            status_code=404,
        ),
    ) from exc


def _raise_validation_error(exc: HistoryValidationError) -> None:
    raise HTTPException(
        status_code=422,
        detail=build_error_body(
            detail=str(exc),
            status_code=422,
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
        500: {"model": ErrorResponse},
    },
)
def list_history(
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> HistorySessionListResponse:
    """Return session metadata rows for the history sidebar."""
    try:
        return list_history_sessions(
            repository=session_repository,
            settings=settings,
            auth_context=auth_context,
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
        500: {"model": ErrorResponse},
    },
)
def delete_all_history(
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> Response:
    """Delete all persisted sessions and related conversation rows."""
    try:
        delete_all_history_sessions(
            repository=session_repository,
            settings=settings,
            auth_context=auth_context,
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    return Response(status_code=204)


@router.patch(
    "/history/{session_id}",
    status_code=204,
    summary="Rename one persisted chat session",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def rename_history_session_route(
    session_id: str,
    payload: HistorySessionRenameRequest,
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> Response:
    """Rename one persisted session."""
    try:
        rename_history_session(
            repository=session_repository,
            session_id=session_id,
            title=payload.title,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except HistoryValidationError as exc:
        _raise_validation_error(exc)
    except HistorySessionNotFoundError as exc:
        _raise_not_found(exc)
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
        500: {"model": ErrorResponse},
    },
)
def get_history_session(
    session_id: str,
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    workbench_repository: WorkbenchTaskRepository = Depends(
        get_workbench_task_repository
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> HistorySessionDetailResponse:
    """Return one full persisted session including all messages."""
    try:
        return get_history_session_detail(
            repository=session_repository,
            workbench_repository=workbench_repository,
            session_id=session_id,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except HistorySessionNotFoundError as exc:
        _raise_not_found(exc)


@router.delete(
    "/history/{session_id}",
    status_code=204,
    summary="Delete one persisted chat session",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_history_session(
    session_id: str,
    request: Request,
    session_repository: SessionRepository = Depends(get_session_repository),
    workbench_repository: WorkbenchTaskRepository = Depends(
        get_workbench_task_repository
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> Response:
    """Delete one persisted session."""
    try:
        delete_history_session_use_case(
            repository=session_repository,
            workbench_repository=workbench_repository,
            session_id=session_id,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except HistoryOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except HistorySessionNotFoundError as exc:
        _raise_not_found(exc)
    return Response(status_code=204)
