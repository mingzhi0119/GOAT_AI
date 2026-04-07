"""Chat streaming orchestration for the FastAPI layer."""
from __future__ import annotations

import io
import json
import logging
import re
import time
from typing import Generator

import pandas as pd

from backend.models.chat import ChatMessage
from backend.services.chart_compiler_v2 import compile_chart_spec_v2
from backend.services.chat_runtime import ConversationLogEntry, ConversationLogger, SessionRepository, TitleGenerator
from backend.services.safeguard_service import (
    SAFEGUARD_BLOCKED_TITLE,
    SafeguardAssessment,
    SafeguardService,
)
from backend.services.session_message_codec import ChartDataSource
from backend.services.session_service import last_user_message, persist_chat_session
from backend.services.sse import sse_done_event, sse_error_event, sse_event, sse_token_event
from goat_ai.echarts_tool import GENERATE_CHART_V2_SCHEMA, parse_chart_intent_v2
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.latency_metrics import record_chat_first_token_ms, record_chat_inference_ms
from goat_ai.ollama_client import LLMClient, ToolCallPlan
from goat_ai.tools import messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)
_STREAM_OUTPUT_HOLDBACK_TOKENS = 1

_CHART_INTENT_RE = re.compile(
    r"(\b(chart|plot|graph|visuali[sz]e|visualization|trend|compare|comparison|pie)\b|图表|图形|可视化|趋势|对比|饼图)",
    re.IGNORECASE,
)
_CHART_BLOCK_RE = re.compile(r":::chart[\s\S]*?:::", re.DOTALL)
_CSV_EMBED_RE = re.compile(r"CHART_DATA_CSV:\n```\n(.*?)\n```", re.DOTALL)


def _to_chat_turns(messages: list[ChatMessage]) -> list[ChatTurn]:
    """Convert Pydantic chat messages to goat_ai chat turns."""
    return [ChatTurn(role=message.role, content=message.content) for message in messages]


def _compose_system_prompt(base_prompt: str, user_name: str, system_instruction: str) -> str:
    """Merge base GOAT prompt, optional name, and optional user instructions."""
    parts: list[str] = [base_prompt]
    if user_name.strip():
        parts.append(
            f"The student's name is {user_name.strip()}. Feel free to address them by name."
        )
    extra = system_instruction.strip()
    if extra:
        parts.append(
            "Additional instructions from the user (apply consistently):\n" + extra
        )
    return "\n\n".join(parts)


def _find_csv_in_messages(messages: list[ChatMessage]) -> pd.DataFrame | None:
    """Search the conversation history for an embedded CHART_DATA_CSV block."""
    for message in messages:
        if message.role != "user":
            continue
        match = _CSV_EMBED_RE.search(message.content)
        if match:
            try:
                return pd.read_csv(io.StringIO(match.group(1)))
            except Exception:
                logger.warning("Failed to parse embedded CSV from file-context message")
    return None


def _default_chart_dataframe() -> pd.DataFrame:
    """Provide a small fallback dataset for chart tool calls without uploads."""
    return pd.DataFrame(
        [
            {"category": "A", "value": 42, "revenue": 120, "cost": 70, "month": "Jan"},
            {"category": "B", "value": 28, "revenue": 95, "cost": 60, "month": "Feb"},
            {"category": "C", "value": 18, "revenue": 80, "cost": 55, "month": "Mar"},
            {"category": "D", "value": 12, "revenue": 72, "cost": 48, "month": "Apr"},
        ]
    )


def _strip_chart_block(text: str) -> str:
    """Remove the legacy :::chart block from assistant text when present."""
    return _CHART_BLOCK_RE.sub("", text).strip()


def _should_attempt_native_chart_tool(messages: list[ChatMessage]) -> bool:
    """Return True when the latest user turn looks like a visualization request."""
    return bool(_CHART_INTENT_RE.search(last_user_message(messages)))


def _compile_native_chart_tool_call(
    tool_plan: ToolCallPlan,
    dataframe: pd.DataFrame,
) -> dict[str, object] | None:
    """Compile a chart spec from a native tool call returned by the LLM."""
    if tool_plan.tool_name != "generate_chart_v2":
        return None

    try:
        intent = parse_chart_intent_v2(tool_plan.arguments)
    except Exception:
        logger.warning("Native chart tool arguments failed ChartIntentV2 validation")
        return None

    compiled_chart = compile_chart_spec_v2(dataframe, intent)
    return compiled_chart.model_dump(mode="json") if compiled_chart is not None else None


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


