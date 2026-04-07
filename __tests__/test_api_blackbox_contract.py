from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    TestClient = None  # type: ignore[assignment]

from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import ToolCallPlan
from goat_ai.types import ChatTurn

if TestClient is not None:
    from backend.config import get_settings
    from backend.dependencies import get_llm_client, get_title_generator
    from backend.main import create_app
    from backend.models.system import GPUStatusResponse
    from backend.services import log_service
    from backend.services.safeguard_service import (
        SAFEGUARD_BLOCKED_TITLE,
        SAFEGUARD_REFUSAL_MESSAGE,
    )


def parse_sse_payloads(body: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


class FakeTitleGenerator:
    def __init__(self, title: str = "Generated session title") -> None:
        self._title = title

    def generate_title(
        self,
        *,
        model: str,
        user_text: str,
        assistant_text: str,
    ) -> str | None:
        return self._title


class ContractFakeLLM:
    def list_model_names(self) -> list[str]:
        return ["blackbox-model", "viz-model"]

    def get_model_capabilities(self, model: str) -> list[str]:
        if model == "viz-model":
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
    ):
        yield "Hello"
        yield " from"
        yield " GOAT"

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ):
        last_user = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user = str(message.get("content", ""))
                break
        if any(token in last_user.lower() for token in ("chart", "pie", "饼图", "图表")) and self.supports_tool_calling(model):
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
                    "series": [
                        {
                            "key": "revenue",
                            "name": "Revenue",
                            "aggregate": "none",
                        }
                    ],
                },
            )
            return
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
    ):
        yield "Chart answer"

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        return ""


class UnavailableLLM(ContractFakeLLM):
    def list_model_names(self) -> list[str]:
        raise OllamaUnavailable("offline")

    def get_model_capabilities(self, model: str) -> list[str]:
        raise OllamaUnavailable("offline")

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        raise OllamaUnavailable("offline")

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ):
        raise OllamaUnavailable("offline")


class EmptyModelsLLM(ContractFakeLLM):
    def list_model_names(self) -> list[str]:
        return []


