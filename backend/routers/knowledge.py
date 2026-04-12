from __future__ import annotations

from fastapi import APIRouter, Depends, Request, UploadFile

from backend.domain.authz_types import AuthorizationContext
from backend.application.knowledge import (
    answer,
    create_upload,
    get_ingestion_status,
    get_upload_status,
    search,
    start_ingestion,
)
from backend.application.ports import (
    KnowledgeDocumentNotFound,
    KnowledgeValidationError,
    Settings,
)
from backend.platform.config import get_settings
from backend.platform.dependencies import get_authorization_context
from backend.models.common import ErrorResponse
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

router = APIRouter()


def _raise_not_found(exc: KnowledgeDocumentNotFound) -> None:
    raise exc


def _raise_bad_request(exc: KnowledgeValidationError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/knowledge/uploads",
    response_model=KnowledgeUploadResponse,
    summary="Register a knowledge file upload",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def post_knowledge_upload(
    file: UploadFile,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeUploadResponse:
    """Persist a knowledge upload and register document metadata."""
    try:
        return create_upload(
            file=file,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except KnowledgeValidationError as exc:
        _raise_bad_request(exc)


@router.get(
    "/knowledge/uploads/{document_id}",
    response_model=KnowledgeUploadStatusResponse,
    summary="Read one persisted knowledge upload",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def get_knowledge_upload_status(
    document_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeUploadStatusResponse:
    """Return metadata for one persisted knowledge upload."""
    try:
        return get_upload_status(
            document_id=document_id,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except KnowledgeDocumentNotFound as exc:
        _raise_not_found(exc)


@router.post(
    "/knowledge/ingestions",
    response_model=KnowledgeIngestionResponse,
    summary="Start a knowledge ingestion job",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def post_knowledge_ingestion(
    request: KnowledgeIngestionRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeIngestionResponse:
    """Start a knowledge ingestion job for one uploaded document."""
    try:
        return start_ingestion(
            request=request,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(http_request.state, "request_id", ""),
        )
    except KnowledgeDocumentNotFound as exc:
        _raise_not_found(exc)
    except KnowledgeValidationError as exc:
        _raise_bad_request(exc)


@router.get(
    "/knowledge/ingestions/{ingestion_id}",
    response_model=KnowledgeIngestionStatusResponse,
    summary="Read one knowledge ingestion job",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def get_knowledge_ingestion(
    ingestion_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeIngestionStatusResponse:
    """Return status for one ingestion attempt."""
    try:
        return get_ingestion_status(
            ingestion_id=ingestion_id,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(request.state, "request_id", ""),
        )
    except KnowledgeDocumentNotFound as exc:
        _raise_not_found(exc)


@router.post(
    "/knowledge/search",
    response_model=KnowledgeSearchResponse,
    summary="Search indexed knowledge chunks",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def post_knowledge_search(
    request: KnowledgeSearchRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeSearchResponse:
    """Run pure retrieval against indexed knowledge chunks."""
    try:
        return search(
            request=request,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(http_request.state, "request_id", ""),
        )
    except KnowledgeValidationError as exc:
        _raise_bad_request(exc)


@router.post(
    "/knowledge/answers",
    response_model=KnowledgeAnswerResponse,
    summary="Generate a retrieval-backed answer",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def post_knowledge_answer(
    request: KnowledgeAnswerRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> KnowledgeAnswerResponse:
    """Return a retrieval-backed answer with citations."""
    try:
        return answer(
            request=request,
            settings=settings,
            auth_context=auth_context,
            request_id=getattr(http_request.state, "request_id", ""),
        )
    except KnowledgeValidationError as exc:
        _raise_bad_request(exc)
