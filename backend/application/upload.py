"""Upload analysis use cases over the knowledge pipeline."""

from __future__ import annotations

from collections.abc import Generator
from typing import Callable

from backend.domain.authz_types import AuthorizationContext
from backend.application.ports import (
    IdempotencyStore,
    KnowledgeValidationError,
    Settings,
    LLMClient,
)
from backend.application.exceptions import (
    UploadIdempotencyConflictError,
    UploadIdempotencyInProgressError,
)
from backend.models.upload import UploadAnalysisResponse
from backend.services.idempotency_service import (
    build_request_hash,
)
from backend.services.runtime_persistence import build_idempotency_store
from backend.services.knowledge_storage import SUPPORTED_KNOWLEDGE_EXTENSIONS
from backend.services.upload_service import (
    ingest_upload as _ingest_upload,
    stream_upload_analysis_sse as _stream_upload_analysis_sse,
)

IdempotencyStoreFactory = Callable[[Settings], IdempotencyStore]


def _validate_upload_input(*, filename: str, content: bytes) -> None:
    if not filename:
        raise KnowledgeValidationError("No filename provided.")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise KnowledgeValidationError(
            "Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX."
        )
    if not content:
        raise KnowledgeValidationError("Uploaded file is empty.")


def stream_upload_analysis(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    llm: LLMClient | None = None,
) -> Generator[str, None, None]:
    """Validate upload input and stream readiness metadata from the knowledge pipeline."""
    _validate_upload_input(filename=filename, content=content)
    return _stream_upload_analysis_sse(
        content=content,
        filename=filename,
        settings=settings,
        auth_context=auth_context,
        llm=llm,
    )


def ingest_upload(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    llm: LLMClient | None = None,
) -> UploadAnalysisResponse:
    """Compatibility wrapper for the underlying upload ingestion use case."""
    return _ingest_upload(
        content=content,
        filename=filename,
        settings=settings,
        auth_context=auth_context,
        llm=llm,
    )


def analyze_upload_json(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    idempotency_key: str | None = None,
    llm: LLMClient | None = None,
    ingest_upload_fn: Callable[..., UploadAnalysisResponse] = ingest_upload,
    idempotency_store_factory: IdempotencyStoreFactory | None = None,
) -> UploadAnalysisResponse:
    """Validate upload input, ingest the file, and return JSON readiness metadata."""
    _validate_upload_input(filename=filename, content=content)
    key = (idempotency_key or "").strip()
    scope = "upload_analyze_json"
    request_hash = build_request_hash(filename.encode("utf-8") + b"\x00" + content)
    store_factory = idempotency_store_factory or _default_idempotency_store_factory

    if key:
        store = store_factory(settings)
        claim = store.claim(
            key=key,
            route="/api/upload/analyze",
            scope=scope,
            request_hash=request_hash,
        )
        if claim.state == "conflict":
            raise UploadIdempotencyConflictError(
                "Idempotency-Key was already used with a different request payload."
            )
        if claim.state == "in_progress":
            raise UploadIdempotencyInProgressError(
                "A request with this Idempotency-Key is already in progress."
            )
        if claim.state == "replay" and claim.completed is not None:
            return UploadAnalysisResponse.model_validate_json(claim.completed.body)

    try:
        response_model = ingest_upload_fn(
            content=content,
            filename=filename,
            settings=settings,
            auth_context=auth_context,
            llm=llm,
        )
    except KnowledgeValidationError:
        if key:
            store.release_pending(
                key=key,
                route="/api/upload/analyze",
                scope=scope,
                request_hash=request_hash,
            )
        raise

    if key:
        store.store_completed(
            key=key,
            route="/api/upload/analyze",
            scope=scope,
            request_hash=request_hash,
            status_code=200,
            content_type="application/json",
            body=response_model.model_dump_json(),
        )
    return response_model


def _default_idempotency_store_factory(settings: Settings) -> IdempotencyStore:
    return build_idempotency_store(settings)
