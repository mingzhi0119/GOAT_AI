"""Knowledge use cases over the knowledge pipeline."""

from __future__ import annotations

from backend.domain.authz_types import AuthorizationContext
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


def create_upload(
    *,
    file,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeUploadResponse:
    return create_knowledge_upload(
        file=file,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )


def get_upload_status(
    *,
    document_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeUploadStatusResponse:
    return get_knowledge_upload(
        document_id=document_id,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )


def start_ingestion(
    *,
    request: KnowledgeIngestionRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeIngestionResponse:
    return start_knowledge_ingestion(
        request=request,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )


def get_ingestion_status(
    *,
    ingestion_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeIngestionStatusResponse:
    return get_knowledge_ingestion_status(
        ingestion_id=ingestion_id,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )


def search(
    *,
    request: KnowledgeSearchRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeSearchResponse:
    return search_knowledge(
        request=request,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )


def answer(
    *,
    request: KnowledgeAnswerRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeAnswerResponse:
    return answer_with_knowledge(
        request=request,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
