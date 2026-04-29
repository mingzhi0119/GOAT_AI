"""Knowledge-backed chat flow helpers."""

from __future__ import annotations

import io
import logging
import time
from collections.abc import Generator

import pandas as pd

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
from backend.services.knowledge_repository import KnowledgeDocumentRecord
from backend.services.knowledge_service import (
    build_chat_knowledge_context,
    resolve_knowledge_documents,
)
from backend.services.knowledge_answer_prompting import compose_knowledge_instruction
from backend.services.safeguard_service import SafeguardService
from backend.services.session_service import last_user_message
from backend.services.sse import sse_done_event, sse_error_event
from backend.services.tabular_context import TabularContextExtractor
from backend.types import Settings
from goat_ai.uploads import build_object_store
from goat_ai.llm.ollama_client import LLMClient
from goat_ai.shared.clocks import Clock

logger = logging.getLogger(__name__)


def build_chat_stream_identity(
    auth_context: AuthorizationContext | None,
) -> tuple[str, str]:
    tenant_id = (
        auth_context.tenant_id.value if auth_context is not None else "tenant:default"
    )
    principal_id = auth_context.principal_id.value if auth_context is not None else ""
    return tenant_id, principal_id


class _KnowledgeTabularFallbackExtractor:
    """Prefer embedded CSV context, then fall back to the authorized knowledge file."""

    def __init__(
        self,
        base: TabularContextExtractor | None,
        dataframe: pd.DataFrame,
    ) -> None:
        self._base = base
        self._dataframe = dataframe

    def extract_dataframe(self, messages: list[ChatMessage]) -> pd.DataFrame | None:
        if self._base is not None:
            embedded = self._base.extract_dataframe(messages)
            if embedded is not None:
                return embedded
        return self._dataframe.copy()


def _read_knowledge_document_bytes(
    *,
    document: KnowledgeDocumentRecord,
    settings: Settings,
) -> bytes | None:
    if document.storage_key:
        return build_object_store(settings).read_bytes(document.storage_key)
    if document.storage_path:
        from pathlib import Path

        return Path(document.storage_path).read_bytes()
    return None


def _load_tabular_dataframe_from_knowledge_documents(
    *,
    documents: list[KnowledgeDocumentRecord],
    settings: Settings,
) -> pd.DataFrame | None:
    for document in documents:
        filename = document.original_filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in {"csv", "xlsx"}:
            continue
        try:
            content = _read_knowledge_document_bytes(
                document=document,
                settings=settings,
            )
            if not content:
                continue
            if ext == "csv":
                return pd.read_csv(io.BytesIO(content))
            return pd.read_excel(io.BytesIO(content))
        except Exception:
            logger.warning(
                "Failed to load knowledge document as tabular chart data: %s",
                document.id,
                exc_info=True,
            )
    return None


def _with_knowledge_tabular_fallback(
    *,
    base: TabularContextExtractor | None,
    documents: list[KnowledgeDocumentRecord],
    settings: Settings,
) -> TabularContextExtractor | None:
    dataframe = _load_tabular_dataframe_from_knowledge_documents(
        documents=documents,
        settings=settings,
    )
    if dataframe is None:
        return base
    return _KnowledgeTabularFallbackExtractor(base, dataframe)


def stream_knowledge_chat_sse(
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
    persona_snapshot: dict[str, str] | None,
    plan_mode: bool,
    ollama_options: dict[str, float | int | bool | str] | None,
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
                persona_snapshot=persona_snapshot,
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

    knowledge_instruction = compose_knowledge_instruction(
        base_instruction=system_instruction,
        context_block=context.context_block,
        has_hits=bool(context.citations),
    )
    tabular_with_knowledge = _with_knowledge_tabular_fallback(
        base=tabular_extractor,
        documents=documents,
        settings=settings,
    )
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
        system_instruction=knowledge_instruction,
        persona_snapshot=persona_snapshot,
        plan_mode=plan_mode,
        ollama_options=ollama_options,
        tabular_extractor=tabular_with_knowledge,
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
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_context=auth_context,
        request_id=request_id,
    )
