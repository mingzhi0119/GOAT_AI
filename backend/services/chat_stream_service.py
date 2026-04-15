"""SSE chat stream orchestration: typed run context, stream driver, finalize."""

from __future__ import annotations

import logging
from collections.abc import Generator

from backend.domain.authz_types import AuthorizationContext
from backend.models.chat import ChatMessage
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)
from backend.services.chat_stream_driver import (
    phase_input_guard,
    phase_llm_token_stream,
)
from backend.services.chat_stream_finalize import phase_emit_completion
from backend.services.chat_stream_run import prepare_chat_stream_run
from backend.services.safeguard_service import SafeguardService
from backend.services.sse import sse_error_event
from backend.services.tabular_context import TabularContextExtractor
from backend.types import Settings
from goat_ai.llm.ollama_client import LLMClient
from goat_ai.shared.clocks import Clock
from goat_ai.shared.exceptions import OllamaUnavailable

logger = logging.getLogger(__name__)


class ChatStreamService:
    """Owns the chat SSE generator while delegating driver/finalize phases."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock

    def stream(
        self,
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
        persona_snapshot: dict[str, str] | None = None,
        plan_mode: bool = False,
        ollama_options: dict[str, float | int | bool | str] | None = None,
        tabular_extractor: TabularContextExtractor | None = None,
        vision_last_user_images_base64: list[str] | None = None,
        settings: Settings | None = None,
        knowledge_documents: list[dict[str, str]] | None = None,
        session_owner_id: str = "",
        tenant_id: str = "tenant:default",
        principal_id: str = "",
        auth_context: AuthorizationContext | None = None,
        request_id: str = "",
    ) -> Generator[str, None, None]:
        """Yield SSE-formatted events for a chat completion."""
        run = prepare_chat_stream_run(
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
            persona_snapshot=persona_snapshot,
            plan_mode=plan_mode,
            ollama_options=ollama_options,
            tabular_extractor=tabular_extractor,
            vision_last_user_images_base64=vision_last_user_images_base64,
            settings=settings,
            knowledge_documents=knowledge_documents,
            session_owner_id=session_owner_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            auth_context=auth_context,
            request_id=request_id,
            clock=self._clock,
        )
        yield from phase_input_guard(run)
        error_message: str | None = None
        try:
            yield from phase_llm_token_stream(run)
        except OllamaUnavailable as exc:
            logger.warning("Ollama unavailable during chat stream: %s", exc)
            error_message = "AI service temporarily unavailable."
            yield sse_error_event(error_message)
        except Exception:
            logger.exception("Unexpected error during chat stream")
            error_message = "An unexpected error occurred."
            yield sse_error_event(error_message)
        finally:
            yield from phase_emit_completion(run, error_message)
