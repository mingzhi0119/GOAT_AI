"""POST /api/upload — parse CSV/XLSX and return structured metadata via SSE."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.upload import UploadAnalysisResponse
from backend.services.upload_service import analyze_upload, stream_upload_analysis_sse
from goat_ai.config import Settings

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

    Returns SSE events: ``file_context`` (always), ``chart_spec`` (when numeric
    data is present), then ``[DONE]``. No LLM inference is performed here; the
    caller uses the file_context prompt as hidden history on the next chat turn.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported.")

    content = await file.read(_MAX_READ_BYTES)

    return StreamingResponse(
        stream_upload_analysis_sse(
            content=content,
            filename=file.filename,
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
) -> UploadAnalysisResponse:
    """Accept a CSV or XLSX upload and return reusable analysis metadata as JSON."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported.")

    content = await file.read(_MAX_READ_BYTES)
    try:
        prompt, chart = analyze_upload(content=content, filename=file.filename, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadAnalysisResponse(filename=file.filename, prompt=prompt, chart=chart)
