"""Scaffold routes for future agent/workbench task orchestration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.application.ports import Settings
from backend.application.workbench import ensure_agent_workbench_enabled
from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.workbench import WorkbenchTaskRequest

router = APIRouter()


@router.post(
    "/workbench/tasks",
    summary="Start a workbench task (scaffold)",
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Workbench runtime is not available on this deployment.",
        },
    },
)
def post_workbench_task(
    request: WorkbenchTaskRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Validate the contract shape and enforce the runtime gate for future tasks."""
    _ = request
    ensure_agent_workbench_enabled(settings)
    raise HTTPException(
        status_code=501,
        detail="Workbench task execution is not implemented yet.",
    )
