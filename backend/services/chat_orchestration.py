"""Collaborators for chat: prompt composition, chart tools, session finalize."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Generator

import pandas as pd

from backend.domain.chart_provenance_policy import (
    resolve_dataframe_for_native_chart_tool,
)
from backend.domain.chart_types import ChartDataSource
from backend.models.chat import ChatMessage
from backend.services.chart_compiler_v2 import compile_chart_spec_v2
from backend.services.chat_runtime import (
    ConversationLogEntry,
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)
from backend.services.safeguard_service import (
    SAFEGUARD_BLOCKED_TITLE,
    SafeguardAssessment,
)
from backend.services.session_service import last_user_message, persist_chat_session
from backend.services.sse import sse_done_event, sse_token_event
from backend.services.tabular_context import TabularContextExtractor
from goat_ai.echarts_tool import parse_chart_intent_v2
from goat_ai.latency_metrics import record_chat_first_token_ms, record_chat_inference_ms
from goat_ai.ollama_client import LLMClient, ToolCallPlan
from goat_ai.tools import messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)

_CHART_INTENT_RE = re.compile(
    r"(\b(chart|plot|graph|visuali[sz]e|visualization|trend|compare|comparison|pie)\b|图表|图形|可视化|趋势|对比|饼图)",
    re.IGNORECASE,
)


def _compose_system_prompt(
    base_prompt: str, user_name: str, system_instruction: str
) -> str:
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
    return (
        compiled_chart.model_dump(mode="json") if compiled_chart is not None else None
    )


class PromptComposer:
    """Compose the effective system prompt for chat orchestration."""

    def compose(
        self, *, base_prompt: str, user_name: str, system_instruction: str
    ) -> str:
        return _compose_system_prompt(base_prompt, user_name, system_instruction)


class ChartToolOrchestrator:
    """Encapsulate chart-tool eligibility, data-source resolution, and compilation."""

    def __init__(self, tabular_extractor: TabularContextExtractor) -> None:
        self._tabular = tabular_extractor

    def should_use_tools(
        self,
        *,
        messages: list[ChatMessage],
        llm: LLMClient,
        model: str,
    ) -> bool:
        return _should_attempt_native_chart_tool(
            messages
        ) and llm.supports_tool_calling(model)

    def resolve_dataframe(
        self, messages: list[ChatMessage]
    ) -> tuple[pd.DataFrame, ChartDataSource]:
        uploaded = self._tabular.extract_dataframe(messages)
        return resolve_dataframe_for_native_chart_tool(uploaded)

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
        knowledge_documents: list[dict[str, str]] | None = None,
        assistant_artifacts: list[dict[str, object]] | None = None,
        chart_data_source: ChartDataSource = "none",
        started_at: float,
        first_token_ms: float | None = None,
        title_override: str | None = None,
        session_owner_id: str = "",
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
            knowledge_documents=knowledge_documents,
            assistant_artifacts=assistant_artifacts,
            chart_data_source=chart_data_source,
            started_at=started_at,
            first_token_ms=first_token_ms,
            title_override=title_override,
            session_owner_id=session_owner_id,
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
        session_owner_id: str = "",
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
            session_owner_id=session_owner_id,
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
    knowledge_documents: list[dict[str, str]] | None = None,
    assistant_artifacts: list[dict[str, object]] | None = None,
    started_at: float,
    chart_data_source: ChartDataSource = "none",
    first_token_ms: float | None = None,
    title_override: str | None = None,
    session_owner_id: str = "",
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
            knowledge_documents=knowledge_documents,
            assistant_artifacts=assistant_artifacts,
            chart_data_source=chart_data_source,
            title_override=title_override,
            owner_id=session_owner_id,
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
    session_owner_id: str = "",
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
            session_owner_id=session_owner_id,
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
        session_owner_id=session_owner_id,
    )
