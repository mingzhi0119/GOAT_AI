"""SSE chat stream orchestration — tool loops, safeguard buffering, emission."""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Generator

import pandas as pd

from backend.models.chat import ChatMessage
from backend.services.chat_orchestration import (
    ChartToolOrchestrator,
    PromptComposer,
    SessionPersistenceService,
)
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator
from backend.services.safeguard_service import SafeguardAssessment, SafeguardService
from backend.services.session_message_codec import ChartDataSource
from backend.services.session_service import last_user_message
from backend.services.sse import sse_done_event, sse_error_event, sse_event, sse_token_event
from backend.services.tabular_context import EmbeddedCsvTabularExtractor, TabularContextExtractor
from goat_ai.echarts_tool import GENERATE_CHART_V2_SCHEMA
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import LLMClient
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)
_STREAM_OUTPUT_HOLDBACK_TOKENS = 1
_CHART_BLOCK_RE = re.compile(r":::chart[\s\S]*?:::", re.DOTALL)


def _to_chat_turns(messages: list[ChatMessage]) -> list[ChatTurn]:
    """Convert Pydantic chat messages to goat_ai chat turns."""
    return [ChatTurn(role=message.role, content=message.content) for message in messages]


def _strip_chart_block(text: str) -> str:
    """Remove the legacy :::chart block from assistant text when present."""
    return _CHART_BLOCK_RE.sub("", text).strip()


class _StreamingOutputBuffer:
    """Incrementally moderate and emit assistant output with token holdback."""

    def __init__(
        self,
        safeguard: SafeguardService | None,
        user_text: str,
        *,
        holdback_tokens: int,
    ) -> None:
        self._safeguard = safeguard
        self._user_text = user_text
        self._holdback_tokens = max(0, holdback_tokens)
        self._pending_tokens: list[str] = []
        self._full_text = ""
        self._blocked = False

    @property
    def blocked(self) -> bool:
        return self._blocked

    def push(self, token: str) -> list[str]:
        """Buffer one token chunk and return any newly-safe token events."""
        if self._blocked or not token:
            return []

        self._full_text += token
        self._pending_tokens.append(token)
        if not self._is_safe(self._full_text):
            self._blocked = True
            return []

        emit_count = len(self._pending_tokens) - self._holdback_tokens
        if emit_count <= 0:
            return []

        emit_tokens = self._pending_tokens[:emit_count]
        self._pending_tokens = self._pending_tokens[emit_count:]
        return [sse_token_event(item) for item in emit_tokens]

    def flush(self) -> list[str]:
        """Emit remaining buffered token events if final output is safe."""
        if self._blocked:
            return []
        if not self._is_safe(self._full_text):
            self._blocked = True
            return []
        if not self._pending_tokens:
            return []
        emit_tokens = [sse_token_event(item) for item in self._pending_tokens]
        self._pending_tokens = []
        return emit_tokens

    def _is_safe(self, assistant_text: str) -> bool:
        if self._safeguard is None:
            return True
        assessment = self._safeguard.review_output(
            user_text=self._user_text,
            assistant_text=assistant_text,
        )
        return assessment.allowed


