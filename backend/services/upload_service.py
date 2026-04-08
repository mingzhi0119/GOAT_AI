"""Upload service for routing file uploads into the knowledge ingestion pipeline."""
from __future__ import annotations

from collections.abc import Generator

from backend.models.knowledge import KnowledgeIngestionRequest
from backend.models.upload import UploadAnalysisResponse
from backend.services.exceptions import KnowledgeValidationError
from backend.services.knowledge_service import (
    create_knowledge_upload_from_bytes,
    start_knowledge_ingestion,
)
from backend.services.sse import sse_done_event, sse_error_event, sse_event
from goat_ai.config import Settings


def ingest_upload(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
) -> UploadAnalysisResponse:
    """Persist, ingest, and return RAG knowledge metadata for one uploaded document."""
    upload = create_knowledge_upload_from_bytes(
        content=content,
        filename=filename,
        content_type=None,
        settings=settings,
    )
    try:
        ingestion = start_knowledge_ingestion(
            request=KnowledgeIngestionRequest(document_id=upload.document_id),
            settings=settings,
        )
    except ValueError as exc:
        raise KnowledgeValidationError(str(exc)) from exc
    return UploadAnalysisResponse(
        filename=upload.filename,
        document_id=upload.document_id,
        ingestion_id=ingestion.ingestion_id,
        status=ingestion.status,
        retrieval_mode="knowledge_rag",
        chart=None,
    )


def stream_upload_analysis_sse(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
) -> Generator[str, None, None]:
    """Ingest the uploaded file into the knowledge pipeline and emit readiness metadata."""
    try:
        result = ingest_upload(content=content, filename=filename, settings=settings)
    except KnowledgeValidationError as exc:
        yield sse_error_event(str(exc))
        yield sse_done_event()
        return

    yield sse_event(
        {
            "type": "knowledge_ready",
            "filename": result.filename,
            "document_id": result.document_id,
            "ingestion_id": result.ingestion_id,
            "status": result.status,
            "retrieval_mode": result.retrieval_mode,
        }
    )
    yield sse_done_event()
