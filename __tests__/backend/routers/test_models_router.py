from __future__ import annotations

import unittest
import tempfile
from collections.abc import Generator
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    FastAPI = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

from goat_ai.llm.ollama_client import ToolCallPlan
from goat_ai.shared.types import ChatTurn
from goat_ai.config.settings import Settings

if FastAPI is not None:
    from backend.platform.config import get_settings
    from backend.platform.exception_handlers import register_exception_handlers
    from backend.platform.dependencies import get_llm_client
    from backend.routers import models


class FakeModelsLLMClient:
    def list_model_names(self) -> list[str]:
        return ["gemma3:4b", "qwen3:4b", "rogue-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        if model == "qwen3:4b":
            return ["completion", "tools"], 32768
        return ["completion"], None

    def get_model_capabilities(self, model: str) -> list[str]:
        return self.describe_model_for_api(model)[0]

    def get_model_context_length(self, model: str) -> int | None:
        return self.describe_model_for_api(model)[1]

    def supports_tool_calling(self, model: str) -> bool:
        return "tools" in self.get_model_capabilities(model)

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
        last_user_images_base64: list[str] | None = None,
    ) -> Generator[str, None, None]:
        if False:
            yield ""
        return

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


@unittest.skipUnless(
    FastAPI is not None and TestClient is not None, "fastapi not installed"
)
class ModelsRouterIntegrationTests(unittest.TestCase):
    def _settings(self, *, deploy_mode: int) -> Settings:
        root = Path(tempfile.mkdtemp())
        return Settings(
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
            deploy_mode=deploy_mode,
        )

    def _build_app(self, *, deploy_mode: int) -> None:
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(models.router, prefix="/api")
        app.dependency_overrides[get_llm_client] = lambda: FakeModelsLLMClient()
        app.dependency_overrides[get_settings] = lambda: self._settings(
            deploy_mode=deploy_mode
        )
        self.client = TestClient(app)

    def setUp(self) -> None:
        self._build_app(deploy_mode=2)

    def test_models_endpoint_filters_to_public_allowlist_for_remote_deploy(
        self,
    ) -> None:
        response = self.client.get("/api/models")

        self.assertEqual(200, response.status_code)
        self.assertEqual(["qwen3:4b", "gemma3:4b"], response.json()["models"])

    def test_models_endpoint_returns_all_installed_models_for_local_deploy(
        self,
    ) -> None:
        self._build_app(deploy_mode=0)

        response = self.client.get("/api/models")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            ["gemma3:4b", "qwen3:4b", "rogue-model"], response.json()["models"]
        )

    def test_model_capabilities_endpoint_reports_tool_support(self) -> None:
        response = self.client.get(
            "/api/models/capabilities", params={"model": "qwen3:4b"}
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("qwen3:4b", payload["model"])
        self.assertEqual(["completion", "tools"], payload["capabilities"])
        self.assertTrue(payload["supports_tool_calling"])
        self.assertTrue(payload["supports_chart_tools"])
        self.assertFalse(payload["supports_vision"])
        self.assertEqual(32768, payload["context_length"])

    def test_model_capabilities_endpoint_rejects_disallowed_model_for_remote_deploy(
        self,
    ) -> None:
        response = self.client.get(
            "/api/models/capabilities", params={"model": "rogue-model"}
        )

        self.assertEqual(422, response.status_code)
        self.assertIn("not enabled on this deployment", response.json()["detail"])

    def test_model_capabilities_endpoint_allows_non_public_model_for_local_deploy(
        self,
    ) -> None:
        self._build_app(deploy_mode=0)

        response = self.client.get(
            "/api/models/capabilities", params={"model": "rogue-model"}
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("rogue-model", response.json()["model"])


if __name__ == "__main__":
    unittest.main()
