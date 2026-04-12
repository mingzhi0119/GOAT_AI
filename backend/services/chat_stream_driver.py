from __future__ import annotations

from collections.abc import Generator

from backend.services.chat_stream_run import ChatStreamRunContext
from backend.services.sse import sse_event
from goat_ai.charts.echarts_tool import GENERATE_CHART_V2_SCHEMA
from goat_ai.llm.ollama_client import StreamTextPart, ToolCallPlan


def emit_thinking_sse(text: str) -> Generator[str, None, None]:
    if text:
        yield sse_event({"type": "thinking", "token": text})


def emit_content_through_buffer(
    run: ChatStreamRunContext, text: str
) -> Generator[str, None, None]:
    if not text:
        return
    run.buffer.append(text)
    for token_event in run.output_buffer.push(text):
        if run.first_token_emitted_at is None:
            import time

            run.first_token_emitted_at = time.monotonic()
        yield token_event


def consume_llm_stream_item(
    run: ChatStreamRunContext, item: str | StreamTextPart
) -> Generator[str, None, None]:
    if isinstance(item, StreamTextPart):
        if not item.text:
            return
        if item.kind == "thinking":
            yield from emit_thinking_sse(item.text)
            return
        yield from emit_content_through_buffer(run, item.text)
        return
    yield from emit_content_through_buffer(run, item)


def phase_input_guard(run: ChatStreamRunContext) -> Generator[str, None, None]:
    """Block unsafe input before any LLM call."""
    if run.safeguard is None:
        return
    input_assessment = run.safeguard.review_input(
        messages=run.messages,
        system_instruction=run.system_instruction,
    )
    if input_assessment.allowed:
        return
    run.input_blocked = True
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
        session_owner_id=run.session_owner_id,
        tenant_id=run.tenant_id,
        principal_id=run.principal_id,
    )


def phase_llm_token_stream(run: ChatStreamRunContext) -> Generator[str, None, None]:
    """Stream model tokens (native chart tool path or plain completion)."""
    if run.input_blocked:
        return

    if run.should_use_native_chart_tools and run.chart_dataframe is not None:
        yield from stream_native_chart_tool_path(run)
    else:
        yield from stream_plain_completion(run)


def stream_native_chart_tool_path(
    run: ChatStreamRunContext,
) -> Generator[str, None, None]:
    followup_messages: list[dict[str, object]] | None = None
    for event in run.llm.stream_tokens_with_tools(
        run.model,
        run.turns,
        run.effective_prompt,
        tools=[GENERATE_CHART_V2_SCHEMA],
        ollama_options=run.ollama_options,
    ):
        if isinstance(event, ToolCallPlan):
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

        yield from consume_llm_stream_item(run, event)
        if run.output_buffer.blocked:
            break

    if followup_messages is not None:
        for token in run.llm.stream_tool_followup(
            run.model,
            followup_messages,
            tools=[GENERATE_CHART_V2_SCHEMA],
            ollama_options=run.ollama_options,
        ):
            yield from consume_llm_stream_item(run, token)
            if run.output_buffer.blocked:
                break
    elif not run.buffer:
        yield from stream_plain_completion(run)


def stream_plain_completion(run: ChatStreamRunContext) -> Generator[str, None, None]:
    for item in run.llm.stream_tokens(
        run.model,
        run.turns,
        run.effective_prompt,
        ollama_options=run.ollama_options,
        last_user_images_base64=run.vision_last_user_images_base64,
    ):
        yield from consume_llm_stream_item(run, item)
        if run.output_buffer.blocked:
            break
