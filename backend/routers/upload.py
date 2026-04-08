"""POST /api/upload - ingest supported files into the knowledge RAG pipeline."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.upload import UploadAnalysisResponse
from backend.services.exceptions import KnowledgeValidationError
from backend.services.idempotency_service import SQLiteIdempotencyStore, build_request_hash
from backend.services.knowledge_storage import SUPPORTED_KNOWLEDGE_EXTENSIONS
from backend.services.upload_service import ingest_upload, stream_upload_analysis_sse
from backend.types import Settings

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
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Accept a supported file, ingest it into knowledge storage, and stream readiness metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
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
    summary="Ingest an uploaded file and return JSON readiness metadata",
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
    """Accept a supported knowledge file and return ingestion metadata as JSON."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    content = await file.read()
    idempotency_key = (idempotency_key_header or "").strip()
    idempotency_scope = "upload_analyze_json"
    request_hash = build_request_hash(file.filename.encode("utf-8") + b"\x00" + content)
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
        response_model = ingest_upload(
            content=content,
            filename=file.filename,
            settings=settings,
        )
    except KnowledgeValidationError as exc:
        if idempotency_key:
            idempotency_store.release_pending(
                key=idempotency_key,
                route="/api/upload/analyze",
                scope=idempotency_scope,
                request_hash=request_hash,
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
