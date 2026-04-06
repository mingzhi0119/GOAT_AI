"""POST /api/upload — parse CSV/XLSX and return structured metadata via SSE."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.services.upload_service import stream_upload_analysis_sse
from goat_ai.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}

_MAX_READ_BYTES = 25 * 1024 * 1024  # hard cap before hitting service logic


@router.post("/upload")
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
