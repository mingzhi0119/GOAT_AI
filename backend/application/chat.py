"""Chat request preflight and request-shape normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Generator, Iterable
from typing import Callable

from backend.domain.authz_types import AuthorizationContext
from fastapi.responses import StreamingResponse
from goat_ai.config import default_system_prompt_for_theme

from backend.application.ports import (
    ConversationLogger,
    LLMClient,
    OllamaUnavailable,
    SafeguardService,
    SessionRepository,
    Settings,
    TabularContextExtractor,
    TitleGenerator,
    IdempotencyStore,
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
from backend.services.idempotency_service import (
    build_request_hash,
    SQLiteIdempotencyStore,
)
from backend.services.media_service import load_images_base64_for_chat
from backend.services.chat_service import stream_chat_sse

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # Disable nginx response buffering
    "Connection": "keep-alive",
}


def _resolve_base_system_prompt(req: ChatRequest, settings: Settings) -> str:
    if settings.system_prompt_overridden:
        return settings.system_prompt
    return default_system_prompt_for_theme(req.theme_style)


@dataclass(frozen=True)
class PreparedChatRequest:
    """Normalized chat request state produced by application preflight."""

    merged_messages: list[ChatMessage]
    session_owner_id: str
    auth_context: AuthorizationContext
    vision_last_user_images_base64: list[str] | None
    ollama_options: dict[str, float | int | bool | str] | None
    plan_mode: bool


@dataclass(frozen=True)
class ChatIdempotencyContext:
    """Resolved idempotency scope for a session append request."""

    store: IdempotencyStore
    key: str
    route: str
    scope: str
    request_hash: str


IdempotencyStoreFactory = Callable[[Settings], IdempotencyStore]


def _build_ollama_options(
    req: ChatRequest,
) -> dict[str, float | int | bool | str] | None:
    opts: dict[str, float | int | bool | str] = {}
    if req.temperature is not None:
        opts["temperature"] = req.temperature
    if req.max_tokens is not None:
        opts["num_predict"] = req.max_tokens
    if req.top_p is not None:
        opts["top_p"] = req.top_p
    if req.think is not None:
        opts["think"] = req.think
    return opts if opts else None


def prepare_chat_request(
    *,
    req: ChatRequest,
    settings: Settings,
    llm: LLMClient,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> PreparedChatRequest:
    """Validate chat request constraints and resolve derived request state."""
    session_owner_id = auth_context.legacy_owner_id
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
            auth_context=auth_context,
            request_id=request_id,
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
        auth_context=auth_context,
        vision_last_user_images_base64=vision_b64,
        ollama_options=_build_ollama_options(req),
        plan_mode=req.plan_mode,
    )


def _idempotency_request_bytes(req: ChatRequest, user_name: str) -> bytes:
    payload = {
        "body": req.model_dump(mode="json"),
        "user_name": user_name,
    }
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return text.encode("utf-8")


def _streaming_sse_response(
    stream: Iterable[str],
    *,
    content_type: str = "text/event-stream",
) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers=_SSE_HEADERS,
    )


def _build_source_stream(
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
    safeguard_service: SafeguardService | None,
    settings: Settings,
    request_id: str,
) -> Generator[str, None, None]:
    return stream_chat_sse(
        llm=llm,
        model=req.model,
        messages=prepared.merged_messages,
        system_prompt=_resolve_base_system_prompt(req, settings),
        ip=client_ip,
        conversation_logger=conversation_logger,
        user_name=user_name,
        session_id=req.session_id,
        all_messages=prepared.merged_messages,
        session_repository=session_repository,
        title_generator=title_generator,
        safeguard_service=safeguard_service,
        system_instruction=(req.system_instruction or "").strip(),
        plan_mode=prepared.plan_mode,
        ollama_options=prepared.ollama_options,
        tabular_extractor=tabular_extractor,
        settings=settings,
        knowledge_document_ids=req.knowledge_document_ids,
        vision_last_user_images_base64=prepared.vision_last_user_images_base64,
        session_owner_id=prepared.session_owner_id,
        auth_context=prepared.auth_context,
        request_id=request_id,
    )


def _build_idempotency_context(
    *,
    req: ChatRequest,
    user_name: str,
    settings: Settings,
    idempotency_key: str,
    idempotency_store_factory: IdempotencyStoreFactory | None = None,
) -> ChatIdempotencyContext | None:
    if not idempotency_key or not req.session_id:
        return None
    store_factory = idempotency_store_factory or _default_idempotency_store_factory

    return ChatIdempotencyContext(
        store=store_factory(settings),
        key=idempotency_key,
        route="/api/chat",
        scope=f"session_append:{req.session_id}",
        request_hash=build_request_hash(_idempotency_request_bytes(req, user_name)),
    )


def _default_idempotency_store_factory(settings: Settings) -> IdempotencyStore:
    return SQLiteIdempotencyStore(
        db_path=settings.log_db_path,
        ttl_sec=settings.idempotency_ttl_sec,
    )


def _claim_or_replay_idempotent_stream(
    context: ChatIdempotencyContext,
) -> StreamingResponse | None:
    claim = context.store.claim(
        key=context.key,
        route=context.route,
        scope=context.scope,
        request_hash=context.request_hash,
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
        return _streaming_sse_response(
            iter([claim.completed.body]),
            content_type=claim.completed.content_type or "text/event-stream",
        )
    return None


def _release_pending_claim(context: ChatIdempotencyContext) -> None:
    context.store.release_pending(
        key=context.key,
        route=context.route,
        scope=context.scope,
        request_hash=context.request_hash,
    )


def _store_completed_stream(
    context: ChatIdempotencyContext,
    *,
    body: str,
) -> None:
    context.store.store_completed(
        key=context.key,
        route=context.route,
        scope=context.scope,
        request_hash=context.request_hash,
        status_code=200,
        content_type="text/event-stream",
        body=body,
    )


def _capture_idempotent_stream(
    source_stream: Generator[str, None, None],
    *,
    context: ChatIdempotencyContext,
) -> Generator[str, None, None]:
    chunks: list[str] = []
    saw_done = False
    try:
        for chunk in source_stream:
            chunks.append(chunk)
            if '"type": "done"' in chunk:
                saw_done = True
            yield chunk
    except BaseException:
        _release_pending_claim(context)
        raise

    if saw_done:
        _store_completed_stream(context, body="".join(chunks))
        return

    _release_pending_claim(context)


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
    safeguard_service: SafeguardService | None,
    settings: Settings,
    idempotency_key: str,
    request_id: str = "",
) -> StreamingResponse:
    """Build the SSE response for chat, including optional idempotency replay."""
    source_stream = _build_source_stream(
        req=req,
        prepared=prepared,
        client_ip=client_ip,
        user_name=user_name,
        llm=llm,
        conversation_logger=conversation_logger,
        session_repository=session_repository,
        title_generator=title_generator,
        tabular_extractor=tabular_extractor,
        safeguard_service=safeguard_service,
        settings=settings,
        request_id=request_id,
    )

    context = _build_idempotency_context(
        req=req,
        user_name=user_name,
        settings=settings,
        idempotency_key=idempotency_key,
    )
    if context is None:
        return _streaming_sse_response(source_stream)

    replay_response = _claim_or_replay_idempotent_stream(context)
    if replay_response is not None:
        return replay_response

    return _streaming_sse_response(
        _capture_idempotent_stream(source_stream, context=context)
    )
