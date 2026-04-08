"""SSE chat stream orchestration — tool loops, safeguard buffering, emission."""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Generator
from types import SimpleNamespace

import pandas as pd

from backend.models.chat import ChatMessage
from backend.prometheus_metrics import inc_chat_stream_completed
from backend.services.chat_orchestration import (
    ChartToolOrchestrator,
    PromptComposer,
    SessionPersistenceService,
)
from backend.services.chat_runtime import ConversationLogger, SessionRepository, TitleGenerator
from backend.services.safeguard_service import SafeguardAssessment, SafeguardService
from backend.domain.chart_types import ChartDataSource
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
        vision_last_user_images_base64: list[str] | None = None,
    ) -> Generator[str, None, None]:
        """Yield SSE-formatted events for a chat completion."""
        run = self._phase_prepare_runtime(
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
        )
        yield from self._phase_input_guard(run)
        error_message: str | None = None
        try:
            yield from self._phase_llm_token_stream(run)
        except OllamaUnavailable as exc:
            logger.warning("Ollama unavailable during chat stream: %s", exc)
            error_message = "AI service temporarily unavailable."
            yield sse_error_event(error_message)
        except Exception:
            logger.exception("Unexpected error during chat stream")
            error_message = "An unexpected error occurred."
            yield sse_error_event(error_message)
        finally:
            yield from self._phase_emit_completion(run, error_message)

    def _phase_prepare_runtime(
        self,
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
        vision_last_user_images_base64: list[str] | None,
    ) -> SimpleNamespace:
        """Assemble collaborators, derived turns, and mutable stream state."""
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
        holdback_tokens = _STREAM_OUTPUT_HOLDBACK_TOKENS if safeguard_service is not None else 0
        output_buffer = _StreamingOutputBuffer(
            safeguard_service,
            latest_user_text,
            holdback_tokens=holdback_tokens,
        )
        vision_b64 = vision_last_user_images_base64 or []
        if vision_b64:
            should_use_native_chart_tools = False
        else:
            should_use_native_chart_tools = chart_orchestrator.should_use_tools(
                messages=messages,
                llm=llm,
                model=model,
            )
        chart_dataframe: pd.DataFrame | None = None
        chart_data_source: ChartDataSource = "none"
        if should_use_native_chart_tools:
            chart_dataframe, chart_data_source = chart_orchestrator.resolve_dataframe(messages)

        return SimpleNamespace(
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
            safeguard=safeguard_service,
            system_instruction=system_instruction,
            ollama_options=ollama_options,
            prompt_composer=prompt_composer,
            chart_orchestrator=chart_orchestrator,
            persistence=persistence,
            turns=turns,
            latest_user_text=latest_user_text,
            effective_prompt=effective_prompt,
            output_buffer=output_buffer,
            should_use_native_chart_tools=should_use_native_chart_tools,
            chart_dataframe=chart_dataframe,
            chart_data_source=chart_data_source,
            started_at=time.monotonic(),
            first_token_emitted_at=None,
            emitted_chart_spec=None,
            buffer=[],
            vision_last_user_images_base64=vision_last_user_images_base64,
        )

    def _phase_input_guard(self, run: SimpleNamespace) -> Generator[str, None, None]:
        """Block unsafe input before any LLM call."""
        if run.safeguard is None:
            return
        input_assessment = run.safeguard.review_input(
            messages=run.messages,
            system_instruction=run.system_instruction,
        )
        if input_assessment.allowed:
            return
        run.input_blocked = True  # type: ignore[attr-defined]
        yield from run.persistence.yield_blocked_response(
            assessment=input_assessment,
            model=run.model,
            messages=run.messages,
            system_prompt=run.system_prompt,
            ip=run.ip,
            conversation_logger=run.conversation_logger,
            user_name=run.user_name,
            session_id=run.session_id,
            all_messages=run.all_messages,
            session_repository=run.session_repository,
            title_generator=run.title_generator,
            started_at=run.started_at,
        )

    def _phase_llm_token_stream(self, run: SimpleNamespace) -> Generator[str, None, None]:
        """Stream model tokens (native chart tool path or plain completion)."""
        if getattr(run, "input_blocked", False):
            return

        if run.should_use_native_chart_tools and run.chart_dataframe is not None:
            yield from self._stream_native_chart_tool_path(run)
        else:
            yield from self._stream_plain_completion(run)

    def _stream_native_chart_tool_path(self, run: SimpleNamespace) -> Generator[str, None, None]:
        followup_messages: list[dict[str, object]] | None = None
        for event in run.llm.stream_tokens_with_tools(
            run.model,
            run.turns,
            run.effective_prompt,
            tools=[GENERATE_CHART_V2_SCHEMA],
            ollama_options=run.ollama_options,
        ):
            if isinstance(event, str):
                run.buffer.append(event)
                for token_event in run.output_buffer.push(event):
                    if run.first_token_emitted_at is None:
                        run.first_token_emitted_at = time.monotonic()
                    yield token_event
                if run.output_buffer.blocked:
                    break
                continue

            chart_spec = run.chart_orchestrator.compile_tool_call(
                tool_plan=event,
                dataframe=run.chart_dataframe,
            )
            if chart_spec is None:
                continue

            run.emitted_chart_spec = chart_spec
            followup_messages = run.chart_orchestrator.build_followup_messages(
                turns=run.turns,
                effective_prompt=run.effective_prompt,
                tool_event=event,
                chart_spec=chart_spec,
            )
            break

        if followup_messages is not None:
            for token in run.llm.stream_tool_followup(
                run.model,
                followup_messages,
                tools=[GENERATE_CHART_V2_SCHEMA],
                ollama_options=run.ollama_options,
            ):
                run.buffer.append(token)
                for token_event in run.output_buffer.push(token):
                    if run.first_token_emitted_at is None:
                        run.first_token_emitted_at = time.monotonic()
                    yield token_event
                if run.output_buffer.blocked:
                    break
        elif not run.buffer:
            yield from self._stream_plain_completion(run)

    def _stream_plain_completion(self, run: SimpleNamespace) -> Generator[str, None, None]:
        for token in run.llm.stream_tokens(
            run.model,
            run.turns,
            run.effective_prompt,
            ollama_options=run.ollama_options,
            last_user_images_base64=run.vision_last_user_images_base64,
        ):
            run.buffer.append(token)
            for token_event in run.output_buffer.push(token):
                if run.first_token_emitted_at is None:
                    run.first_token_emitted_at = time.monotonic()
                yield token_event
            if run.output_buffer.blocked:
                break

    def _phase_emit_completion(
        self,
        run: SimpleNamespace,
        error_message: str | None,
    ) -> Generator[str, None, None]:
        """After LLM phase: error tail, or safeguard output check + persist + done."""
        if getattr(run, "input_blocked", False):
            return
        if error_message is not None:
            yield sse_done_event()
            return

        full_text = "".join(run.buffer)
        clean_text = _strip_chart_block(full_text)
        chart_spec = run.emitted_chart_spec
        if not run.buffer:
            return

        output_assessment = (
            SafeguardAssessment(allowed=False, stage="output")
            if run.output_buffer.blocked
            else (
                run.safeguard.review_output(
                    user_text=run.latest_user_text,
                    assistant_text=clean_text,
                )
                if run.safeguard is not None
                else SafeguardAssessment(allowed=True, stage="output")
            )
        )
        if output_assessment.allowed:
            for token_event in run.output_buffer.flush():
                if run.first_token_emitted_at is None:
                    run.first_token_emitted_at = time.monotonic()
                yield token_event
            if chart_spec is not None:
                yield sse_event({"type": "chart_spec", "chart": chart_spec})
            yield sse_done_event()
            inc_chat_stream_completed()
            first_token_ms = (
                round((run.first_token_emitted_at - run.started_at) * 1000, 1)
                if run.first_token_emitted_at is not None
                else None
            )
            run.persistence.persist_and_log_chat_result(
                model=run.model,
                messages=run.messages,
                system_prompt=run.system_prompt,
                ip=run.ip,
                conversation_logger=run.conversation_logger,
                user_name=run.user_name,
                session_id=run.session_id,
                all_messages=run.all_messages,
                session_repository=run.session_repository,
                title_generator=run.title_generator,
                assistant_text=clean_text,
                chart_spec=chart_spec,
                chart_data_source=(
                    run.chart_data_source if chart_spec is not None else "none"
                ),
                started_at=run.started_at,
                first_token_ms=first_token_ms,
            )
        else:
            yield from run.persistence.yield_blocked_response(
                assessment=output_assessment,
                model=run.model,
                messages=run.messages,
                system_prompt=run.system_prompt,
                ip=run.ip,
                conversation_logger=run.conversation_logger,
                user_name=run.user_name,
                session_id=run.session_id,
                all_messages=run.all_messages,
                session_repository=run.session_repository,
                title_generator=run.title_generator,
                started_at=run.started_at,
            )
