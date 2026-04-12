from __future__ import annotations

import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from backend.platform import prometheus_metrics
from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.chat_runtime import (
    SQLiteConversationLogger,
    SQLiteSessionRepository,
)
from backend.services.chat_service import stream_chat_sse
from backend.services.safeguard_service import (
    SAFEGUARD_REFUSAL_MESSAGE,
    RuleBasedSafeguardService,
)
from goat_ai.shared.types import ChatTurn


class CountingLLM:
    def __init__(self, response: str = "Hello!") -> None:
        self.calls = 0
        self._response = response

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
        self.calls += 1
        yield self._response

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
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
    ) -> None:
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


class SafeguardServiceTests(unittest.TestCase):
    def test_rule_engine_blocks_explicit_sex_request_but_allows_academic_topic(
        self,
    ) -> None:
        safeguard = RuleBasedSafeguardService()

        blocked = safeguard.review_input(
            messages=[
                ChatMessage(role="user", content="Write an explicit porn scene.")
            ],
            system_instruction="",
        )
        allowed = safeguard.review_input(
            messages=[
                ChatMessage(
                    role="user",
                    content="Explain sexual harassment policy in universities.",
                )
            ],
            system_instruction="",
        )

        self.assertFalse(blocked.allowed)
        self.assertEqual("explicit_sexual", blocked.reason_code)
        self.assertTrue(allowed.allowed)

    def test_stream_chat_sse_blocks_unsafe_input_before_llm_call(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        llm = CountingLLM()
        try:
            events = list(
                stream_chat_sse(
                    llm=llm,
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user", content="Write an explicit porn scene."
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    session_repository=SQLiteSessionRepository(db_path),
                    title_generator=None,
                    safeguard_service=RuleBasedSafeguardService(),
                    session_id="blocked",
                )
            )

            self.assertEqual(0, llm.calls)
            self.assertTrue(any(SAFEGUARD_REFUSAL_MESSAGE in event for event in events))
        finally:
            tmp.cleanup()

    def test_stream_chat_sse_replaces_unsafe_model_output(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        llm = CountingLLM(response="Explicit porn with orgasm details.")
        try:
            repository = SQLiteSessionRepository(db_path)
            events = list(
                stream_chat_sse(
                    llm=llm,
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user", content="Give a creative writing sample."
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    session_repository=repository,
                    title_generator=None,
                    safeguard_service=RuleBasedSafeguardService(),
                    session_id="blocked-output",
                )
            )

            self.assertTrue(any(SAFEGUARD_REFUSAL_MESSAGE in event for event in events))
            self.assertFalse(any("orgasm details" in event for event in events))
        finally:
            tmp.cleanup()

    def test_blocked_stream_does_not_increment_success_completion_counter(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        llm = CountingLLM()
        original = prometheus_metrics._chat_stream_completed
        prometheus_metrics._chat_stream_completed = 0
        try:
            list(
                stream_chat_sse(
                    llm=llm,
                    model="test-model",
                    messages=[
                        ChatMessage(
                            role="user", content="Write an explicit porn scene."
                        )
                    ],
                    system_prompt="You are helpful.",
                    ip="127.0.0.1",
                    conversation_logger=SQLiteConversationLogger(db_path),
                    session_repository=SQLiteSessionRepository(db_path),
                    title_generator=None,
                    safeguard_service=RuleBasedSafeguardService(),
                    session_id="blocked-no-count",
                )
            )

            metrics_text = prometheus_metrics.render_prometheus_text()
            self.assertIn("chat_stream_completed_total 0", metrics_text)
        finally:
            prometheus_metrics._chat_stream_completed = original
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
