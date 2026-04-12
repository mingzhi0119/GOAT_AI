"""Routes for durable workbench task orchestration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api_errors import build_error_body
from backend.application.exceptions import (
    WorkbenchSourceValidationError,
    WorkbenchTaskNotFoundError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.ports import (
    SessionRepository,
    Settings,
    WorkbenchTaskDispatcher,
    WorkbenchTaskRepository,
)
from backend.application.workbench import (
    create_and_dispatch_workbench_task,
    export_workbench_workspace_output,
    get_workbench_sources,
    get_workbench_task,
    get_workbench_task_events,
    get_workbench_workspace_output,
    list_workbench_workspace_outputs,
)
from backend.platform.dependencies import (
    get_authorization_context,
    get_session_repository,
    get_workbench_task_dispatcher,
    get_workbench_task_repository,
)
from backend.platform.config import get_settings
from backend.domain.authz_types import AuthorizationContext
from backend.models.common import ErrorResponse
from backend.models.workbench import (
    WorkbenchTaskAcceptedResponse,
    WorkbenchTaskEventsResponse,
    WorkbenchTaskRequest,
    WorkbenchTaskStatusResponse,
    WorkbenchWorkspaceOutputExportRequest,
    WorkbenchWorkspaceOutputPayload,
    WorkbenchWorkspaceOutputsResponse,
    WorkbenchSourcesResponse,
)
from backend.models.artifact import ChatArtifact

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
    "/workbench/workspace-outputs",
    response_model=WorkbenchWorkspaceOutputsResponse,
    summary="List durable workspace outputs by session or project scope",
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
def list_workbench_workspace_outputs_route(
    session_id: str | None = None,
    project_id: str | None = None,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> WorkbenchWorkspaceOutputsResponse:
    """List visible workspace outputs for one session or project restoration scope."""
    try:
        return list_workbench_workspace_outputs(
            repository=repository,
            settings=settings,
            auth_context=auth_context,
            session_id=session_id,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=build_error_body(
                detail=str(exc),
                status_code=422,
            ),
        ) from exc


@router.get(
    "/workbench/workspace-outputs/{output_id}",
    response_model=WorkbenchWorkspaceOutputPayload,
    summary="Read one durable workspace output",
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
def get_workbench_workspace_output_route(
    output_id: str,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> WorkbenchWorkspaceOutputPayload:
    """Read the latest durable state for one workspace output."""
    try:
        return get_workbench_workspace_output(
            output_id=output_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except WorkbenchWorkspaceOutputNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(
                detail=str(exc),
                status_code=404,
            ),
        ) from exc


@router.post(
    "/workbench/workspace-outputs/{output_id}/exports",
    status_code=201,
    response_model=ChatArtifact,
    summary="Export one durable workspace output into a downloadable artifact",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def export_workbench_workspace_output_route(
    output_id: str,
    payload: WorkbenchWorkspaceOutputExportRequest,
    session_repository: SessionRepository = Depends(get_session_repository),
    task_repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    settings: Settings = Depends(get_settings),
) -> ChatArtifact:
    """Create one downloadable artifact from a durable workspace output."""
    try:
        return export_workbench_workspace_output(
            output_id=output_id,
            request=payload,
            task_repository=task_repository,
            session_repository=session_repository,
            settings=settings,
            auth_context=auth_context,
        )
    except WorkbenchWorkspaceOutputNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(
                detail=str(exc),
                status_code=404,
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=build_error_body(
                detail=str(exc),
                status_code=422,
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
