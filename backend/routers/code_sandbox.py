"""Routes for capability-gated code sandbox execution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from backend.api_errors import build_error_body
from backend.application.code_sandbox import (
    execute_code_sandbox_request,
    get_code_sandbox_execution,
    get_code_sandbox_execution_events,
    stream_code_sandbox_execution_logs,
)
from backend.application.exceptions import (
    CodeSandboxExecutionNotFoundError,
    CodeSandboxValidationError,
)
from backend.application.ports import (
    CodeSandboxExecutionDispatcher,
    CodeSandboxExecutionRepository,
    SandboxProvider,
    Settings,
)
from backend.platform.config import get_settings
from backend.platform.dependencies import (
    get_authorization_context,
    get_code_sandbox_execution_dispatcher,
    get_code_sandbox_execution_repository,
    get_code_sandbox_provider,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.code_sandbox import (
    CodeSandboxExecRequest,
    CodeSandboxExecutionEventsResponse,
    CodeSandboxExecutionResponse,
)
from backend.models.common import ErrorResponse

router = APIRouter()


@router.post(
    "/code-sandbox/exec",
    response_model=CodeSandboxExecutionResponse,
    summary="Execute code in an isolated sandbox",
    responses={
        401: {"model": ErrorResponse},
        202: {
            "model": CodeSandboxExecutionResponse,
            "description": "Execution accepted for async processing.",
        },
        403: {
            "model": ErrorResponse,
            "description": "Policy denied (FEATURE_DISABLED)",
        },
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Runtime gate closed or sandbox provider unavailable.",
        },
    },
)
def post_code_sandbox_exec(
    request: CodeSandboxExecRequest,
    response: Response,
    repository: CodeSandboxExecutionRepository = Depends(
        get_code_sandbox_execution_repository
    ),
    provider: SandboxProvider = Depends(get_code_sandbox_provider),
    dispatcher: CodeSandboxExecutionDispatcher = Depends(
        get_code_sandbox_execution_dispatcher
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> CodeSandboxExecutionResponse:
    """Execute one durable code sandbox request and persist the result."""
    try:
        payload = execute_code_sandbox_request(
            request=request,
            repository=repository,
            provider=provider,
            dispatcher=dispatcher,
            settings=settings,
            auth_context=auth_context,
        )
        if payload.execution_mode == "async" and payload.status in {
            "queued",
            "running",
        }:
            response.status_code = 202
        return payload
    except CodeSandboxValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=build_error_body(detail=str(exc), status_code=422),
        ) from exc


@router.get(
    "/code-sandbox/executions/{execution_id}",
    response_model=CodeSandboxExecutionResponse,
    summary="Read one persisted code sandbox execution",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Runtime gate closed or sandbox provider unavailable.",
        },
    },
)
def get_code_sandbox_execution_route(
    execution_id: str,
    repository: CodeSandboxExecutionRepository = Depends(
        get_code_sandbox_execution_repository
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> CodeSandboxExecutionResponse:
    """Read one visible code sandbox execution record."""
    try:
        return get_code_sandbox_execution(
            execution_id=execution_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except CodeSandboxExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(detail=str(exc), status_code=404),
        ) from exc


@router.get(
    "/code-sandbox/executions/{execution_id}/events",
    response_model=CodeSandboxExecutionEventsResponse,
    summary="Read one code sandbox execution event timeline",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Runtime gate closed or sandbox provider unavailable.",
        },
    },
)
def get_code_sandbox_execution_events_route(
    execution_id: str,
    repository: CodeSandboxExecutionRepository = Depends(
        get_code_sandbox_execution_repository
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> CodeSandboxExecutionEventsResponse:
    """Read the durable event timeline for one visible execution."""
    try:
        return get_code_sandbox_execution_events(
            execution_id=execution_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except CodeSandboxExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(detail=str(exc), status_code=404),
        ) from exc


@router.get(
    "/code-sandbox/executions/{execution_id}/logs",
    summary="Stream one code sandbox execution log timeline",
    responses={
        200: {"content": {"text/event-stream": {}}},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Runtime gate closed or sandbox provider unavailable.",
        },
    },
)
def get_code_sandbox_execution_logs_route(
    execution_id: str,
    after_seq: int = Query(default=0, ge=0),
    repository: CodeSandboxExecutionRepository = Depends(
        get_code_sandbox_execution_repository
    ),
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> StreamingResponse:
    """Stream replayable stdout/stderr chunks and status updates for one execution."""
    try:
        return stream_code_sandbox_execution_logs(
            execution_id=execution_id,
            after_sequence=after_seq,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    except CodeSandboxExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_error_body(detail=str(exc), status_code=404),
        ) from exc
