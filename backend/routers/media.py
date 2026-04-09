"""POST /api/media/uploads - register a vision image attachment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from backend.application.authz_types import AuthorizationContext
from backend.application.media import create_media_upload
from backend.application.ports import MediaValidationError, Settings
from backend.config import get_settings
from backend.dependencies import get_authorization_context
from backend.models.common import ErrorResponse
from backend.models.media import MediaUploadResponse

router = APIRouter()


@router.post(
    "/media/uploads",
    response_model=MediaUploadResponse,
    summary="Upload an image for vision chat",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def post_media_upload(
    request: Request,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> MediaUploadResponse:
    """Persist and normalize a PNG/JPEG/WebP image for use with POST /api/chat."""
    try:
        raw = await file.read()
        return create_media_upload(
            content=raw,
            filename=file.filename or "",
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except MediaValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
