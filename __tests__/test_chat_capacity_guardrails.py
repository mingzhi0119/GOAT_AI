from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]

from backend.api_errors import REQUEST_VALIDATION_ERROR
from goat_ai.config import Settings

if TestClient is not None:
    from backend.config import get_settings
    from backend.dependencies import get_llm_client, get_title_generator
    from backend.main import create_app
    from backend.services import log_service
    from goat_ai.types import ChatTurn


class _FakeLLM:
    def list_model_names(self) -> list[str]:
        return ["blackbox-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return ["completion"], None

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
    ):
        yield "ok"

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ):
        yield from self.stream_tokens(
            model, messages, system_prompt, ollama_options=ollama_options
        )

    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ):
        return None

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ):
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
        return "title"


class _FakeTitle:
    def generate_title(
        self, *, model: str, user_text: str, assistant_text: str
    ) -> str | None:
        return "title"


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ChatCapacityGuardrailsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            ready_skip_ollama_probe=True,
            max_chat_messages=2,
            max_chat_payload_bytes=120,
        )
        log_service.init_db(self.settings.log_db_path)
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: _FakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: _FakeTitle()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_rejects_message_count_over_limit(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "messages": [
                    {"role": "user", "content": "a"},
                    {"role": "assistant", "content": "b"},
                    {"role": "user", "content": "c"},
                ],
            },
        )
        self.assertEqual(422, response.status_code)
        body = response.json()
        self.assertEqual(REQUEST_VALIDATION_ERROR, body["code"])
        self.assertIn("max message count", body["detail"])

    def test_rejects_payload_bytes_over_limit(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "x" * 400}],
            },
        )
        self.assertEqual(422, response.status_code)
        body = response.json()
        self.assertEqual(REQUEST_VALIDATION_ERROR, body["code"])
        self.assertIn("max payload bytes", body["detail"])


if __name__ == "__main__":
    unittest.main()
