from __future__ import annotations

import unittest
from collections.abc import Generator

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    FastAPI = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

from goat_ai.ollama_client import ToolCallPlan
from goat_ai.types import ChatTurn

if FastAPI is not None:
    from backend.dependencies import get_llm_client
    from backend.routers import models


class FakeModelsLLMClient:
    def list_model_names(self) -> list[str]:
        return ["gemma4:26b", "qwen3"]

    def get_model_capabilities(self, model: str) -> list[str]:
        if model == "qwen3":
            return ["completion", "tools"]
        return ["completion"]

    def supports_tool_calling(self, model: str) -> bool:
        return "tools" in self.get_model_capabilities(model)

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        if False:
            yield ""
        return

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


@unittest.skipUnless(FastAPI is not None and TestClient is not None, "fastapi not installed")
class ModelsRouterIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(models.router, prefix="/api")
        app.dependency_overrides[get_llm_client] = lambda: FakeModelsLLMClient()
        self.client = TestClient(app)

    def test_model_capabilities_endpoint_reports_tool_support(self) -> None:
        response = self.client.get("/api/models/capabilities", params={"model": "qwen3"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("qwen3", payload["model"])
        self.assertEqual(["completion", "tools"], payload["capabilities"])
        self.assertTrue(payload["supports_tool_calling"])
        self.assertTrue(payload["supports_chart_tools"])


if __name__ == "__main__":
    unittest.main()
