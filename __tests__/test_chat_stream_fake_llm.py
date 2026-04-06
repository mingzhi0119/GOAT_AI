"""stream_chat_sse with a fake LLM client (no Ollama)."""
from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.chat_service import stream_chat_sse, sse_event
from goat_ai.latency_metrics import get_inference_snapshot
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
