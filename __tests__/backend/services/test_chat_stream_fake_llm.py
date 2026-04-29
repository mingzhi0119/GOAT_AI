"""stream_chat_sse with a fake LLM client (no Ollama)."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.chat_runtime import (
    OllamaTitleGenerator,
    SQLiteConversationLogger,
    SQLiteSessionRepository,
)
from backend.services.chat_service import stream_chat_sse
from backend.services.safeguard_service import RuleBasedSafeguardService
from backend.services.sse import sse_event
from goat_ai.config.settings import Settings
from goat_ai.llm.ollama_client import ToolCallPlan
from goat_ai.search.providers import WebSearchError, WebSearchHit
from goat_ai.shared.types import ChatTurn
from goat_ai.telemetry.latency_metrics import get_inference_snapshot


class FakeLLMClient:
    """Minimal LLMClient Protocol implementation for tests."""

    def list_model_names(self) -> list[str]:
        return ["test-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return [], None

    def get_model_capabilities(self, model: str) -> list[str]:
        return self.describe_model_for_api(model)[0]

    def get_model_context_length(self, model: str) -> int | None:
        return self.describe_model_for_api(model)[1]

    def supports_tool_calling(self, model: str) -> bool:
        return False

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
        last_user_images_base64: list[str] | None = None,
    ) -> Generator[str, None, None]:
        yield "Hello"
        yield "!"

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]:
        yield from self.stream_tokens(
            model,
            messages,
            system_prompt,
            ollama_options=ollama_options,
        )

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

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        return ""


class FakeChartToolLLMClient(FakeLLMClient):
    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return ["completion", "tools"], None

    def get_model_capabilities(self, model: str) -> list[str]:
        return self.describe_model_for_api(model)[0]

    def get_model_context_length(self, model: str) -> int | None:
        return self.describe_model_for_api(model)[1]

    def supports_tool_calling(self, model: str) -> bool:
        return True

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]:
        yield ToolCallPlan(
            assistant_message={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "generate_chart_v2",
                            "arguments": {
                                "chart_type": "line",
                                "title": "Revenue trend",
                                "x_key": "month",
                                "series": [
                                    {
                                        "key": "revenue",
                                        "name": "Revenue",
                                        "aggregate": "none",
                                    }
                                ],
                            },
                        }
                    }
                ],
            },
            tool_name="generate_chart_v2",
            arguments={
                "version": "2.0",
                "chart_type": "line",
                "title": "Revenue trend",
                "x_key": "month",
                "series": [{"key": "revenue", "name": "Revenue", "aggregate": "none"}],
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


class FakeWebSearchToolLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.tools_seen: list[dict[str, object]] = []
        self.followup_messages: list[dict[str, object]] = []

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return ["completion", "tools"], None

    def get_model_capabilities(self, model: str) -> list[str]:
        return self.describe_model_for_api(model)[0]

    def get_model_context_length(self, model: str) -> int | None:
        return self.describe_model_for_api(model)[1]

    def supports_tool_calling(self, model: str) -> bool:
        return True

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]:
        _ = model, messages, system_prompt, ollama_options
        self.tools_seen = tools
        yield ToolCallPlan(
            assistant_message={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "web_search",
                            "arguments": {
                                "query": "Serper GOAT AI search",
                                "max_results": 2,
                            },
                        }
                    }
                ],
            },
            tool_name="web_search",
            arguments={"query": "Serper GOAT AI search", "max_results": 2},
        )

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        _ = model, tools, ollama_options
        self.followup_messages = followup_messages
        yield "Search answer citing https://example.com/news"


class FakeSearchFallbackLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.followup_messages: list[dict[str, object]] = []
        self.tools_seen: list[dict[str, object]] = []

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]:
        _ = model, messages, system_prompt, tools, ollama_options
        raise AssertionError("native tool path should not be used")

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        _ = model, ollama_options
        self.followup_messages = followup_messages
        self.tools_seen = tools
        yield "Fallback search answer citing https://example.com/news"


class FakeLongStreamingLLMClient(FakeLLMClient):
    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
        last_user_images_base64: list[str] | None = None,
    ) -> Generator[str, None, None]:
        yield "This is the first chunk."
        yield " Here is the second chunk."
        yield " Finally the third chunk."


def _search_settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test system prompt",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        data_dir=root / "data",
        serper_api_key="serper-test-key",
    )


def _example_search_hit() -> WebSearchHit:
    return WebSearchHit(
        title="Example News",
        url="https://example.com/news",
        snippet="Current search evidence.",
        rank=1,
    )


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
            conversation_logger=SQLiteConversationLogger(db_path),
        ):
            events.append(chunk)

        token_lines = [e for e in events if "Hello" in e or "!" in e]
        assert len(token_lines) >= 2
        assert any('"type": "done"' in e for e in events)

        snap = get_inference_snapshot()
        assert snap["chat_sample_count"] == 1
        assert float(snap["chat_avg_ms"]) >= 0.0
        assert snap["first_token_sample_count"] == 1
        assert float(snap["first_token_avg_ms"]) >= 0.0
    finally:
        tmp.cleanup()


def test_stream_chat_sse_explicit_search_uses_native_web_search_tool() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    settings = _search_settings(Path(tmp.name))
    log_service.init_db(db_path)
    llm = FakeWebSearchToolLLMClient()
    try:
        with patch(
            "goat_ai.search.tool.search_web",
            return_value=[_example_search_hit()],
        ) as search_web:
            events = list(
                stream_chat_sse(
                    llm=llm,
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user",
                            content="Please search the latest GOAT AI news.",
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    settings=settings,
                )
            )

        assert search_web.call_args.kwargs["query"] == "Serper GOAT AI search"
        assert search_web.call_args.kwargs["max_results"] == 2
        assert llm.tools_seen[0]["function"]["name"] == "web_search"
        assert any(
            message.get("role") == "tool" and "https://example.com/news" in str(message)
            for message in llm.followup_messages
        )
        assert any("Search answer citing https://example.com/news" in e for e in events)
        assert any('"type": "done"' in e for e in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_non_search_prompt_does_not_trigger_web_search() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    settings = _search_settings(Path(tmp.name))
    log_service.init_db(db_path)
    try:
        with patch(
            "goat_ai.search.tool.search_web",
            side_effect=AssertionError("search should not run"),
        ):
            events = list(
                stream_chat_sse(
                    llm=FakeLLMClient(),
                    model="test-model",
                    messages=[ChatMessage(role="user", content="Say hello.")],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    settings=settings,
                )
            )

        assert any("Hello" in event for event in events)
        assert any('"type": "done"' in event for event in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_search_falls_back_when_native_tools_are_unsupported() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    settings = _search_settings(Path(tmp.name))
    log_service.init_db(db_path)
    llm = FakeSearchFallbackLLMClient()
    try:
        with patch(
            "goat_ai.search.tool.search_web",
            return_value=[_example_search_hit()],
        ) as search_web:
            events = list(
                stream_chat_sse(
                    llm=llm,
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user",
                            content="查一下 GOAT AI 最新搜索能力",
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    settings=settings,
                )
            )

        assert search_web.call_args.kwargs["query"] == "查一下 GOAT AI 最新搜索能力"
        assert llm.tools_seen[0]["function"]["name"] == "web_search"
        assert any(
            message.get("role") == "system"
            and "Public web search results" in str(message.get("content"))
            and "https://example.com/news" in str(message.get("content"))
            for message in llm.followup_messages
        )
        assert any(
            "Fallback search answer citing https://example.com/news" in e
            for e in events
        )
        assert any('"type": "done"' in e for e in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_search_failure_returns_unavailable_answer() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    settings = _search_settings(Path(tmp.name))
    log_service.init_db(db_path)
    try:
        with patch(
            "goat_ai.search.tool.search_web",
            side_effect=WebSearchError("boom"),
        ):
            events = list(
                stream_chat_sse(
                    llm=FakeSearchFallbackLLMClient(),
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user",
                            content="Search online for the latest GOAT AI status.",
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    settings=settings,
                )
            )

        body = "".join(events)
        assert "Search is currently unavailable" in body
        assert "https://example.com/news" not in body
        assert '"type": "done"' in body
    finally:
        tmp.cleanup()


def test_sse_event_format() -> None:
    assert (
        sse_event({"type": "token", "token": "x"})
        == 'data: {"type": "token", "token": "x"}\n\n'
    )


def test_stream_chat_sse_emits_chart_only_after_native_tool_followup_completes() -> (
    None
):
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
                    ChatMessage(
                        role="assistant", content="I have loaded the file context."
                    ),
                    ChatMessage(role="user", content="Please chart the revenue trend."),
                ],
                system_prompt="You are helpful.",
                ip="127.0.0.1",
                conversation_logger=SQLiteConversationLogger(db_path),
                session_repository=SQLiteSessionRepository(db_path),
                title_generator=OllamaTitleGenerator(FakeChartToolLLMClient()),
            )
        )

        chart_index = next(
            i for i, event in enumerate(events) if '"type": "chart_spec"' in event
        )
        answer_index = next(
            i
            for i, event in enumerate(events)
            if "Here is the chart-driven answer." in event
        )
        assert answer_index < chart_index
        assert any('"type": "done"' in event for event in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_allows_tool_chart_without_uploaded_file_context() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    log_service.init_db(db_path)
    try:
        events = list(
            stream_chat_sse(
                llm=FakeChartToolLLMClient(),
                model="test-model",
                messages=[ChatMessage(role="user", content="生成一个典型的饼状图表")],
                system_prompt="You are helpful.",
                ip="127.0.0.1",
                conversation_logger=SQLiteConversationLogger(db_path),
            )
        )

        assert any('"type": "chart_spec"' in event for event in events)
        assert any('"type": "done"' in event for event in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_does_not_emit_chart_from_legacy_pseudo_block_when_tools_unsupported() -> (
    None
):
    class FakeLegacyChartBlockLLMClient(FakeLLMClient):
        def stream_tokens(
            self,
            model: str,
            messages: list[ChatTurn],
            system_prompt: str,
            *,
            ollama_options: dict[str, float | int] | None = None,
            last_user_images_base64: list[str] | None = None,
        ) -> Generator[str, None, None]:
            yield "Analysis summary.\n\n:::chart\n"
            yield '{"type":"line","title":"Revenue trend","xKey":"month","series":[{"key":"revenue","name":"Revenue"}]}\n:::'

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
                llm=FakeLegacyChartBlockLLMClient(),
                model="test-model",
                messages=[
                    ChatMessage(role="user", content=file_context),
                    ChatMessage(
                        role="assistant", content="I have loaded the file context."
                    ),
                    ChatMessage(role="user", content="Please chart the revenue trend."),
                ],
                system_prompt="You are helpful.",
                ip="127.0.0.1",
                conversation_logger=SQLiteConversationLogger(db_path),
            )
        )

        assert not any('"type": "chart_spec"' in event for event in events)
        assert any('"type": "done"' in event for event in events)
    finally:
        tmp.cleanup()


def test_stream_chat_sse_emits_tokens_before_done_with_safeguard_enabled() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "chat_logs.db"
    log_service.init_db(db_path)
    try:
        events = list(
            stream_chat_sse(
                llm=FakeLongStreamingLLMClient(),
                model="test-model",
                messages=[ChatMessage(role="user", content="Share a brief update.")],
                system_prompt="You are helpful.",
                ip="127.0.0.1",
                conversation_logger=SQLiteConversationLogger(db_path),
                safeguard_service=RuleBasedSafeguardService(),
            )
        )

        first_token_index = next(
            i for i, event in enumerate(events) if '"type": "token"' in event
        )
        done_index = next(
            i for i, event in enumerate(events) if '"type": "done"' in event
        )
        assert first_token_index < done_index
    finally:
        tmp.cleanup()
