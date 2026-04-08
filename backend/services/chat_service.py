"""Public entry for chat streaming, including knowledge-backed RAG answers."""
from __future__ import annotations

import re
import time
from collections.abc import Generator

from backend.models.chat import ChatMessage
from backend.models.knowledge import KnowledgeAnswerRequest
from backend.services.chat_orchestration import SessionPersistenceService
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator
from backend.services.chat_stream_service import ChatStreamService
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.knowledge_service import answer_with_knowledge, resolve_knowledge_documents
from backend.services.safeguard_service import SafeguardService
from backend.services.session_service import last_user_message
from backend.services.sse import sse_done_event, sse_error_event, sse_token_event
from backend.services.tabular_context import TabularContextExtractor
from backend.types import Settings
from goat_ai.ollama_client import LLMClient

_TOKEN_SPLIT_RE = re.compile(r"\S+\s*|\n")


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
            settings=settings,
            knowledge_document_ids=knowledge_document_ids,
            session_owner_id=session_owner_id,
        )
        return

    yield from ChatStreamService().stream(
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
        session_owner_id=session_owner_id,
    )


def _stream_knowledge_chat_sse(
    *,
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
    settings: Settings,
    knowledge_document_ids: list[str],
    session_owner_id: str = "",
) -> Generator[str, None, None]:
    """Serve a deterministic retrieval-backed answer for sessions bound to indexed documents."""
    persistence = SessionPersistenceService()
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
        )
        answer = answer_with_knowledge(
            request=KnowledgeAnswerRequest(
                query=last_user_message(messages),
                document_ids=knowledge_document_ids,
                top_k=5,
                session_id=session_id,
            ),
            settings=settings,
        )
    except KnowledgeDocumentNotFound:
        yield sse_error_event("Knowledge document not found.")
        yield sse_done_event()
        return
    except Exception:
        yield sse_error_event("Knowledge retrieval failed.")
        yield sse_done_event()
        return

    if safeguard_service is not None:
        output_assessment = safeguard_service.review_output(
            user_text=last_user_message(messages),
            assistant_text=answer.answer,
        )
        if not output_assessment.allowed:
            yield from persistence.yield_blocked_response(
                assessment=output_assessment,
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

    first_token_started = False
    first_token_ms: float | None = None
    for token in _TOKEN_SPLIT_RE.findall(answer.answer):
        if not first_token_started:
            first_token_ms = round((time.monotonic() - started_at) * 1000, 1)
            first_token_started = True
        yield sse_token_event(token)
    yield sse_done_event()
    persistence.persist_and_log_chat_result(
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
        assistant_text=answer.answer,
        chart_spec=None,
        knowledge_documents=[
            {
                "document_id": document.id,
                "filename": document.original_filename,
                "mime_type": document.mime_type,
            }
            for document in documents
        ],
        chart_data_source="none",
        started_at=started_at,
        first_token_ms=first_token_ms,
        session_owner_id=session_owner_id,
    )


__all__ = ["stream_chat_sse"]
