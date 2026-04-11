"""Routes for durable workbench task orchestration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api_errors import build_error_body
from backend.application.exceptions import (
    WorkbenchSourceValidationError,
    WorkbenchTaskNotFoundError,
)
from backend.application.ports import (
    Settings,
    WorkbenchTaskDispatcher,
    WorkbenchTaskRepository,
)
from backend.application.workbench import (
    create_and_dispatch_workbench_task,
    get_workbench_sources,
    get_workbench_task,
    get_workbench_task_events,
)
from backend.dependencies import (
    get_authorization_context,
    get_workbench_task_dispatcher,
    get_workbench_task_repository,
)
from backend.config import get_settings
from backend.domain.authz_types import AuthorizationContext
from backend.models.common import ErrorResponse
from backend.models.workbench import (
    WorkbenchTaskAcceptedResponse,
    WorkbenchTaskEventsResponse,
    WorkbenchTaskRequest,
    WorkbenchTaskStatusResponse,
    WorkbenchSourcesResponse,
)

router = APIRouter()


@router.post(
    "/workbench/tasks",
    status_code=202,
    summary="Create and enqueue a durable workbench task",
    response_model=WorkbenchTaskAcceptedResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def post_workbench_task(
    http_request: Request,
    request: WorkbenchTaskRequest,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    dispatcher: WorkbenchTaskDispatcher = Depends(get_workbench_task_dispatcher),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> WorkbenchTaskAcceptedResponse:
    """Create a durable queued workbench task record and enqueue execution."""
    try:
        return create_and_dispatch_workbench_task(
            request=request,
            repository=repository,
            dispatcher=dispatcher,
            settings=settings,
            auth_context=auth_context,
            request_id=str(getattr(http_request.state, "request_id", "")),
        )
    except WorkbenchSourceValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=build_error_body(
                detail=str(exc),
                status_code=422,
            ),
        ) from exc


@router.get(
    "/workbench/sources",
    response_model=WorkbenchSourcesResponse,
    summary="List declarative workbench retrieval sources",
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def get_workbench_sources_route(
    http_request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> WorkbenchSourcesResponse:
    """List the current caller-visible retrieval sources for workbench tasks."""
    return get_workbench_sources(
        settings=settings,
        auth_context=auth_context,
        request_id=str(getattr(http_request.state, "request_id", "")),
    )


@router.get(
    "/workbench/tasks/{task_id}",
    response_model=WorkbenchTaskStatusResponse,
    summary="Read one durable workbench task status",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def get_workbench_task_status(
    task_id: str,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> WorkbenchTaskStatusResponse:
    """Read the current durable state for one workbench task."""
    try:
        return get_workbench_task(
            task_id=task_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except WorkbenchTaskNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(
                detail=str(exc),
                status_code=404,
            ),
        ) from exc


@router.get(
    "/workbench/tasks/{task_id}/events",
    response_model=WorkbenchTaskEventsResponse,
    summary="Read one durable workbench task event timeline",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def get_workbench_task_event_timeline(
    task_id: str,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> WorkbenchTaskEventsResponse:
    """Read the current durable event timeline for one workbench task."""
    try:
        return get_workbench_task_events(
            task_id=task_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except WorkbenchTaskNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(
                detail=str(exc),
                status_code=404,
            ),
        ) from exc
