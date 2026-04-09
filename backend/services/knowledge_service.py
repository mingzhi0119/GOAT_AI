from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from backend.domain.authz_types import AuthorizationContext
from backend.services.authorizer import (
    authorize_knowledge_document_read,
    authorize_knowledge_document_write,
)
from backend.domain.authorization import ResourceRef
from backend.models.knowledge import (
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    KnowledgeCitation,
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
    KnowledgeIngestionStatusResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
    KnowledgeUploadStatusResponse,
)
from backend.services.authz_audit import emit_authorization_audit
from backend.services.exceptions import (
    KnowledgeDocumentNotFound,
    KnowledgeValidationError,
)
from backend.services.retrieval_quality import (
    apply_rerank_hits,
    prepare_search_query,
    resolve_query_rewrite_enabled,
    resolve_rerank_mode,
)
from backend.services.knowledge_pipeline import (
    chunk_text,
    normalize_document,
    persist_normalized_text,
    persist_vector_index,
    search_vector_index,
)
from goat_ai.telemetry_counters import (
    inc_knowledge_query_rewrite_applied,
    inc_knowledge_retrieval,
)

from backend.services.knowledge_repository import (
    KnowledgeChunkRow,
    KnowledgeDocumentRecord,
    KnowledgeIngestionRecord,
    SQLiteKnowledgeRepository,
)
from backend.services.knowledge_storage import (
    KnowledgeValidationError as StorageValidationError,
    persist_knowledge_bytes,
)
from backend.types import AsyncUploadReader, Settings

_VECTOR_BACKEND = "simple_local_v1"
_MAX_READ_BYTES = 25 * 1024 * 1024
_CHAT_CONTEXT_SNIPPET_CHARS = 900
_CHAT_CONTEXT_TOTAL_CHARS = 5000


@dataclass(frozen=True)
class KnowledgeChatContext:
    """Bounded retrieval context for LLM-backed chat turns."""

    context_block: str
    citations: list[KnowledgeCitation]


