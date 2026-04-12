"""POST /api/upload - ingest supported files into the knowledge RAG pipeline."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.application.exceptions import (
    UploadIdempotencyConflictError,
    UploadIdempotencyInProgressError,
)
from backend.domain.authz_types import AuthorizationContext
from backend.application.upload import (
    analyze_upload_json,
    ingest_upload,
    stream_upload_analysis,
)
from backend.application.ports import KnowledgeValidationError, Settings
from backend.platform.config import get_settings
from backend.platform.dependencies import get_authorization_context, get_llm_client
from backend.models.common import ErrorResponse
from backend.models.upload import UploadAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.post(
    "/upload",
    summary="Stream upload ingestion events over SSE",
    responses={
        200: {"content": {"text/event-stream": {}}},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def upload_and_parse(
    request: Request,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    llm=Depends(get_llm_client),
) -> StreamingResponse:
    """Accept a supported file, ingest it into knowledge storage, and stream readiness metadata."""
    content = await file.read()
    try:
        return StreamingResponse(
            stream_upload_analysis(
                content=content,
                filename=file.filename or "",
                settings=settings,
                auth_context=auth_context,
                llm=llm,
            ),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )
    except KnowledgeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/upload/analyze",
    response_model=UploadAnalysisResponse,
    summary="Ingest an uploaded file and return JSON readiness metadata",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def analyze_upload_json_route(
    request: Request,
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
    llm=Depends(get_llm_client),
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> UploadAnalysisResponse:
    """Accept a supported knowledge file and return ingestion metadata as JSON."""
    content = await file.read()
    try:
        return analyze_upload_json(
            content=content,
            filename=file.filename or "",
            settings=settings,
            auth_context=auth_context,
            idempotency_key=idempotency_key_header,
            llm=llm,
            ingest_upload_fn=ingest_upload,
        )
    except KnowledgeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UploadIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UploadIdempotencyInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
