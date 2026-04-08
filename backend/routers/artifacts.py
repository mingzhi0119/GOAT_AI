"""Artifact download router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from backend.application.artifacts import download_artifact_response
from backend.application.ports import SessionRepository, Settings
from backend.config import get_settings
from backend.dependencies import get_session_repository
from backend.models.common import ErrorResponse

router = APIRouter()


@router.get(
    "/artifacts/{artifact_id}",
    summary="Download one generated chat artifact",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def get_artifact_download(
    artifact_id: str,
    request: Request,
    repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve one persisted artifact file."""
    request_owner = (request.headers.get("x-goat-owner-id") or "").strip()
    return download_artifact_response(
        artifact_id=artifact_id,
        repository=repository,
        settings=settings,
        request_owner=request_owner,
    )
