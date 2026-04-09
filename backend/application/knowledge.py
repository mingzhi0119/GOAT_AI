"""Knowledge use cases over the knowledge pipeline."""

from __future__ import annotations

from backend.application.ports import Settings
from backend.models.knowledge import (
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
    KnowledgeIngestionStatusResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
    KnowledgeUploadStatusResponse,
)
from backend.services.knowledge_service import (
    answer_with_knowledge,
    create_knowledge_upload,
    get_knowledge_ingestion_status,
    get_knowledge_upload,
    search_knowledge,
    start_knowledge_ingestion,
)


def create_upload(*, file, settings: Settings) -> KnowledgeUploadResponse:
    return create_knowledge_upload(file=file, settings=settings)


def get_upload_status(
    *, document_id: str, settings: Settings
) -> KnowledgeUploadStatusResponse:
    return get_knowledge_upload(document_id=document_id, settings=settings)


def start_ingestion(
    *,
    request: KnowledgeIngestionRequest,
    settings: Settings,
) -> KnowledgeIngestionResponse:
    return start_knowledge_ingestion(request=request, settings=settings)


def get_ingestion_status(
    *,
    ingestion_id: str,
    settings: Settings,
) -> KnowledgeIngestionStatusResponse:
    return get_knowledge_ingestion_status(ingestion_id=ingestion_id, settings=settings)


def search(
    *, request: KnowledgeSearchRequest, settings: Settings
) -> KnowledgeSearchResponse:
    return search_knowledge(request=request, settings=settings)


def answer(
    *, request: KnowledgeAnswerRequest, settings: Settings
) -> KnowledgeAnswerResponse:
    return answer_with_knowledge(request=request, settings=settings)
