from __future__ import annotations

import re
import time
from dataclasses import dataclass

import pandas as pd

from backend.domain.authz_types import AuthorizationContext
from backend.domain.chart_types import ChartDataSource
from backend.models.artifact import ChatArtifact
from backend.models.chat import ChatMessage
from backend.services.chat_orchestration import (
    ChartToolOrchestrator,
    PromptComposer,
    SessionPersistenceService,
)
from backend.services.chat_runtime import (
    ConversationLogger,
    SessionRepository,
    TitleGenerator,
)
from backend.services.safeguard_service import SafeguardService
from backend.services.session_service import last_user_message
from backend.services.sse import sse_token_event
from backend.services.tabular_context import (
    EmbeddedCsvTabularExtractor,
    TabularContextExtractor,
)
from backend.types import Settings
from goat_ai.llm.ollama_client import LLMClient
from goat_ai.shared.clocks import Clock
from goat_ai.shared.types import ChatTurn

_STREAM_OUTPUT_HOLDBACK_TOKENS = 1
_CHART_BLOCK_RE = re.compile(r":::chart[\s\S]*?:::", re.DOTALL)


def to_chat_turns(messages: list[ChatMessage]) -> list[ChatTurn]:
    """Convert Pydantic chat messages to goat_ai chat turns."""
    return [
        ChatTurn(role=message.role, content=message.content) for message in messages
    ]


def strip_chart_block(text: str) -> str:
    """Remove the legacy :::chart block from assistant text when present."""
    return _CHART_BLOCK_RE.sub("", text).strip()


class StreamingOutputBuffer:
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


@dataclass(slots=True)
class ChatStreamRunContext:
    llm: LLMClient
    model: str
    messages: list[ChatMessage]
    system_prompt: str
    ip: str
    conversation_logger: ConversationLogger
    user_name: str
    session_id: str | None
    all_messages: list[ChatMessage] | None
    session_repository: SessionRepository | None
    title_generator: TitleGenerator | None
    safeguard: SafeguardService | None
    system_instruction: str
    ollama_options: dict[str, float | int | bool | str] | None
    prompt_composer: PromptComposer
    chart_orchestrator: ChartToolOrchestrator
    persistence: SessionPersistenceService
    turns: list[ChatTurn]
    latest_user_text: str
    effective_prompt: str
    output_buffer: StreamingOutputBuffer
    should_use_native_chart_tools: bool
    chart_dataframe: pd.DataFrame | None
    chart_data_source: ChartDataSource
    started_at: float
    first_token_emitted_at: float | None
    emitted_chart_spec: dict[str, object] | None
    buffer: list[str]
    vision_last_user_images_base64: list[str] | None
    settings: Settings | None
    knowledge_documents: list[dict[str, str]] | None
    emitted_artifacts: list[ChatArtifact]
    session_owner_id: str
    tenant_id: str
    principal_id: str
    auth_context: AuthorizationContext | None
    request_id: str
    input_blocked: bool = False


def prepare_chat_stream_run(
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
    plan_mode: bool,
    ollama_options: dict[str, float | int | bool | str] | None,
    tabular_extractor: TabularContextExtractor | None,
    vision_last_user_images_base64: list[str] | None,
    settings: Settings | None,
    knowledge_documents: list[dict[str, str]] | None,
    session_owner_id: str,
    tenant_id: str,
    principal_id: str,
    auth_context: AuthorizationContext | None,
    request_id: str,
    clock: Clock | None,
) -> ChatStreamRunContext:
    """Assemble collaborators, derived turns, and mutable stream state."""
    prompt_composer = PromptComposer()
    chart_orchestrator = ChartToolOrchestrator(
        tabular_extractor or EmbeddedCsvTabularExtractor(),
    )
    persistence = SessionPersistenceService(clock=clock)
    turns = to_chat_turns(messages)
    latest_user_text = last_user_message(messages)
    effective_prompt = prompt_composer.compose(
        base_prompt=system_prompt,
        user_name=user_name,
        system_instruction=system_instruction,
        plan_mode=plan_mode,
    )
    holdback_tokens = (
        _STREAM_OUTPUT_HOLDBACK_TOKENS if safeguard_service is not None else 0
    )
    output_buffer = StreamingOutputBuffer(
        safeguard_service,
        latest_user_text,
        holdback_tokens=holdback_tokens,
    )
    vision_b64 = vision_last_user_images_base64 or []
    should_use_native_chart_tools = (
        False
        if vision_b64
        else chart_orchestrator.should_use_tools(
            messages=messages,
            llm=llm,
            model=model,
        )
    )
    chart_dataframe: pd.DataFrame | None = None
    chart_data_source: ChartDataSource = "none"
    if should_use_native_chart_tools:
        chart_dataframe, chart_data_source = chart_orchestrator.resolve_dataframe(
            messages
        )

    return ChatStreamRunContext(
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
        settings=settings,
        knowledge_documents=knowledge_documents,
        emitted_artifacts=[],
        session_owner_id=session_owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_context=auth_context,
        request_id=request_id,
    )
