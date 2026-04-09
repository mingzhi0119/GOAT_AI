"""Public entry for chat streaming, including knowledge-backed RAG answers."""

from __future__ import annotations

import time
from collections.abc import Generator

from backend.domain.authz_types import AuthorizationContext
from backend.models.chat import ChatMessage
from backend.services.chat_orchestration import SessionPersistenceService
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)
from backend.services.chat_stream_service import ChatStreamService
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.knowledge_service import (
    build_chat_knowledge_context,
    resolve_knowledge_documents,
)
from backend.services.safeguard_service import SafeguardService
from backend.services.session_service import last_user_message
from backend.services.sse import sse_done_event, sse_error_event
from backend.services.tabular_context import TabularContextExtractor
from backend.types import Settings
from goat_ai.clocks import Clock
from goat_ai.ollama_client import LLMClient


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
    ollama_options: dict[str, float | int] | None = None,
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
        yield from _stream_knowledge_chat_sse(
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
        ollama_options=ollama_options,
        tabular_extractor=tabular_extractor,
        vision_last_user_images_base64=vision_last_user_images_base64,
        settings=settings,
        session_owner_id=session_owner_id,
        tenant_id=auth_context.tenant_id.value
        if auth_context is not None
        else "tenant:default",
        principal_id=auth_context.principal_id.value
        if auth_context is not None
        else "",
        auth_context=auth_context,
        request_id=request_id,
    )


def _stream_knowledge_chat_sse(
    *,
    llm: LLMClient,
    model: str,
    messages: list[ChatMessage],
    system_prompt: str,
    ip: str,
    conversation_logger: ConversationLogger,
    user_name: str,
    session_id: str | None,
    all_messages: list[ChatMessage] | None,
    session_repository: SessionRepository | None,
    title_generator: TitleGenerator | None,
    safeguard_service: SafeguardService | None,
    system_instruction: str,
    ollama_options: dict[str, float | int] | None,
    tabular_extractor: TabularContextExtractor | None,
    settings: Settings,
    knowledge_document_ids: list[str],
    session_owner_id: str = "",
    auth_context: AuthorizationContext | None = None,
    request_id: str = "",
    clock: Clock | None = None,
) -> Generator[str, None, None]:
    """Serve a retrieval-backed chat answer using the main chat streaming stack."""
    persistence = SessionPersistenceService(clock=clock)
    started_at = time.monotonic()

    if safeguard_service is not None:
        input_assessment = safeguard_service.review_input(
            messages=messages,
            system_instruction="",
        )
        if not input_assessment.allowed:
            yield from persistence.yield_blocked_response(
                assessment=input_assessment,
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
                started_at=started_at,
                session_owner_id=session_owner_id,
            )
            return

    try:
        documents = resolve_knowledge_documents(
            document_ids=knowledge_document_ids,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
        context = build_chat_knowledge_context(
            query=last_user_message(messages),
            document_ids=knowledge_document_ids,
            top_k=5,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    except KnowledgeDocumentNotFound:
        yield sse_error_event("Knowledge document not found.")
        yield sse_done_event()
        return
    except Exception:
        yield sse_error_event("Knowledge retrieval failed.")
        yield sse_done_event()
        return

    knowledge_instruction = _compose_knowledge_instruction(
        base_instruction=system_instruction,
        context_block=context.context_block,
        has_hits=bool(context.citations),
    )
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
        system_instruction=knowledge_instruction,
        ollama_options=ollama_options,
        tabular_extractor=tabular_extractor,
        settings=settings,
        knowledge_documents=[
            {
                "document_id": document.id,
                "filename": document.original_filename,
                "mime_type": document.mime_type,
            }
            for document in documents
        ],
        session_owner_id=session_owner_id,
        tenant_id=auth_context.tenant_id.value
        if auth_context is not None
        else "tenant:default",
        principal_id=auth_context.principal_id.value
        if auth_context is not None
        else "",
        auth_context=auth_context,
        request_id=request_id,
    )


def _compose_knowledge_instruction(
    *,
    base_instruction: str,
    context_block: str,
    has_hits: bool,
) -> str:
    parts: list[str] = []
    if base_instruction.strip():
        parts.append(base_instruction.strip())
    if has_hits:
        parts.append(
            "Use the retrieved knowledge context below as your primary evidence. "
            "Answer naturally, synthesize rather than dumping snippets, and say when the context is insufficient.\n\n"
            "Retrieved knowledge context:\n"
            f"{context_block}"
        )
    else:
        parts.append(
            "No relevant retrieved context was found in the attached knowledge documents. "
            "Explain that briefly and suggest how the user can refine the question."
        )
    return "\n\n".join(parts)


__all__ = ["stream_chat_sse"]