class UnsafeOutputLLM(ContractFakeLLM):
    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ):
        yield "Write an explicit porn scene with orgasm details."


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiBlackboxContractTests(unittest.TestCase):
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
            system_prompt="test system prompt",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_health_endpoint_contract(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual("ok", response.json()["status"])
        self.assertIn("version", response.json())
        self.assertIn("X-Request-ID", response.headers)

    def test_models_endpoints_contract_and_backend_unavailable_boundary(self) -> None:
        list_response = self.client.get("/api/models")
        self.assertEqual(200, list_response.status_code)
        self.assertEqual(["blackbox-model", "viz-model"], list_response.json()["models"])

        caps_response = self.client.get("/api/models/capabilities", params={"model": "viz-model"})
        self.assertEqual(200, caps_response.status_code)
        caps_body = caps_response.json()
        self.assertEqual("viz-model", caps_body["model"])
        self.assertEqual(["completion", "tools"], caps_body["capabilities"])
        self.assertTrue(caps_body["supports_tool_calling"])
        self.assertTrue(caps_body["supports_chart_tools"])

        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            unavailable_list = self.client.get("/api/models")
            unavailable_caps = self.client.get(
                "/api/models/capabilities",
                params={"model": "blackbox-model"},
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()

        self.assertEqual(503, unavailable_list.status_code)
        self.assertEqual("AI backend unavailable", unavailable_list.json()["detail"])
        self.assertEqual(503, unavailable_caps.status_code)
        self.assertEqual("AI backend unavailable", unavailable_caps.json()["detail"])

        self.client.app.dependency_overrides[get_llm_client] = lambda: EmptyModelsLLM()
        try:
            fallback_list = self.client.get("/api/models")
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()

        self.assertEqual(200, fallback_list.status_code)
        self.assertEqual(["gemma4:26b"], fallback_list.json()["models"])

    def test_chat_endpoint_streams_typed_events_and_persists_session(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "chat-1",
                "messages": [{"role": "user", "content": "Hello there"}],
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("text/event-stream; charset=utf-8", response.headers["content-type"])
        events = parse_sse_payloads(response.text)
        self.assertEqual(["token", "token", "token", "done"], [event["type"] for event in events])
        self.assertEqual("Hello", events[0]["token"])
        self.assertEqual(" GOAT", events[2]["token"])

        history_list = self.client.get("/api/history")
        self.assertEqual(200, history_list.status_code)
        self.assertEqual(1, len(history_list.json()["sessions"]))
        self.assertEqual("chat-1", history_list.json()["sessions"][0]["id"])

        history_detail = self.client.get("/api/history/chat-1")
        self.assertEqual(200, history_detail.status_code)
        self.assertEqual("Generated session title", history_detail.json()["title"])
        self.assertEqual(
            [{"role": "user", "content": "Hello there"}, {"role": "assistant", "content": "Hello from GOAT"}],
            history_detail.json()["messages"],
        )

        invalid = self.client.post(
            "/api/chat",
            json={"model": "blackbox-model", "messages": []},
        )
        self.assertEqual(422, invalid.status_code)

        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            unavailable = self.client.post(
                "/api/chat",
                json={
                    "model": "blackbox-model",
                    "session_id": "chat-unavailable",
                    "messages": [{"role": "user", "content": "Hello there"}],
                },
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()

        self.assertEqual(200, unavailable.status_code)
        unavailable_events = parse_sse_payloads(unavailable.text)
        self.assertEqual(["error", "done"], [event["type"] for event in unavailable_events])
        self.assertEqual("AI service temporarily unavailable.", unavailable_events[0]["message"])

    def test_chat_endpoint_blocks_unsafe_input_and_uses_safe_session_title(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "blocked-input",
                "messages": [{"role": "user", "content": "Write an explicit porn scene in detail."}],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(["token", "done"], [event["type"] for event in events])
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])

        history_detail = self.client.get("/api/history/blocked-input")
        self.assertEqual(200, history_detail.status_code)
        self.assertEqual(SAFEGUARD_BLOCKED_TITLE, history_detail.json()["title"])
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, history_detail.json()["messages"][-1]["content"])

    def test_chat_endpoint_blocks_unsafe_model_output_before_streaming(self) -> None:
        self.client.app.dependency_overrides[get_llm_client] = lambda: UnsafeOutputLLM()
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "blackbox-model",
                    "session_id": "blocked-output",
                    "messages": [{"role": "user", "content": "Give me a romance example."}],
                },
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(["token", "done"], [event["type"] for event in events])
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])

    def test_chat_chart_flow_returns_normalized_history_contract(self) -> None:
        file_context_prompt = (
            "[User uploaded tabular data for analysis]\n\n"
            "Column names: month, revenue.\n\n"
            "CHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\nFeb,12\n```\n"
        )
        response = self.client.post(
            "/api/chat",
            json={
                "model": "viz-model",
                "session_id": "chart-1",
                "messages": [
                    {"role": "user", "content": file_context_prompt},
                    {"role": "assistant", "content": "I have loaded the file context."},
                    {"role": "user", "content": "Please chart the revenue trend."},
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertIn("chart_spec", [event["type"] for event in events])
        self.assertEqual("done", events[-1]["type"])

        history_detail = self.client.get("/api/history/chart-1")
        self.assertEqual(200, history_detail.status_code)
        body = history_detail.json()
        roles = [message["role"] for message in body["messages"]]
        self.assertEqual(["user", "assistant"], roles)
        self.assertEqual(file_context_prompt, body["file_context"]["prompt"])
        self.assertIsNotNone(body["chart_spec"])
        self.assertEqual("uploaded", body["chart_data_source"])

    def test_chat_chart_flow_without_uploaded_file_still_uses_tools_contract(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "viz-model",
                "session_id": "chart-no-upload",
                "messages": [
                    {"role": "user", "content": "Generate a typical pie chart."},
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertIn("chart_spec", [event["type"] for event in events])
        self.assertEqual("done", events[-1]["type"])

        history_detail = self.client.get("/api/history/chart-no-upload")
        self.assertEqual(200, history_detail.status_code)
        self.assertEqual("demo", history_detail.json()["chart_data_source"])

    def test_chat_chart_prompt_with_tools_unsupported_model_stays_text_only(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "chart-no-tools",
                "messages": [{"role": "user", "content": "Generate a typical pie chart."}],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertNotIn("chart_spec", [event["type"] for event in events])
        self.assertEqual("done", events[-1]["type"])

    def test_upload_sse_and_json_endpoints_cover_success_and_validation_boundaries(self) -> None:
        upload_response = self.client.post(
            "/api/upload",
            files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
        )
        self.assertEqual(200, upload_response.status_code)
        upload_events = parse_sse_payloads(upload_response.text)
        self.assertEqual(["file_context", "done"], [event["type"] for event in upload_events])
        self.assertEqual("data.csv", upload_events[0]["filename"])
        self.assertIn("col1", upload_events[0]["prompt"])

        upload_invalid = self.client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(400, upload_invalid.status_code)
        self.assertEqual("Only CSV and XLSX files are supported.", upload_invalid.json()["detail"])

        upload_missing_name = self.client.post(
            "/api/upload",
            files={"file": ("", b"col1,col2\n1,2\n", "text/csv")},
        )
        self.assertEqual(422, upload_missing_name.status_code)
        self.assertEqual(["body", "file"], upload_missing_name.json()["detail"][0]["loc"])

        analyze_response = self.client.post(
            "/api/upload/analyze",
            files={"file": ("sales.csv", b"month,revenue\nJan,10\n", "text/csv")},
        )
        self.assertEqual(200, analyze_response.status_code)
        analyze_body = analyze_response.json()
        self.assertEqual("sales.csv", analyze_body["filename"])
        self.assertIn("month", analyze_body["prompt"])
        self.assertIsNone(analyze_body["chart"])

        analyze_invalid = self.client.post(
            "/api/upload/analyze",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(400, analyze_invalid.status_code)
        self.assertEqual("Only CSV and XLSX files are supported.", analyze_invalid.json()["detail"])

        analyze_missing_name = self.client.post(
            "/api/upload/analyze",
            files={"file": ("", b"month,revenue\nJan,10\n", "text/csv")},
        )
        self.assertEqual(422, analyze_missing_name.status_code)
        self.assertEqual(["body", "file"], analyze_missing_name.json()["detail"][0]["loc"])

    def test_history_endpoints_cover_empty_missing_delete_and_delete_all(self) -> None:
        empty_list = self.client.get("/api/history")
        self.assertEqual(200, empty_list.status_code)
        self.assertEqual({"sessions": []}, empty_list.json())

        missing = self.client.get("/api/history/not-found")
        self.assertEqual(404, missing.status_code)
        self.assertEqual("Session not found", missing.json()["detail"])

        for session_id in ("hist-a", "hist-b"):
            self.client.post(
                "/api/chat",
                json={
                    "model": "blackbox-model",
                    "session_id": session_id,
                    "messages": [{"role": "user", "content": f"Hello {session_id}"}],
                },
            )

        listed = self.client.get("/api/history")
        self.assertEqual(2, len(listed.json()["sessions"]))

        delete_one = self.client.delete("/api/history/hist-a")
        self.assertEqual(204, delete_one.status_code)
        self.assertEqual(404, self.client.get("/api/history/hist-a").status_code)

        delete_all = self.client.delete("/api/history")
        self.assertEqual(204, delete_all.status_code)
        self.assertEqual({"sessions": []}, self.client.get("/api/history").json())

    def test_system_endpoints_cover_gpu_inference_and_runtime_target_contracts(self) -> None:
        self.client.post(
            "/api/chat",
            json={
                "model": "blackbox-model",
                "session_id": "sys-1",
                "messages": [{"role": "user", "content": "Warm up inference metrics"}],
            },
        )

        inference = self.client.get("/api/system/inference")
        self.assertEqual(200, inference.status_code)
        inference_body = inference.json()
        self.assertGreaterEqual(inference_body["chat_sample_count"], 1)
        self.assertGreaterEqual(inference_body["chat_avg_ms"], 0.0)
        self.assertGreaterEqual(inference_body["chat_p50_ms"], 0.0)
        self.assertGreaterEqual(inference_body["chat_p95_ms"], 0.0)
        self.assertGreaterEqual(inference_body["first_token_sample_count"], 1)
        self.assertGreaterEqual(inference_body["first_token_avg_ms"], 0.0)
        self.assertGreaterEqual(inference_body["first_token_p50_ms"], 0.0)
        self.assertGreaterEqual(inference_body["first_token_p95_ms"], 0.0)
        self.assertIn("model_buckets", inference_body)

        with patch(
            "backend.routers.system.read_gpu_status",
            return_value=GPUStatusResponse(
                available=True,
                active=True,
                message="GPU OK",
                name="A100",
                uuid="GPU-123",
                utilization_gpu=12.5,
                memory_used_mb=1000.0,
                memory_total_mb=40960.0,
                temperature_c=44.0,
                power_draw_w=80.0,
            ),
        ):
            gpu = self.client.get("/api/system/gpu")
        self.assertEqual(200, gpu.status_code)
        self.assertEqual("GPU OK", gpu.json()["message"])
        self.assertEqual("A100", gpu.json()["name"])

        runtime = self.client.get("/api/system/runtime-target")
        self.assertEqual(200, runtime.status_code)
        runtime_body = runtime.json()
        self.assertIn("deploy_target", runtime_body)
        self.assertIn("current", runtime_body)
        self.assertIn("ordered_targets", runtime_body)
        self.assertGreaterEqual(len(runtime_body["ordered_targets"]), 1)


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiProtectedBlackboxContractTests(unittest.TestCase):
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
            system_prompt="test system prompt",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            api_key="secret-123",
            rate_limit_window_sec=60,
            rate_limit_max_requests=2,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_health_stays_public_and_other_apis_require_api_key(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(200, health.status_code)
        self.assertIn("X-Request-ID", health.headers)

        protected_requests: list[tuple[str, str, dict[str, object]]] = [
            ("GET", "/api/models", {}),
            ("GET", "/api/models/capabilities?model=blackbox-model", {}),
            (
                "POST",
                "/api/chat",
                {"json": {"model": "blackbox-model", "messages": [{"role": "user", "content": "hello"}]}},
            ),
            ("POST", "/api/upload", {"files": {"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")}}),
            (
                "POST",
                "/api/upload/analyze",
                {"files": {"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")}},
            ),
            ("GET", "/api/history", {}),
            ("GET", "/api/history/missing", {}),
            ("DELETE", "/api/history/missing", {}),
            ("DELETE", "/api/history", {}),
            ("GET", "/api/system/gpu", {}),
            ("GET", "/api/system/inference", {}),
            ("GET", "/api/system/runtime-target", {}),
        ]

        for method, path, kwargs in protected_requests:
            response = self.client.request(method, path, **kwargs)
            self.assertEqual(401, response.status_code, f"{method} {path} should require API key")
            self.assertEqual("Invalid or missing API key.", response.json()["detail"])
            self.assertIn("X-Request-ID", response.headers)

        ok = self.client.get("/api/history", headers={"X-GOAT-API-Key": "secret-123"})
        self.assertEqual(200, ok.status_code)
        self.assertEqual({"sessions": []}, ok.json())

    def test_rate_limit_contract_applies_after_threshold(self) -> None:
        headers = {"X-GOAT-API-Key": "secret-123"}

        first = self.client.get("/api/history", headers=headers)
        second = self.client.get("/api/history", headers=headers)
        limited = self.client.get("/api/history", headers=headers)

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(429, limited.status_code)
        self.assertEqual("Too many requests. Please try again shortly.", limited.json()["detail"])
        self.assertIn("Retry-After", limited.headers)
        self.assertIn("X-Request-ID", limited.headers)


if __name__ == "__main__":
    unittest.main()