class ChatStreamService:
    """Owns the chat SSE generator: native chart tools, safeguards, persistence hooks."""

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
        ollama_options: dict[str, float | int] | None = None,
        tabular_extractor: TabularContextExtractor | None = None,
    ) -> Generator[str, None, None]:
        """Yield SSE-formatted events for a chat completion."""
        prompt_composer = PromptComposer()
        chart_orchestrator = ChartToolOrchestrator(
            tabular_extractor or EmbeddedCsvTabularExtractor(),
        )
        persistence = SessionPersistenceService()
        turns = _to_chat_turns(messages)
        latest_user_text = last_user_message(messages)
        effective_prompt = prompt_composer.compose(
            base_prompt=system_prompt,
            user_name=user_name,
            system_instruction=system_instruction,
        )
        emitted_chart_spec: dict[str, object] | None = None
        chart_data_source: ChartDataSource = "none"
        buffer: list[str] = []
        holdback_tokens = _STREAM_OUTPUT_HOLDBACK_TOKENS if safeguard_service is not None else 0
        output_buffer = _StreamingOutputBuffer(
            safeguard_service,
            latest_user_text,
            holdback_tokens=holdback_tokens,
        )
        started_at = time.monotonic()
        first_token_emitted_at: float | None = None
        safeguard = safeguard_service
        error_message: str | None = None
        should_use_native_chart_tools = chart_orchestrator.should_use_tools(
            messages=messages,
            llm=llm,
            model=model,
        )
        chart_dataframe: pd.DataFrame | None = None
        if should_use_native_chart_tools:
            chart_dataframe, chart_data_source = chart_orchestrator.resolve_dataframe(messages)

        if safeguard is not None:
            input_assessment = safeguard.review_input(
                messages=messages,
                system_instruction=system_instruction,
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
                )
                return

        try:
            if should_use_native_chart_tools and chart_dataframe is not None:
                followup_messages: list[dict[str, object]] | None = None
                for event in llm.stream_tokens_with_tools(
                    model,
                    turns,
                    effective_prompt,
                    tools=[GENERATE_CHART_V2_SCHEMA],
                    ollama_options=ollama_options,
                ):
                    if isinstance(event, str):
                        buffer.append(event)
                        for token_event in output_buffer.push(event):
                            if first_token_emitted_at is None:
                                first_token_emitted_at = time.monotonic()
                            yield token_event
                        if output_buffer.blocked:
                            break
                        continue

                    chart_spec = chart_orchestrator.compile_tool_call(
                        tool_plan=event,
                        dataframe=chart_dataframe,
                    )
                    if chart_spec is None:
                        continue

                    emitted_chart_spec = chart_spec
                    followup_messages = chart_orchestrator.build_followup_messages(
                        turns=turns,
                        effective_prompt=effective_prompt,
                        tool_event=event,
                        chart_spec=chart_spec,
                    )
                    break

                if followup_messages is not None:
                    for token in llm.stream_tool_followup(
                        model,
                        followup_messages,
                        tools=[GENERATE_CHART_V2_SCHEMA],
                        ollama_options=ollama_options,
                    ):
                        buffer.append(token)
                        for token_event in output_buffer.push(token):
                            if first_token_emitted_at is None:
                                first_token_emitted_at = time.monotonic()
                            yield token_event
                        if output_buffer.blocked:
                            break
                elif not buffer:
                    for token in llm.stream_tokens(
                        model,
                        turns,
                        effective_prompt,
                        ollama_options=ollama_options,
                    ):
                        buffer.append(token)
                        for token_event in output_buffer.push(token):
                            if first_token_emitted_at is None:
                                first_token_emitted_at = time.monotonic()
                            yield token_event
                        if output_buffer.blocked:
                            break
            else:
                for token in llm.stream_tokens(
                    model,
                    turns,
                    effective_prompt,
                    ollama_options=ollama_options,
                ):
                    buffer.append(token)
                    for token_event in output_buffer.push(token):
                        if first_token_emitted_at is None:
                            first_token_emitted_at = time.monotonic()
                        yield token_event
                    if output_buffer.blocked:
                        break
        except OllamaUnavailable as exc:
            logger.warning("Ollama unavailable during chat stream: %s", exc)
            error_message = "AI service temporarily unavailable."
            yield sse_error_event(error_message)
        except Exception:
            logger.exception("Unexpected error during chat stream")
            error_message = "An unexpected error occurred."
            yield sse_error_event(error_message)
        finally:
            if error_message is not None:
                yield sse_done_event()
                return
            full_text = "".join(buffer)
            clean_text = _strip_chart_block(full_text)
            chart_spec = emitted_chart_spec
            if buffer:
                output_assessment = (
                    SafeguardAssessment(allowed=False, stage="output")
                    if output_buffer.blocked
                    else (
                        safeguard.review_output(
                            user_text=latest_user_text,
                            assistant_text=clean_text,
                        )
                        if safeguard is not None
                        else SafeguardAssessment(allowed=True, stage="output")
                    )
                )
                if output_assessment.allowed:
                    for token_event in output_buffer.flush():
                        if first_token_emitted_at is None:
                            first_token_emitted_at = time.monotonic()
                        yield token_event
                    if chart_spec is not None:
                        yield sse_event({"type": "chart_spec", "chart": chart_spec})
                    yield sse_done_event()
                    first_token_ms = (
                        round((first_token_emitted_at - started_at) * 1000, 1)
                        if first_token_emitted_at is not None
                        else None
                    )
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
                        assistant_text=clean_text,
                        chart_spec=chart_spec,
                        chart_data_source=(chart_data_source if chart_spec is not None else "none"),
                        started_at=started_at,
                        first_token_ms=first_token_ms,
                    )
                else:
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
                    )
