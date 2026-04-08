"""POST /api/upload — parse CSV/XLSX and return structured metadata via SSE."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.upload import UploadAnalysisResponse
from backend.services.idempotency_service import SQLiteIdempotencyStore, build_request_hash
from backend.services.upload_request_service import UploadValidationError, read_validated_upload
from backend.services.upload_service import analyze_upload, stream_upload_analysis_sse
from backend.types import Settings

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}

_MAX_READ_BYTES = 25 * 1024 * 1024  # hard cap before hitting service logic


@router.post(
    "/upload",
    summary="Stream upload analysis events over SSE",
    responses={
        200: {"content": {"text/event-stream": {}}},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def upload_and_parse(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Accept a CSV or XLSX upload, parse it, and stream structured metadata.

    Returns SSE events: ``file_context`` (always), then ``{"type":"done"}``. No LLM
    inference is performed here; the caller uses the file_context prompt as
    hidden history on the next chat turn. Charts are rendered later only if the
    LLM explicitly calls the native chart tool during chat.
    """
    try:
        upload = await read_validated_upload(file=file, max_read_bytes=_MAX_READ_BYTES)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        stream_upload_analysis_sse(
            content=upload.content,
            filename=upload.filename,
            settings=settings,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post(
    "/upload/analyze",
    response_model=UploadAnalysisResponse,
    summary="Analyze an uploaded CSV/XLSX and return JSON",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def analyze_upload_json(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> UploadAnalysisResponse:
    """Accept a CSV or XLSX upload and return reusable analysis metadata as JSON."""
    try:
        upload = await read_validated_upload(file=file, max_read_bytes=_MAX_READ_BYTES)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    idempotency_key = (idempotency_key_header or "").strip()
    idempotency_scope = "upload_analyze_json"
    request_hash = build_request_hash(upload.filename.encode("utf-8") + b"\x00" + upload.content)
    idempotency_store = SQLiteIdempotencyStore(
        db_path=settings.log_db_path,
        ttl_sec=settings.idempotency_ttl_sec,
    )

    if idempotency_key:
        claim = idempotency_store.claim(
            key=idempotency_key,
            route="/api/upload/analyze",
            scope=idempotency_scope,
            request_hash=request_hash,
        )
        if claim.state == "conflict":
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different request payload.",
            )
        if claim.state == "in_progress":
            raise HTTPException(
                status_code=409,
                detail="A request with this Idempotency-Key is already in progress.",
            )
        if claim.state == "replay" and claim.completed is not None:
            return UploadAnalysisResponse.model_validate_json(claim.completed.body)

    try:
        prompt, chart = analyze_upload(
            content=upload.content,
            filename=upload.filename,
            settings=settings,
        )
    except ValueError as exc:
        if idempotency_key:
            idempotency_store.release_pending(
                key=idempotency_key,
                route="/api/upload/analyze",
                scope=idempotency_scope,
                request_hash=request_hash,
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response_model = UploadAnalysisResponse(filename=upload.filename, prompt=prompt, chart=chart)
    if idempotency_key:
        idempotency_store.store_completed(
            key=idempotency_key,
            route="/api/upload/analyze",
            scope=idempotency_scope,
            request_hash=request_hash,
            status_code=200,
            content_type="application/json",
            body=response_model.model_dump_json(),
        )
    return response_model
