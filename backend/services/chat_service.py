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
from backend.services.session_service import last_user_message, persist_chat_session
from backend.services.sse import sse_done_event, sse_error_event, sse_event, sse_token_event
from goat_ai.echarts_tool import GENERATE_CHART_V2_SCHEMA, parse_chart_intent_v2
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.latency_metrics import record_chat_inference_ms
from goat_ai.ollama_client import LLMClient, ToolCallPlan
from goat_ai.tools import messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)

_CHART_INTENT_RE = re.compile(
    r"\b(chart|plot|graph|visuali[sz]e|visualization|trend|compare|comparison)\b",
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


def _emit_buffered_tokens(tokens: list[str]) -> Generator[str, None, None]:
    """Replay buffered token chunks once output moderation passes."""
    for token in tokens:
        yield sse_token_event(token)


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
    title_override: str | None = None,
) -> None:
    """Finalize telemetry, audit log, and optional session persistence."""
    elapsed_ms = round((time.monotonic() - started_at) * 1000)
    record_chat_inference_ms(float(elapsed_ms))
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
) -> Generator[str, None, None]:
    """Emit a policy refusal and finalize logging/persistence."""
    refusal = assessment.refusal_message
    yield sse_token_event(refusal)
    yield sse_done_event()
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
    turns = _to_chat_turns(messages)
    effective_prompt = _compose_system_prompt(system_prompt, user_name, system_instruction)
    emitted_chart_spec: dict[str, object] | None = None
    buffer: list[str] = []
    started_at = time.monotonic()
    safeguard = safeguard_service
    error_message: str | None = None
    should_use_native_chart_tools = (
        _should_attempt_native_chart_tool(messages) and llm.supports_tool_calling(model)
    )
    chart_dataframe = _find_csv_in_messages(messages) if should_use_native_chart_tools else None

    if safeguard is not None:
        input_assessment = safeguard.review_input(
            messages=messages,
            system_instruction=system_instruction,
        )
        if not input_assessment.allowed:
            yield from _yield_blocked_response(
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
                    continue

                chart_spec = _compile_native_chart_tool_call(event, chart_dataframe)
                if chart_spec is None:
                    continue

                emitted_chart_spec = chart_spec
                followup_messages = [
                    *messages_for_ollama(turns, effective_prompt),
                    event.assistant_message,
                    {
                        "role": "tool",
                        "tool_name": event.tool_name,
                        "content": json.dumps({"chart": chart_spec}, ensure_ascii=False),
                    },
                ]
                break

            if followup_messages is not None:
                for token in llm.stream_tool_followup(
                    model,
                    followup_messages,
                    tools=[GENERATE_CHART_V2_SCHEMA],
                    ollama_options=ollama_options,
                ):
                    buffer.append(token)
            elif not buffer:
                for token in llm.stream_tokens(
                    model,
                    turns,
                    effective_prompt,
                    ollama_options=ollama_options,
                ):
                    buffer.append(token)
        else:
            for token in llm.stream_tokens(
                model,
                turns,
                effective_prompt,
                ollama_options=ollama_options,
            ):
                buffer.append(token)
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
                safeguard.review_output(
                    user_text=last_user_message(messages),
                    assistant_text=clean_text,
                )
                if safeguard is not None
                else SafeguardAssessment(allowed=True, stage="output")
            )
            if output_assessment.allowed:
                yield from _emit_buffered_tokens(buffer)
                if chart_spec is not None:
                    yield sse_event({"type": "chart_spec", "chart": chart_spec})
                yield sse_done_event()
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
                    assistant_text=clean_text,
                    chart_spec=chart_spec,
                    started_at=started_at,
                )
            else:
                yield from _yield_blocked_response(
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
