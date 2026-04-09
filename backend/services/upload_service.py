"""Upload service for routing file uploads into the knowledge ingestion pipeline."""

from __future__ import annotations

from collections.abc import Generator

from backend.application.authz_types import AuthorizationContext
from backend.application.credential_registry import build_local_authorization_context
from backend.models.knowledge import KnowledgeIngestionRequest
from backend.models.upload import UploadAnalysisResponse
from backend.services.exceptions import KnowledgeValidationError
from backend.services.upload_prompt_service import (
    build_suffix_prompt,
    recommend_template_prompt,
)
from backend.services.knowledge_service import (
    create_knowledge_upload_from_bytes,
    start_knowledge_ingestion,
)
from backend.services.sse import sse_done_event, sse_error_event, sse_event
from goat_ai.config import Settings
from backend.types import LLMClient


def ingest_upload(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext | None = None,
    llm: LLMClient | None = None,
) -> UploadAnalysisResponse:
    """Persist, ingest, and return RAG knowledge metadata for one uploaded document."""
    active_auth = auth_context or build_local_authorization_context()
    upload = create_knowledge_upload_from_bytes(
        content=content,
        filename=filename,
        content_type=None,
        settings=settings,
        auth_context=active_auth,
    )
    try:
        ingestion = start_knowledge_ingestion(
            request=KnowledgeIngestionRequest(document_id=upload.document_id),
            settings=settings,
            auth_context=active_auth,
        )
    except ValueError as exc:
        raise KnowledgeValidationError(str(exc)) from exc
    template_prompt = recommend_template_prompt(
        llm=llm,
        settings=settings,
        document_id=upload.document_id,
        filename=upload.filename,
    )
    return UploadAnalysisResponse(
        filename=upload.filename,
        suffix_prompt=build_suffix_prompt(upload.filename),
        document_id=upload.document_id,
        ingestion_id=ingestion.ingestion_id,
        status=ingestion.status,
        retrieval_mode="knowledge_rag",
        template_prompt=template_prompt,
        chart=None,
    )


def stream_upload_analysis_sse(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext | None = None,
    llm: LLMClient | None = None,
) -> Generator[str, None, None]:
    """Ingest the uploaded file into the knowledge pipeline and emit readiness metadata."""
    try:
        suffix_prompt = build_suffix_prompt(filename)
        yield sse_event(
            {
                "type": "file_prompt",
                "filename": filename,
                "suffix_prompt": suffix_prompt,
            }
        )
        result = ingest_upload(
            content=content,
            filename=filename,
            settings=settings,
            auth_context=auth_context,
            llm=llm,
        )
    except KnowledgeValidationError as exc:
        yield sse_error_event(str(exc))
        yield sse_done_event()
        return
    except Exception as exc:
        yield sse_error_event(str(exc))
        yield sse_done_event()
        return

    yield sse_event(
        {
            "type": "knowledge_ready",
            "filename": result.filename,
            "suffix_prompt": result.suffix_prompt,
            "document_id": result.document_id,
            "ingestion_id": result.ingestion_id,
            "status": result.status,
            "retrieval_mode": result.retrieval_mode,
            "template_prompt": result.template_prompt,
        }
    )
    yield sse_done_event()
