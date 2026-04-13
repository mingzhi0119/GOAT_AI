"""Public entry for chat streaming, including knowledge-backed RAG answers."""

from __future__ import annotations

from collections.abc import Generator

from backend.domain.authz_types import AuthorizationContext
from backend.models.chat import ChatMessage
from backend.services.chat_knowledge_flow import (
    build_chat_stream_identity,
    stream_knowledge_chat_sse,
)
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)
from backend.services.chat_stream_service import ChatStreamService
from backend.services.safeguard_service import SafeguardService
from backend.services.tabular_context import TabularContextExtractor
from backend.types import Settings
from goat_ai.shared.clocks import Clock
from goat_ai.llm.ollama_client import LLMClient


def stream_chat_sse(
    *,
    llm: LLMClient,
    model: str,
    messages: list[ChatMessage],
    system_prompt: str,
    ip: str,
    conversation_logger: ConversationLogger,
    user_name: str = "",
    session_id: str | None = None,
    all_messages: list[ChatMessage] | None = None,
    session_repository: SessionRepository | None = None,
    title_generator: TitleGenerator | None = None,
    safeguard_service: SafeguardService | None = None,
    system_instruction: str = "",
    plan_mode: bool = False,
    ollama_options: dict[str, float | int | bool | str] | None = None,
    tabular_extractor: TabularContextExtractor | None = None,
    settings: Settings | None = None,
    knowledge_document_ids: list[str] | None = None,
    vision_last_user_images_base64: list[str] | None = None,
    session_owner_id: str = "",
    auth_context: AuthorizationContext | None = None,
    request_id: str = "",
    clock: Clock | None = None,
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion."""
    if knowledge_document_ids and settings is not None:
        yield from stream_knowledge_chat_sse(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            ip=ip,
            conversation_logger=conversation_logger,
            user_name=user_name,
            session_id=session_id,
            all_messages=all_messages,
            session_repository=session_repository,
            title_generator=title_generator,
            safeguard_service=safeguard_service,
            system_instruction=system_instruction,
            plan_mode=plan_mode,
            ollama_options=ollama_options,
            tabular_extractor=tabular_extractor,
            settings=settings,
            knowledge_document_ids=knowledge_document_ids,
            llm=llm,
            session_owner_id=session_owner_id,
            auth_context=auth_context,
            request_id=request_id,
            clock=clock,
        )
        return

    tenant_id, principal_id = build_chat_stream_identity(auth_context)
    yield from ChatStreamService(clock=clock).stream(
        llm=llm,
        model=model,
        messages=messages,
        system_prompt=system_prompt,
        ip=ip,
        conversation_logger=conversation_logger,
        user_name=user_name,
        session_id=session_id,
        all_messages=all_messages,
        session_repository=session_repository,
        title_generator=title_generator,
        safeguard_service=safeguard_service,
        system_instruction=system_instruction,
        plan_mode=plan_mode,
        ollama_options=ollama_options,
        tabular_extractor=tabular_extractor,
        vision_last_user_images_base64=vision_last_user_images_base64,
        settings=settings,
        session_owner_id=session_owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_context=auth_context,
        request_id=request_id,
    )


__all__ = ["stream_chat_sse"]