class PromptComposer:
    """Compose the effective system prompt for chat orchestration."""

    def compose(self, *, base_prompt: str, user_name: str, system_instruction: str) -> str:
        return _compose_system_prompt(base_prompt, user_name, system_instruction)


class ChartToolOrchestrator:
    """Encapsulate chart-tool eligibility, data-source resolution, and compilation."""

    def should_use_tools(
        self,
        *,
        messages: list[ChatMessage],
        llm: LLMClient,
        model: str,
    ) -> bool:
        return _should_attempt_native_chart_tool(messages) and llm.supports_tool_calling(model)

    def resolve_dataframe(self, messages: list[ChatMessage]) -> tuple[pd.DataFrame, ChartDataSource]:
        uploaded = _find_csv_in_messages(messages)
        if uploaded is not None:
            return uploaded, "uploaded"
        return _default_chart_dataframe(), "demo"

    def compile_tool_call(
        self,
        *,
        tool_plan: ToolCallPlan,
        dataframe: pd.DataFrame,
    ) -> dict[str, object] | None:
        return _compile_native_chart_tool_call(tool_plan, dataframe)

    def build_followup_messages(
        self,
        *,
        turns: list[ChatTurn],
        effective_prompt: str,
        tool_event: ToolCallPlan,
        chart_spec: dict[str, object],
    ) -> list[dict[str, object]]:
        return [
            *messages_for_ollama(turns, effective_prompt),
            tool_event.assistant_message,
            {
                "role": "tool",
                "tool_name": tool_event.tool_name,
                "content": json.dumps({"chart": chart_spec}, ensure_ascii=False),
            },
        ]


class SessionPersistenceService:
    """Finalize telemetry and session persistence for chat streams."""

    def persist_and_log_chat_result(
        self,
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
        assistant_text: str,
        chart_spec: dict[str, object] | None,
        chart_data_source: ChartDataSource = "none",
        started_at: float,
        first_token_ms: float | None = None,
        title_override: str | None = None,
    ) -> None:
        _persist_and_log_chat_result(
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
            assistant_text=assistant_text,
            chart_spec=chart_spec,
            chart_data_source=chart_data_source,
            started_at=started_at,
            first_token_ms=first_token_ms,
            title_override=title_override,
        )

    def yield_blocked_response(
        self,
        *,
        assessment: SafeguardAssessment,
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
        started_at: float,
    ) -> Generator[str, None, None]:
        yield from _yield_blocked_response(
            assessment=assessment,
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
            persistence=self,
        )


def _persist_and_log_chat_result(
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
    assistant_text: str,
    chart_spec: dict[str, object] | None,
    started_at: float,
    chart_data_source: ChartDataSource = "none",
    first_token_ms: float | None = None,
    title_override: str | None = None,
) -> None:
    """Finalize telemetry, audit log, and optional session persistence."""
    elapsed_ms = round((time.monotonic() - started_at) * 1000)
    record_chat_inference_ms(float(elapsed_ms), model=model)
    if first_token_ms is not None:
        record_chat_first_token_ms(float(first_token_ms), model=model)
    conversation_logger.log(
        ConversationLogEntry(
            ip=ip,
            model=model,
            turn_count=len(messages),
            user_message=last_user_message(messages),
            assistant_response=assistant_text,
            response_ms=elapsed_ms,
            user_name=user_name,
            session_id=session_id,
        )
    )

    if session_id and session_repository is not None and title_generator is not None:
        persist_chat_session(
            session_id=session_id,
            model=model,
            final_messages=all_messages if all_messages is not None else messages,
            assistant_text=assistant_text,
            chart_spec=chart_spec,
            session_repository=session_repository,
            title_generator=title_generator,
            chart_data_source=chart_data_source,
            title_override=title_override,
        )


def _yield_blocked_response(
    *,
    assessment: SafeguardAssessment,
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
    started_at: float,
    persistence: SessionPersistenceService | None = None,
) -> Generator[str, None, None]:
    """Emit a policy refusal and finalize logging/persistence."""
    refusal = assessment.refusal_message
    yield sse_token_event(refusal)
    yield sse_done_event()
    if persistence is not None:
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
            assistant_text=refusal,
            chart_spec=None,
            chart_data_source="none",
            started_at=started_at,
            title_override=SAFEGUARD_BLOCKED_TITLE,
        )
        return

    _persist_and_log_chat_result(
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
        assistant_text=refusal,
        chart_spec=None,
        started_at=started_at,
        chart_data_source="none",
        title_override=SAFEGUARD_BLOCKED_TITLE,
    )


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
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion."""
    prompt_composer = PromptComposer()
    chart_orchestrator = ChartToolOrchestrator()
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
