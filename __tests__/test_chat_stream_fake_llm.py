"""stream_chat_sse with a fake LLM client (no Ollama)."""
from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.chat_service import stream_chat_sse, sse_event
from goat_ai.latency_metrics import get_inference_snapshot
from goat_ai.ollama_client import ToolCallPlan
from goat_ai.types import ChatTurn


class FakeLLMClient:
    """Minimal LLMClient Protocol implementation for tests."""

    def list_model_names(self) -> list[str]:
        return ["test-model"]

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        yield "Hello"
        yield "!"

    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> ToolCallPlan | None:
        return None

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        if False:
            yield ""
        return


class FakeChartToolLLMClient(FakeLLMClient):
    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> ToolCallPlan | None:
        return ToolCallPlan(
            assistant_message={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "generate_chart",
                            "arguments": {
                                "chart_type": "line",
                                "title": "Revenue trend",
                                "x_key": "month",
                                "series": [{"key": "revenue", "name": "Revenue"}],
                            },
                        }
                    }
                ],
            },
            tool_name="generate_chart",
            arguments={
                "chart_type": "line",
                "title": "Revenue trend",
                "x_key": "month",
                "series": [{"key": "revenue", "name": "Revenue"}],
            },
        )

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        yield "Here is the chart-driven answer."


def test_stream_chat_sse_emits_tokens_done_and_records_latency() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    log_service.init_db(db_path)
    try:
        events: list[str] = []
        for chunk in stream_chat_sse(
            llm=FakeLLMClient(),
            model="test-model",
            messages=[ChatMessage(role="user", content="Hi")],
            system_prompt="You are helpful.",
            ip="127.0.0.1",
            log_db_path=db_path,
        ):
            events.append(chunk)

        token_lines = [e for e in events if "Hello" in e or "!" in e]
        assert len(token_lines) >= 2
        assert any("[DONE]" in e for e in events)

        snap = get_inference_snapshot()
        assert snap["chat_sample_count"] == 1
        assert float(snap["chat_avg_ms"]) >= 0.0
    finally:
        tmp.cleanup()


def test_sse_event_format() -> None:
    assert sse_event("x") == 'data: "x"\n\n'


def test_stream_chat_sse_prefers_native_chart_tool_call_when_available() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    log_service.init_db(db_path)
    try:
        file_context = (
            "[User uploaded tabular data for analysis]\n\n"
            "Column names: month, revenue.\n\n"
            "CHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\nFeb,12\n```\n"
        )
        events = list(
            stream_chat_sse(
                llm=FakeChartToolLLMClient(),
                model="test-model",
                messages=[
                    ChatMessage(role="user", content=file_context),
                    ChatMessage(role="assistant", content="I have loaded the file context."),
                    ChatMessage(role="user", content="Please chart the revenue trend."),
                ],
                system_prompt="You are helpful.",
                ip="127.0.0.1",
                log_db_path=db_path,
            )
        )

        assert any('"type": "chart_spec"' in event for event in events)
        assert any("Here is the chart-driven answer." in event for event in events)
        assert any("[DONE]" in event for event in events)
    finally:
        tmp.cleanup()
