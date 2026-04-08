"""POST /api/chat — streaming chat completion via Server-Sent Events."""
from __future__ import annotations

import json
import logging
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.dependencies import (
    get_conversation_logger,
    get_llm_client,
    get_safeguard_service,
    get_session_repository,
    get_tabular_context_extractor,
    get_title_generator,
)
from backend.models.common import ErrorResponse
from backend.models.chat import ChatRequest
from backend.routers.chat_options import ollama_options_from_chat_request
from backend.services.chat_capacity_service import ChatCapacityError, validate_chat_capacity
from backend.services.chat_message_merge import merge_request_image_attachments
from backend.services.idempotency_service import SQLiteIdempotencyStore, build_request_hash
from backend.services.chat_service import stream_chat_sse
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator
from backend.services.media_service import load_images_base64_for_chat
from backend.services.exceptions import VisionNotSupported
from backend.services.tabular_context import TabularContextExtractor
from backend.services.safeguard_service import SafeguardService
from backend.types import LLMClient, OllamaUnavailable, Settings

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # Disable nginx response buffering
    "Connection": "keep-alive",
}


def _idempotency_request_bytes(req: ChatRequest, user_name: str) -> bytes:
    payload = {
        "body": req.model_dump(mode="json"),
        "user_name": user_name,
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


@router.post(
    "/chat",
    summary="Stream a chat completion over SSE",
    responses={
        200: {"content": {"text/event-stream": {}}},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def chat_stream(
    request: Request,
    req: ChatRequest,
    llm: LLMClient = Depends(get_llm_client),
    conversation_logger: ConversationLogger = Depends(get_conversation_logger),
    session_repository: SessionRepository = Depends(get_session_repository),
    title_generator: TitleGenerator = Depends(get_title_generator),
    tabular_extractor: TabularContextExtractor = Depends(get_tabular_context_extractor),
    safeguard_service: SafeguardService = Depends(get_safeguard_service),
    settings: Settings = Depends(get_settings),
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    """Stream an LLM response as Server-Sent Events.

    Each SSE event carries a typed JSON object.
    The final event is ``{"type":"done"}``.
    The client reads events with the native ``EventSource`` API or a fetch+ReadableStream.
    """
    client_ip: str = request.client.host if request.client else "unknown"
    user_name: str = request.headers.get("x-user-name", "").strip()
    idempotency_key = (idempotency_key_header or "").strip()
    try:
        validate_chat_capacity(req=req, settings=settings)
    except ChatCapacityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if req.knowledge_document_ids and req.image_attachment_ids:
        raise HTTPException(
            status_code=422,
            detail="Cannot combine knowledge retrieval and image attachments in one request.",
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
            logger.warning("Ollama unreachable during vision capability check: %s", exc)
            raise HTTPException(status_code=503, detail="AI backend unavailable") from exc
        if "vision" not in caps:
            raise VisionNotSupported()

    o_opts = ollama_options_from_chat_request(req)

    source_stream = stream_chat_sse(
        llm=llm,
        model=req.model,
        messages=merged_messages,
        system_prompt=settings.system_prompt,
        ip=client_ip,
        conversation_logger=conversation_logger,
        user_name=user_name,
        session_id=req.session_id,
        all_messages=merged_messages,
        session_repository=session_repository,
        title_generator=title_generator,
        safeguard_service=safeguard_service,
        system_instruction=(req.system_instruction or "").strip(),
        ollama_options=o_opts,
        tabular_extractor=tabular_extractor,
        settings=settings,
        knowledge_document_ids=req.knowledge_document_ids,
        vision_last_user_images_base64=vision_b64,
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
