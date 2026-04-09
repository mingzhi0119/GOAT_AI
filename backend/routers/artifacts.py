"""Artifact download router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from backend.domain.authz_types import AuthorizationContext
from backend.application.artifacts import download_artifact_response
from backend.application.ports import SessionRepository, Settings
from backend.config import get_settings
from backend.dependencies import get_authorization_context, get_session_repository
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
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> FileResponse:
    """Serve one persisted artifact file."""
    return download_artifact_response(
        artifact_id=artifact_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
        request_id=getattr(request.state, "request_id", ""),
    )
