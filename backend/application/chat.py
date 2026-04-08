"""Chat request preflight and request-shape normalization."""
from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Generator

from fastapi.responses import StreamingResponse

from backend.application.ports import (
    ConversationLogger,
    LLMClient,
    OllamaUnavailable,
    SafeguardService,
    SessionRepository,
    Settings,
    TabularContextExtractor,
    TitleGenerator,
    VisionNotSupported,
    validate_chat_capacity,
)
from backend.application.exceptions import (
    ChatIdempotencyConflictError,
    ChatIdempotencyInProgressError,
    ChatKnowledgeImageConflictError,
    ChatOwnerRequiredError,
)
from backend.models.chat import ChatMessage, ChatRequest
from backend.services.chat_message_merge import merge_request_image_attachments
from backend.services.idempotency_service import SQLiteIdempotencyStore, build_request_hash
from backend.services.media_service import load_images_base64_for_chat
from backend.services.chat_service import stream_chat_sse

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # Disable nginx response buffering
    "Connection": "keep-alive",
}


@dataclass(frozen=True)
class PreparedChatRequest:
    """Normalized chat request state produced by application preflight."""

    merged_messages: list[ChatMessage]
    session_owner_id: str
    vision_last_user_images_base64: list[str] | None
    ollama_options: dict[str, float | int] | None


def _build_ollama_options(req: ChatRequest) -> dict[str, float | int] | None:
    opts: dict[str, float | int] = {}
    if req.temperature is not None:
        opts["temperature"] = req.temperature
    if req.max_tokens is not None:
        opts["num_predict"] = req.max_tokens
    if req.top_p is not None:
        opts["top_p"] = req.top_p
    return opts if opts else None


def prepare_chat_request(
    *,
    req: ChatRequest,
    settings: Settings,
    llm: LLMClient,
    session_owner_id: str,
) -> PreparedChatRequest:
    """Validate chat request constraints and resolve derived request state."""
    validate_chat_capacity(req=req, settings=settings)
    if req.knowledge_document_ids and req.image_attachment_ids:
        raise ChatKnowledgeImageConflictError(
            "Cannot combine knowledge retrieval and image attachments in one request."
        )
    if settings.require_session_owner and not session_owner_id:
        raise ChatOwnerRequiredError(
            "X-GOAT-Owner-Id is required when GOAT_REQUIRE_SESSION_OWNER is enabled."
        )

    merged_messages = merge_request_image_attachments(req)
    vision_b64: list[str] | None = None
    if req.image_attachment_ids:
        if not settings.use_chat_api:
            raise VisionNotSupported("Vision chat requires GOAT_USE_CHAT_API=true.")
        vision_b64 = load_images_base64_for_chat(
            attachment_ids=req.image_attachment_ids,
            settings=settings,
        )
        try:
            caps = llm.get_model_capabilities(req.model)
        except OllamaUnavailable as exc:
            raise OllamaUnavailable("AI backend unavailable") from exc
        if "vision" not in caps:
            raise VisionNotSupported()

    return PreparedChatRequest(
        merged_messages=merged_messages,
        session_owner_id=session_owner_id,
        vision_last_user_images_base64=vision_b64,
        ollama_options=_build_ollama_options(req),
    )


def _idempotency_request_bytes(req: ChatRequest, user_name: str) -> bytes:
    payload = {
        "body": req.model_dump(mode="json"),
        "user_name": user_name,
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def stream_chat_response(
    *,
    req: ChatRequest,
    prepared: PreparedChatRequest,
    client_ip: str,
    user_name: str,
    llm: LLMClient,
    conversation_logger: ConversationLogger,
    session_repository: SessionRepository,
    title_generator: TitleGenerator,
    tabular_extractor: TabularContextExtractor,
    safeguard_service: SafeguardService,
    settings: Settings,
    idempotency_key: str,
) -> StreamingResponse:
    """Build the SSE response for chat, including optional idempotency replay."""
    source_stream = stream_chat_sse(
        llm=llm,
        model=req.model,
        messages=prepared.merged_messages,
        system_prompt=settings.system_prompt,
        ip=client_ip,
        conversation_logger=conversation_logger,
        user_name=user_name,
        session_id=req.session_id,
        all_messages=prepared.merged_messages,
        session_repository=session_repository,
        title_generator=title_generator,
        safeguard_service=safeguard_service,
        system_instruction=(req.system_instruction or "").strip(),
        ollama_options=prepared.ollama_options,
        tabular_extractor=tabular_extractor,
        settings=settings,
        knowledge_document_ids=req.knowledge_document_ids,
        vision_last_user_images_base64=prepared.vision_last_user_images_base64,
        session_owner_id=prepared.session_owner_id,
    )

    if not idempotency_key or not req.session_id:
        return StreamingResponse(
            source_stream,
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    store = SQLiteIdempotencyStore(
        db_path=settings.log_db_path,
        ttl_sec=settings.idempotency_ttl_sec,
    )
    idempotency_route = "/api/chat"
    idempotency_scope = f"session_append:{req.session_id}"
    request_hash = build_request_hash(_idempotency_request_bytes(req, user_name))
    claim = store.claim(
        key=idempotency_key,
        route=idempotency_route,
        scope=idempotency_scope,
        request_hash=request_hash,
    )
    if claim.state == "conflict":
        raise ChatIdempotencyConflictError(
            "Idempotency-Key was already used with a different request payload."
        )
    if claim.state == "in_progress":
        raise ChatIdempotencyInProgressError(
            "A request with this Idempotency-Key is already in progress."
        )
    if claim.state == "replay" and claim.completed is not None:
        return StreamingResponse(
            iter([claim.completed.body]),
            media_type=claim.completed.content_type or "text/event-stream",
            headers=_SSE_HEADERS,
        )

    def _capture_and_store() -> Generator[str, None, None]:
        chunks: list[str] = []
        saw_done = False
        try:
            for chunk in source_stream:
                chunks.append(chunk)
                if '"type": "done"' in chunk:
                    saw_done = True
                yield chunk
        except BaseException:
            store.release_pending(
                key=idempotency_key,
                route=idempotency_route,
                scope=idempotency_scope,
                request_hash=request_hash,
            )
            raise
        if saw_done:
            store.store_completed(
                key=idempotency_key,
                route=idempotency_route,
                scope=idempotency_scope,
                request_hash=request_hash,
                status_code=200,
                content_type="text/event-stream",
                body="".join(chunks),
            )
            return
        store.release_pending(
            key=idempotency_key,
            route=idempotency_route,
            scope=idempotency_scope,
            request_hash=request_hash,
        )

    return StreamingResponse(
        _capture_and_store(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
