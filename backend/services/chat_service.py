"""Public entry for chat streaming — thin wrapper over ``ChatStreamService``."""
from __future__ import annotations

from collections.abc import Generator

from backend.models.chat import ChatMessage
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator
from backend.services.chat_stream_service import ChatStreamService
from backend.services.safeguard_service import SafeguardService
from backend.services.tabular_context import TabularContextExtractor
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
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion."""
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
    )


__all__ = ["stream_chat_sse"]