def create_knowledge_upload(
    *,
    file: AsyncUploadReader,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeUploadResponse:
    """Persist a knowledge upload and register document metadata."""
    return create_knowledge_upload_from_bytes(
        content_type=file.content_type,
        filename=file.filename or "",
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
        content=_run_async_read(file=file),
    )


def create_knowledge_upload_from_bytes(
    *,
    content: bytes,
    filename: str,
    content_type: str | None,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeUploadResponse:
    """Persist a knowledge upload from already-read bytes and register document metadata."""
    document_id = f"doc-{uuid4().hex}"
    upload_id = f"upload-{uuid4().hex}"
    try:
        stored = persist_knowledge_bytes(
            content=content,
            filename=filename,
            content_type=content_type,
            settings=settings,
            document_id=document_id,
        )
    except StorageValidationError as exc:
        raise KnowledgeValidationError(str(exc)) from exc

    now = _now_iso()
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    repository.create_document(
        KnowledgeDocumentRecord(
            id=document_id,
            source_type="upload",
            original_filename=stored.filename,
            mime_type=stored.mime_type,
            sha256=stored.sha256,
            storage_path=str(stored.storage_path),
            byte_size=stored.byte_size,
            status="uploaded",
            created_at=now,
            updated_at=now,
            deleted_at=None,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
        )
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="knowledge.document.create",
        resource=ResourceRef(
            resource_type="knowledge_document", resource_id=document_id
        ),
        decision=authorize_knowledge_document_write(
            ctx=auth_context,
            document=repository.get_document(document_id)
            or KnowledgeDocumentRecord(
                id=document_id,
                source_type="upload",
                original_filename=stored.filename,
                mime_type=stored.mime_type,
                sha256=stored.sha256,
                storage_path=str(stored.storage_path),
                byte_size=stored.byte_size,
                status="uploaded",
                created_at=now,
                updated_at=now,
                deleted_at=None,
                owner_id=auth_context.legacy_owner_id,
                tenant_id=auth_context.tenant_id.value,
                principal_id=auth_context.principal_id.value,
            ),
            require_owner_header=settings.require_session_owner,
        ),
        request_id=request_id,
    )
    return KnowledgeUploadResponse(
        upload_id=upload_id,
        document_id=document_id,
        status="uploaded",
        filename=stored.filename,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
    )


def get_knowledge_upload(
    *,
    document_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeUploadStatusResponse:
    """Lookup one persisted uploaded knowledge document."""
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    document = repository.get_document(document_id)
    if document is None:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")
    decision = authorize_knowledge_document_read(
        ctx=auth_context,
        document=document,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="knowledge.document.read",
        resource=ResourceRef(
            resource_type="knowledge_document", resource_id=document_id
        ),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")
    status = (
        "indexed"
        if _document_has_completed_ingestion(document_id=document_id, settings=settings)
        else "uploaded"
    )
    return KnowledgeUploadStatusResponse(
        upload_id=document_id,
        document_id=document.id,
        status=status,
        filename=document.original_filename,
        mime_type=document.mime_type,
        byte_size=document.byte_size,
    )


def start_knowledge_ingestion(
    *,
    request: KnowledgeIngestionRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeIngestionResponse:
    """Normalize, chunk, and index one persisted knowledge document."""
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    document = repository.get_document(request.document_id)
    if document is None:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")
    decision = authorize_knowledge_document_write(
        ctx=auth_context,
        document=document,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="knowledge.ingestion.start",
        resource=ResourceRef(
            resource_type="knowledge_document", resource_id=request.document_id
        ),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")

    now = _now_iso()
    ingestion_id = f"ing-{uuid4().hex}"
    repository.create_ingestion(
        KnowledgeIngestionRecord(
            id=ingestion_id,
            document_id=document.id,
            status="running",
            parser_profile=request.parser_profile,
            chunking_profile=request.chunking_profile,
            embedding_profile=request.embedding_profile,
            vector_backend=_VECTOR_BACKEND,
            started_at=now,
            completed_at=None,
            error_code=None,
            error_detail=None,
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
    )

    try:
        normalized_text = normalize_document(
            settings=settings,
            document_id=document.id,
            filename=document.original_filename,
        )
        persist_normalized_text(
            settings=settings, document_id=document.id, text=normalized_text
        )
        chunks = chunk_text(normalized_text)
        vector_ref = persist_vector_index(
            settings=settings,
            document_id=document.id,
            filename=document.original_filename,
            chunks=chunks,
            backend_name=_VECTOR_BACKEND,
        )
        repository.replace_chunks(
            ingestion_id=ingestion_id,
            document_id=document.id,
            chunks=[
                KnowledgeChunkRow(
                    id=f"chunk-{uuid4().hex}",
                    ingestion_id=ingestion_id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    text_content=chunk.text,
                    text_hash=hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    token_count=len(chunk.text.split()),
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    vector_ref=f"{vector_ref}#{chunk.chunk_index}",
                    created_at=now,
                )
                for chunk in chunks
            ],
        )
        repository.update_ingestion_status(
            ingestion_id=ingestion_id,
            status="completed",
            updated_at=_now_iso(),
            chunk_count=len(chunks),
            completed_at=_now_iso(),
        )
    except Exception as exc:
        repository.update_ingestion_status(
            ingestion_id=ingestion_id,
            status="failed",
            updated_at=_now_iso(),
            error_code="KNOWLEDGE_INGESTION_FAILED",
            error_detail=str(exc),
        )
        raise

    return KnowledgeIngestionResponse(
        ingestion_id=ingestion_id,
        document_id=document.id,
        status="completed",
    )


def get_knowledge_ingestion_status(
    *,
    ingestion_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeIngestionStatusResponse:
    """Lookup one ingestion attempt."""
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    ingestion = repository.get_ingestion(ingestion_id)
    if ingestion is None:
        raise KnowledgeDocumentNotFound("Knowledge ingestion not found.")
    document = repository.get_document(ingestion.document_id)
    if document is None:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")
    decision = authorize_knowledge_document_read(
        ctx=auth_context,
        document=document,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="knowledge.ingestion.read",
        resource=ResourceRef(
            resource_type="knowledge_ingestion", resource_id=ingestion_id
        ),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise KnowledgeDocumentNotFound("Knowledge ingestion not found.")
    return KnowledgeIngestionStatusResponse(
        ingestion_id=ingestion.id,
        document_id=ingestion.document_id,
        status=ingestion.status,
        chunk_count=ingestion.chunk_count,
        error_code=ingestion.error_code,
        error_detail=ingestion.error_detail,
    )


def search_knowledge(
    *,
    request: KnowledgeSearchRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeSearchResponse:
    """Search indexed chunks using the local simple vector backend."""
    rewrite_enabled = resolve_query_rewrite_enabled(
        retrieval_profile=request.retrieval_profile
    )
    effective_query = prepare_search_query(
        original_query=request.query, rewrite_enabled=rewrite_enabled
    )
    mode = resolve_rerank_mode(
        retrieval_profile=request.retrieval_profile, settings=settings
    )
    allowed_document_ids = _authorized_document_ids_for_request(
        requested_document_ids=request.document_ids,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
        action="knowledge.search",
    )
    hits = search_vector_index(
        settings=settings,
        backend_name=_VECTOR_BACKEND,
        query=effective_query,
        document_filters=allowed_document_ids,
    )
    ranked = apply_rerank_hits(query=effective_query, mode=mode, hits=hits)
    effective_out: str | None = (
        effective_query if effective_query != request.query else None
    )
    top = ranked[: request.top_k]
    inc_knowledge_retrieval(
        retrieval_profile=request.retrieval_profile,
        outcome="hit" if top else "miss",
    )
    if rewrite_enabled and effective_out is not None:
        inc_knowledge_query_rewrite_applied(retrieval_profile=request.retrieval_profile)
    return KnowledgeSearchResponse(
        query=request.query,
        effective_query=effective_out,
        hits=[
            KnowledgeCitation(
                document_id=hit.document_id,
                chunk_id=hit.chunk_id,
                filename=hit.filename,
                snippet=hit.snippet,
                score=hit.score,
            )
            for hit in top
        ],
    )


def answer_with_knowledge(
    *,
    request: KnowledgeAnswerRequest,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeAnswerResponse:
    """Return a deterministic retrieval-backed answer with citations."""
    search_response = search_knowledge(
        request=KnowledgeSearchRequest(
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
            retrieval_profile="default",
        ),
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    if not search_response.hits and request.document_ids:
        search_response = _fallback_answer_scope(
            document_ids=request.document_ids,
            query=request.query,
            top_k=request.top_k,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    if not search_response.hits:
        return KnowledgeAnswerResponse(
            answer="No relevant context found in the indexed knowledge base.",
            citations=[],
        )

    bullets = [
        f"- {citation.filename}: {citation.snippet[:220].strip()}"
        for citation in search_response.hits
    ]
    answer = "Relevant retrieved context:\n" + "\n".join(bullets)
    return KnowledgeAnswerResponse(answer=answer, citations=search_response.hits)


def build_chat_knowledge_context(
    *,
    query: str,
    document_ids: list[str],
    top_k: int,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeChatContext:
    """Build a bounded retrieval context block for RAG chat."""
    search_response = search_knowledge(
        request=KnowledgeSearchRequest(
            query=query,
            document_ids=document_ids,
            top_k=top_k,
            retrieval_profile="default",
        ),
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    if not search_response.hits and document_ids:
        search_response = _fallback_answer_scope(
            document_ids=document_ids,
            query=query,
            top_k=top_k,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    if not search_response.hits:
        return KnowledgeChatContext(context_block="", citations=[])

    context_sections: list[str] = []
    used_chars = 0
    citations: list[KnowledgeCitation] = []
    for index, citation in enumerate(search_response.hits, start=1):
        snippet = citation.snippet.strip()
        if not snippet:
            continue
        bounded = snippet[:_CHAT_CONTEXT_SNIPPET_CHARS].strip()
        block = (
            f"[Source {index}] filename={citation.filename} score={citation.score:.3f}\n"
            f"{bounded}"
        )
        projected = used_chars + len(block) + 2
        if context_sections and projected > _CHAT_CONTEXT_TOTAL_CHARS:
            break
        context_sections.append(block)
        citations.append(citation)
        used_chars = projected

    return KnowledgeChatContext(
        context_block="\n\n".join(context_sections),
        citations=citations,
    )


def resolve_knowledge_documents(
    *,
    document_ids: list[str],
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> list[KnowledgeDocumentRecord]:
    """Return persisted knowledge documents in caller order or raise when any are missing."""
    if not document_ids:
        return []
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    deduped_ids = list(dict.fromkeys(document_ids))
    documents = repository.list_documents(deduped_ids)
    documents_by_id = {document.id: document for document in documents}
    missing = [
        document_id for document_id in deduped_ids if document_id not in documents_by_id
    ]
    if missing:
        raise KnowledgeDocumentNotFound("Knowledge document not found.")
    resolved = [documents_by_id[document_id] for document_id in deduped_ids]
    for document in resolved:
        decision = authorize_knowledge_document_read(
            ctx=auth_context,
            document=document,
            require_owner_header=settings.require_session_owner,
        )
        emit_authorization_audit(
            ctx=auth_context,
            action="knowledge.document.resolve",
            resource=ResourceRef(
                resource_type="knowledge_document", resource_id=document.id
            ),
            decision=decision,
            request_id=request_id,
        )
        if not decision.allowed:
            raise KnowledgeDocumentNotFound("Knowledge document not found.")
    return resolved


def _fallback_answer_scope(
    *,
    document_ids: list[str],
    query: str,
    top_k: int,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> KnowledgeSearchResponse:
    """Fallback to attached-document leading chunks when lexical retrieval finds nothing."""
    documents = resolve_knowledge_documents(
        document_ids=document_ids,
        settings=settings,
        auth_context=auth_context,
        request_id=request_id,
    )
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    chunks = repository.get_chunks_for_documents(document_ids)
    chunks_by_document: dict[str, KnowledgeChunkRow] = {}
    for chunk in chunks:
        chunks_by_document.setdefault(chunk.document_id, chunk)
    hits: list[KnowledgeCitation] = []
    for rank, document in enumerate(documents):
        chunk = chunks_by_document.get(document.id)
        if chunk is None:
            continue
        hits.append(
            KnowledgeCitation(
                document_id=document.id,
                chunk_id=chunk.vector_ref,
                filename=document.original_filename,
                snippet=chunk.text_content[:400],
                score=max(0.01, 1.0 - (rank * 0.05)),
            )
        )
        if len(hits) >= top_k:
            break
    return KnowledgeSearchResponse(query=query, hits=hits)


def _run_async_read(*, file: AsyncUploadReader) -> bytes:
    import asyncio

    return asyncio.run(file.read(_MAX_READ_BYTES))


def _document_has_completed_ingestion(*, document_id: str, settings: Settings) -> bool:
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    chunks = repository.get_chunks_for_documents([document_id])
    return bool(chunks)


def _authorized_document_ids_for_request(
    *,
    requested_document_ids: list[str],
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
    action: str,
) -> list[str]:
    repository = SQLiteKnowledgeRepository(settings.log_db_path)
    if requested_document_ids:
        documents = repository.list_documents(
            list(dict.fromkeys(requested_document_ids))
        )
    else:
        documents = repository.list_documents_for_tenant(auth_context.tenant_id.value)
    allowed_ids: list[str] = []
    for document in documents:
        decision = authorize_knowledge_document_read(
            ctx=auth_context,
            document=document,
            require_owner_header=settings.require_session_owner,
        )
        emit_authorization_audit(
            ctx=auth_context,
            action=action,
            resource=ResourceRef(
                resource_type="knowledge_document", resource_id=document.id
            ),
            decision=decision,
            request_id=request_id,
        )
        if decision.allowed:
            allowed_ids.append(document.id)
    return allowed_ids


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
