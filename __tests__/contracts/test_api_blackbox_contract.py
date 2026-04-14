from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    TestClient = None  # type: ignore[assignment]

from backend.api_errors import (
    AUTH_INVALID_API_KEY,
    ARTIFACT_NOT_FOUND,
    BAD_REQUEST,
    FEATURE_UNAVAILABLE,
    INFERENCE_BACKEND_UNAVAILABLE,
    KNOWLEDGE_NOT_FOUND,
    MEDIA_NOT_FOUND,
    NOT_FOUND,
    RATE_LIMITED,
    RESOURCE_CONFLICT,
    REQUEST_VALIDATION_ERROR,
    VISION_NOT_SUPPORTED,
)
from goat_ai.config.settings import Settings
from goat_ai.shared.exceptions import OllamaUnavailable
from goat_ai.llm.ollama_client import ToolCallPlan
from goat_ai.shared.types import ChatTurn
from backend.services.workbench_web_search import WorkbenchWebSearchHit

if TestClient is not None:
    from backend.platform.config import get_settings
    from backend.platform.dependencies import (
        get_code_sandbox_execution_dispatcher,
        get_code_sandbox_provider,
        get_llm_client,
        get_title_generator,
        get_workbench_task_dispatcher,
    )
    from backend.main import create_app
    from backend.models.system import GPUStatusResponse
    from backend.services import log_service
    from backend.services.code_sandbox_provider import (
        SandboxProviderLogChunk,
        SandboxProviderRequest,
        SandboxProviderResult,
    )
    from backend.services.exceptions import PersistenceWriteError
    from backend.services.session_message_codec import SESSION_PAYLOAD_VERSION
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


class FakeCodeSandboxProvider:
    provider_name = "fake-docker"

    def run_stream(self, request: SandboxProviderRequest, *, cancel_requested=None):
        output_files: list[dict[str, object]] = []
        if request.command == "touch outputs/report.txt":
            output_files.append({"path": "report.txt", "byte_size": 12})
        if request.command == "printf async":
            yield SandboxProviderLogChunk(
                stream_name="stdout",
                created_at="2026-04-10T00:00:00Z",
                text="async log line\n",
            )
        if request.command == "hold-cancellable":
            yield SandboxProviderLogChunk(
                stream_name="stdout",
                created_at="2026-04-10T00:00:00Z",
                text="holding\n",
            )
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if cancel_requested is not None and cancel_requested():
                    yield SandboxProviderResult(
                        provider_name=self.provider_name,
                        exit_code=None,
                        stdout="",
                        stderr="",
                        timed_out=False,
                        cancelled=True,
                        error_detail="Execution cancelled by request.",
                        output_files=[],
                    )
                    return
                time.sleep(0.02)
            yield SandboxProviderResult(
                provider_name=self.provider_name,
                exit_code=0,
                stdout="finished after hold",
                stderr="",
                timed_out=False,
                cancelled=False,
                error_detail=None,
                output_files=[],
            )
            return
        if request.command == "sleep-forever":
            yield SandboxProviderResult(
                provider_name=self.provider_name,
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=True,
                cancelled=False,
                error_detail="Execution timed out.",
                output_files=[],
            )
            return
        if request.command == "exit 2":
            yield SandboxProviderResult(
                provider_name=self.provider_name,
                exit_code=2,
                stdout="",
                stderr="bad exit",
                timed_out=False,
                cancelled=False,
                error_detail="Execution exited with a non-zero status.",
                output_files=[],
            )
            return
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="sandbox ok",
            stderr="",
            timed_out=False,
            cancelled=False,
            error_detail=None,
            output_files=output_files,
        )


class NoopCodeSandboxDispatcher:
    def dispatch_execution(self, *, execution_id: str, request_id: str = "") -> None:
        _ = (execution_id, request_id)


class NoopWorkbenchTaskDispatcher:
    def dispatch_task(self, *, task_id: str, request_id: str = "") -> None:
        _ = (task_id, request_id)


class ContractFakeLLM:
    def list_model_names(self) -> list[str]:
        return ["qwen3:4b", "gemma3:4b"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        if model == "gemma3:4b":
            return ["completion", "tools", "vision"], None
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
    ):
        if last_user_images_base64:
            yield "Vision"
            yield "OK"
            return
        last_user = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user = str(message.get("content", ""))
                break
        if "Retrieved knowledge context:" in system_prompt:
            if "competitive pressure" in system_prompt:
                yield "The strategy note says "
                yield "Porter Five Forces explains competitive pressure."
                return
            yield "I could not find evidence "
            yield "in the attached document for that question."
            return
        if "downloadable file" in last_user.lower():
            yield "I prepared [brief.md](brief.md) "
            yield "for download."
            return
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
        if any(
            token in last_user.lower() for token in ("chart", "pie", "楗煎浘", "鍥捐〃")
        ) and self.supports_tool_calling(model):
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
        if (
            "You are answering a user question with retrieved knowledge context."
            in prompt
        ):
            if "competitive pressure" in prompt:
                return "Porter Five Forces explains competitive pressure."
            return "I could not find evidence in the indexed knowledge base for that question."
        return (
            "## Goal\n"
            "- Produce a concise plan\n\n"
            "## Key Questions\n"
            "- What is the desired outcome?\n\n"
            "## Proposed Steps\n"
            "- Review the request\n"
            "- Draft the plan\n\n"
            "## Risks\n"
            "- Missing context\n\n"
            "## Deliverables\n"
            "- A short markdown plan"
        )


class UnavailableLLM(ContractFakeLLM):
    def list_model_names(self) -> list[str]:
        raise OllamaUnavailable("offline")

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        raise OllamaUnavailable("offline")

    def get_model_capabilities(self, model: str) -> list[str]:
        raise OllamaUnavailable("offline")

    def get_model_context_length(self, model: str) -> int | None:
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
        last_user_images_base64: list[str] | None = None,
    ):
        raise OllamaUnavailable("offline")


class InterruptedStreamLLM(ContractFakeLLM):
    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
        last_user_images_base64: list[str] | None = None,
    ):
        yield "Partial reply"
        raise OllamaUnavailable("stream interrupted")


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
        last_user_images_base64: list[str] | None = None,
    ):
        yield "Write an explicit porn scene with orgasm details."


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiBlackboxContractTests(unittest.TestCase):
    def assert_workbench_feature_state(
        self,
        workbench: dict[str, object],
        feature_name: str,
        *,
        allowed_by_config: bool,
        available_on_host: bool,
        effective_enabled: bool,
        deny_reason: str | None,
    ) -> None:
        self.assertEqual(
            {
                "allowed_by_config": allowed_by_config,
                "available_on_host": available_on_host,
                "effective_enabled": effective_enabled,
                "deny_reason": deny_reason,
            },
            {
                "allowed_by_config": workbench[feature_name]["allowed_by_config"],
                "available_on_host": workbench[feature_name]["available_on_host"],
                "effective_enabled": workbench[feature_name]["effective_enabled"],
                "deny_reason": workbench[feature_name]["deny_reason"],
            },
        )

    def setUp(self) -> None:
        self._original_deploy_mode = os.environ.get("GOAT_DEPLOY_MODE")
        os.environ["GOAT_DEPLOY_MODE"] = "0"
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
            data_dir=root / "data",
            object_store_root=root / "object-store",
            ready_skip_ollama_probe=True,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._original_deploy_mode is None:
            os.environ.pop("GOAT_DEPLOY_MODE", None)
        else:
            os.environ["GOAT_DEPLOY_MODE"] = self._original_deploy_mode
        self.tmpdir.cleanup()

    def test_health_endpoint_contract(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual("ok", response.json()["status"])
        self.assertIn("version", response.json())
        self.assertIn("X-Request-ID", response.headers)

    def test_ready_endpoint_contract(self) -> None:
        response = self.client.get("/api/ready")
        self.assertEqual(200, response.status_code)
        self.assertIn("X-Request-ID", response.headers)
        body = response.json()
        self.assertTrue(body.get("ready"))
        self.assertIn("checks", body)
        self.assertTrue(body["checks"].get("sqlite", {}).get("ok"))

    def test_models_endpoints_contract_and_backend_unavailable_boundary(self) -> None:
        list_response = self.client.get("/api/models")
        self.assertEqual(200, list_response.status_code)
        self.assertEqual(["qwen3:4b", "gemma3:4b"], list_response.json()["models"])

        caps_response = self.client.get(
            "/api/models/capabilities", params={"model": "gemma3:4B"}
        )
        self.assertEqual(200, caps_response.status_code)
        caps_body = caps_response.json()
        self.assertEqual("gemma3:4b", caps_body["model"])
        self.assertEqual(["completion", "tools", "vision"], caps_body["capabilities"])
        self.assertTrue(caps_body["supports_tool_calling"])
        self.assertTrue(caps_body["supports_chart_tools"])
        self.assertTrue(caps_body["supports_vision"])

        caps_bb = self.client.get(
            "/api/models/capabilities", params={"model": "qwen3:4b"}
        )
        self.assertFalse(caps_bb.json()["supports_vision"])

        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            unavailable_list = self.client.get("/api/models")
            unavailable_caps = self.client.get(
                "/api/models/capabilities",
                params={"model": "qwen3:4b"},
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(503, unavailable_list.status_code)
        ul = unavailable_list.json()
        self.assertEqual("AI backend unavailable", ul["detail"])
        self.assertEqual(INFERENCE_BACKEND_UNAVAILABLE, ul["code"])
        self.assertIn("request_id", ul)
        self.assertEqual(503, unavailable_caps.status_code)
        uc = unavailable_caps.json()
        self.assertEqual("AI backend unavailable", uc["detail"])
        self.assertEqual(INFERENCE_BACKEND_UNAVAILABLE, uc["code"])
        self.assertIn("request_id", uc)

        self.client.app.dependency_overrides[get_llm_client] = lambda: EmptyModelsLLM()
        try:
            fallback_list = self.client.get("/api/models")
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, fallback_list.status_code)
        self.assertEqual([], fallback_list.json()["models"])

    def test_chat_endpoint_streams_typed_events_and_persists_session(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "chat-1",
                "messages": [{"role": "user", "content": "Hello there"}],
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "text/event-stream; charset=utf-8", response.headers["content-type"]
        )
        events = parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "token", "token", "done"], [event["type"] for event in events]
        )
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
            SESSION_PAYLOAD_VERSION, history_detail.json()["schema_version"]
        )
        self.assertEqual(
            [
                {
                    "role": "user",
                    "content": "Hello there",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
                {
                    "role": "assistant",
                    "content": "Hello from GOAT",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
            ],
            history_detail.json()["messages"],
        )

        invalid = self.client.post(
            "/api/chat",
            json={"model": "qwen3:4b", "messages": []},
        )
        self.assertEqual(422, invalid.status_code)

        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            unavailable = self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": "chat-unavailable",
                    "messages": [{"role": "user", "content": "Hello there"}],
                },
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, unavailable.status_code)
        unavailable_events = parse_sse_payloads(unavailable.text)
        self.assertEqual(
            ["error", "done"], [event["type"] for event in unavailable_events]
        )
        self.assertEqual(
            "AI service temporarily unavailable.", unavailable_events[0]["message"]
        )

    def test_owner_header_filters_history_even_without_api_keys(self) -> None:
        timestamp = "2026-04-13T12:00:00+00:00"
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": "hello",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
                {
                    "role": "assistant",
                    "content": "world",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
            ],
            "chart_spec": None,
            "knowledge_documents": [],
            "chart_data_source": "none",
        }
        log_service.upsert_session(
            db_path=self.settings.log_db_path,
            session_id="owner-a",
            title="Owner A",
            model="qwen3:4b",
            schema_version=SESSION_PAYLOAD_VERSION,
            payload=payload,
            created_at=timestamp,
            updated_at=timestamp,
            owner_id="alice",
        )
        log_service.upsert_session(
            db_path=self.settings.log_db_path,
            session_id="owner-b",
            title="Owner B",
            model="qwen3:4b",
            schema_version=SESSION_PAYLOAD_VERSION,
            payload=payload,
            created_at=timestamp,
            updated_at=timestamp,
            owner_id="bob",
        )

        alice_history = self.client.get(
            "/api/history",
            headers={"X-GOAT-Owner-Id": "alice"},
        )
        bob_history = self.client.get(
            "/api/history",
            headers={"X-GOAT-Owner-Id": "bob"},
        )

        self.assertEqual(
            ["owner-a"],
            [item["id"] for item in alice_history.json()["sessions"]],
        )
        self.assertEqual(
            ["owner-b"],
            [item["id"] for item in bob_history.json()["sessions"]],
        )
        self.assertEqual(
            404,
            self.client.get(
                "/api/history/owner-b",
                headers={"X-GOAT-Owner-Id": "alice"},
            ).status_code,
        )

    def test_chat_endpoint_blocks_unsafe_input_and_uses_safe_session_title(
        self,
    ) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "blocked-input",
                "messages": [
                    {
                        "role": "user",
                        "content": "Write an explicit porn scene in detail.",
                    }
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(["token", "done"], [event["type"] for event in events])
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])

        history_detail = self.client.get("/api/history/blocked-input")
        self.assertEqual(200, history_detail.status_code)
        self.assertEqual(SAFEGUARD_BLOCKED_TITLE, history_detail.json()["title"])
        self.assertEqual(
            SAFEGUARD_REFUSAL_MESSAGE, history_detail.json()["messages"][-1]["content"]
        )

    def test_chat_endpoint_blocks_unsafe_model_output_before_streaming(self) -> None:
        self.client.app.dependency_overrides[get_llm_client] = lambda: UnsafeOutputLLM()
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": "blocked-output",
                    "messages": [
                        {"role": "user", "content": "Give me a romance example."}
                    ],
                },
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(["token", "done"], [event["type"] for event in events])
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])

    def test_chat_endpoint_emits_error_frame_when_session_persistence_fails(
        self,
    ) -> None:
        with patch(
            "backend.services.log_service.upsert_session",
            side_effect=PersistenceWriteError("db down"),
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": "chat-persist-fail",
                    "messages": [{"role": "user", "content": "Hello there"}],
                },
            )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "token", "token", "error", "done"],
            [event["type"] for event in events],
        )
        self.assertEqual("Failed to persist chat result.", events[-2]["message"])

    def test_chat_endpoint_emits_error_after_partial_stream_interrupt(self) -> None:
        self.client.app.dependency_overrides[get_llm_client] = lambda: (
            InterruptedStreamLLM()
        )
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": "chat-stream-interrupted",
                    "messages": [{"role": "user", "content": "Hello there"}],
                },
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(["error", "done"], [event["type"] for event in events])
        self.assertEqual(
            "AI service temporarily unavailable.",
            events[0]["message"],
        )

    def test_chat_blocked_input_still_emits_refusal_when_persistence_fails(
        self,
    ) -> None:
        with patch(
            "backend.services.log_service.upsert_session",
            side_effect=PersistenceWriteError("db down"),
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": "blocked-input-persist-fail",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Write an explicit porn scene in detail.",
                        }
                    ],
                },
            )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "error", "done"],
            [event["type"] for event in events],
        )
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])
        self.assertEqual("Failed to persist chat result.", events[1]["message"])

    def test_chat_blocked_output_still_emits_refusal_when_persistence_fails(
        self,
    ) -> None:
        self.client.app.dependency_overrides[get_llm_client] = lambda: UnsafeOutputLLM()
        try:
            with patch(
                "backend.services.log_service.upsert_session",
                side_effect=PersistenceWriteError("db down"),
            ):
                response = self.client.post(
                    "/api/chat",
                    json={
                        "model": "qwen3:4b",
                        "session_id": "blocked-output-persist-fail",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Give me a romance example.",
                            }
                        ],
                    },
                )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "error", "done"],
            [event["type"] for event in events],
        )
        self.assertEqual(SAFEGUARD_REFUSAL_MESSAGE, events[0]["token"])
        self.assertEqual("Failed to persist chat result.", events[1]["message"])

    def test_chat_chart_flow_returns_normalized_history_contract(self) -> None:
        file_context_prompt = (
            "[User uploaded tabular data for analysis]\n\n"
            "Column names: month, revenue.\n\n"
            "CHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\nFeb,12\n```\n"
        )
        response = self.client.post(
            "/api/chat",
            json={
                "model": "gemma3:4b",
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

    def test_chat_chart_flow_without_uploaded_file_still_uses_tools_contract(
        self,
    ) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "gemma3:4b",
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

    def test_chat_chart_prompt_with_tools_unsupported_model_stays_text_only(
        self,
    ) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "chart-no-tools",
                "messages": [
                    {"role": "user", "content": "Generate a typical pie chart."}
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        self.assertNotIn("chart_spec", [event["type"] for event in events])
        self.assertEqual("done", events[-1]["type"])

    def test_upload_sse_and_json_endpoints_cover_success_and_validation_boundaries(
        self,
    ) -> None:
        upload_response = self.client.post(
            "/api/upload",
            files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
        )
        self.assertEqual(200, upload_response.status_code)
        upload_events = parse_sse_payloads(upload_response.text)
        self.assertEqual(
            ["file_prompt", "knowledge_ready", "done"],
            [event["type"] for event in upload_events],
        )
        self.assertEqual("data.csv", upload_events[0]["filename"])
        self.assertIn("suffix_prompt", upload_events[0])
        self.assertEqual("data.csv", upload_events[1]["filename"])
        self.assertEqual("knowledge_rag", upload_events[1]["retrieval_mode"])
        self.assertIn("document_id", upload_events[1])
        self.assertIn("ingestion_id", upload_events[1])
        self.assertIn("template_prompt", upload_events[1])

        upload_invalid = self.client.post(
            "/api/upload",
            files={"file": ("image.png", b"not-a-knowledge-file", "image/png")},
        )
        self.assertEqual(400, upload_invalid.status_code)
        uinv = upload_invalid.json()
        self.assertEqual(
            "Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX.",
            uinv["detail"],
        )
        self.assertEqual(BAD_REQUEST, uinv["code"])

        upload_missing_name = self.client.post(
            "/api/upload",
            files={"file": ("", b"col1,col2\n1,2\n", "text/csv")},
        )
        self.assertEqual(422, upload_missing_name.status_code)
        umn = upload_missing_name.json()
        self.assertEqual(["body", "file"], umn["detail"][0]["loc"])
        self.assertEqual(REQUEST_VALIDATION_ERROR, umn["code"])

        analyze_response = self.client.post(
            "/api/upload/analyze",
            files={"file": ("sales.csv", b"month,revenue\nJan,10\n", "text/csv")},
        )
        self.assertEqual(200, analyze_response.status_code)
        analyze_body = analyze_response.json()
        self.assertEqual("sales.csv", analyze_body["filename"])
        self.assertEqual("knowledge_rag", analyze_body["retrieval_mode"])
        self.assertEqual("completed", analyze_body["status"])
        self.assertIn("document_id", analyze_body)
        self.assertIn("ingestion_id", analyze_body)
        self.assertIn("suffix_prompt", analyze_body)
        self.assertIn("template_prompt", analyze_body)
        self.assertIsNone(analyze_body["chart"])

        analyze_invalid = self.client.post(
            "/api/upload/analyze",
            files={"file": ("image.png", b"hello", "image/png")},
        )
        self.assertEqual(400, analyze_invalid.status_code)
        ainv = analyze_invalid.json()
        self.assertEqual(
            "Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX.",
            ainv["detail"],
        )
        self.assertEqual(BAD_REQUEST, ainv["code"])

        analyze_missing_name = self.client.post(
            "/api/upload/analyze",
            files={"file": ("", b"month,revenue\nJan,10\n", "text/csv")},
        )
        self.assertEqual(422, analyze_missing_name.status_code)
        amn = analyze_missing_name.json()
        self.assertEqual(["body", "file"], amn["detail"][0]["loc"])
        self.assertEqual(REQUEST_VALIDATION_ERROR, amn["code"])

    def test_knowledge_endpoints_cover_upload_ingestion_search_and_answer(self) -> None:
        upload = self.client.post(
            "/api/knowledge/uploads",
            files={
                "file": (
                    "strategy.txt",
                    b"Porter Five Forces explains competitive pressure.",
                    "text/plain",
                )
            },
        )
        self.assertEqual(200, upload.status_code)
        upload_body = upload.json()
        self.assertEqual("uploaded", upload_body["status"])
        document_id = upload_body["document_id"]
        self.assertEqual("strategy.txt", upload_body["filename"])

        upload_status = self.client.get(f"/api/knowledge/uploads/{document_id}")
        self.assertEqual(200, upload_status.status_code)
        self.assertEqual("uploaded", upload_status.json()["status"])

        missing_document = self.client.get("/api/knowledge/uploads/doc-missing")
        self.assertEqual(404, missing_document.status_code)
        self.assertEqual(KNOWLEDGE_NOT_FOUND, missing_document.json()["code"])

        ingestion = self.client.post(
            "/api/knowledge/ingestions",
            json={"document_id": document_id},
        )
        self.assertEqual(200, ingestion.status_code)
        ingestion_body = ingestion.json()
        self.assertEqual("completed", ingestion_body["status"])
        ingestion_id = ingestion_body["ingestion_id"]

        ingestion_status = self.client.get(f"/api/knowledge/ingestions/{ingestion_id}")
        self.assertEqual(200, ingestion_status.status_code)
        self.assertEqual("completed", ingestion_status.json()["status"])
        self.assertGreaterEqual(ingestion_status.json()["chunk_count"], 1)

        search = self.client.post(
            "/api/knowledge/search",
            json={"query": "Porter's Five Forces", "top_k": 3},
        )
        self.assertEqual(200, search.status_code)
        search_body = search.json()
        self.assertEqual("Porter's Five Forces", search_body["query"])
        self.assertIsNone(search_body.get("effective_query"))
        self.assertGreaterEqual(len(search_body["hits"]), 1)
        self.assertEqual(document_id, search_body["hits"][0]["document_id"])

        quality_search = self.client.post(
            "/api/knowledge/search",
            json={
                "query": "Porter's  Five  Forces",
                "top_k": 3,
                "retrieval_profile": "rag3_quality",
            },
        )
        self.assertEqual(200, quality_search.status_code)
        qs = quality_search.json()
        self.assertEqual("Porter's  Five  Forces", qs["query"])
        self.assertEqual("Porter's Five Forces", qs["effective_query"])
        self.assertGreaterEqual(len(qs["hits"]), 1)

        answer = self.client.post(
            "/api/knowledge/answers",
            json={"query": "Porter competitive pressure summary", "top_k": 3},
        )
        self.assertEqual(200, answer.status_code)
        answer_body = answer.json()
        self.assertTrue(answer_body["answer"])
        self.assertGreaterEqual(len(answer_body["citations"]), 1)
        self.assertNotIn("Relevant retrieved context:", answer_body["answer"])
        self.assertIn("competitive pressure", answer_body["answer"])

        no_hit = self.client.post(
            "/api/knowledge/answers",
            json={"query": "zxqv non matching token", "top_k": 3},
        )
        self.assertEqual(200, no_hit.status_code)
        self.assertEqual([], no_hit.json()["citations"])
        self.assertEqual(
            "I could not find evidence in the indexed knowledge base for that question.",
            no_hit.json()["answer"],
        )

        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            unavailable = self.client.post(
                "/api/knowledge/answers",
                json={"query": "Porter competitive pressure summary", "top_k": 3},
            )
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )
        self.assertEqual(503, unavailable.status_code)
        self.assertEqual("AI backend unavailable", unavailable.json()["detail"])

        rag_chat = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "rag-chat-1",
                "knowledge_document_ids": [document_id],
                "messages": [
                    {
                        "role": "user",
                        "content": "What does the indexed strategy note say?",
                    }
                ],
            },
        )
        self.assertEqual(200, rag_chat.status_code)
        rag_events = parse_sse_payloads(rag_chat.text)
        self.assertEqual("done", rag_events[-1]["type"])
        rag_text = "".join(
            event["token"] for event in rag_events if event["type"] == "token"
        )
        self.assertNotIn("Relevant retrieved context:", rag_text)
        self.assertIn("competitive pressure", rag_text)

        rag_history = self.client.get("/api/history/rag-chat-1")
        self.assertEqual(200, rag_history.status_code)
        self.assertEqual(SESSION_PAYLOAD_VERSION, rag_history.json()["schema_version"])
        self.assertEqual(
            [
                {
                    "document_id": document_id,
                    "filename": "strategy.txt",
                    "mime_type": "text/plain",
                }
            ],
            rag_history.json()["knowledge_documents"],
        )

    def test_chat_artifact_event_and_download_route(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "artifact-1",
                "messages": [
                    {
                        "role": "user",
                        "content": "Create a downloadable file with a short brief.",
                    }
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        events = parse_sse_payloads(response.text)
        artifact_event = next(
            event for event in events if event.get("type") == "artifact"
        )
        self.assertEqual("brief.md", artifact_event["filename"])
        self.assertTrue(artifact_event["download_url"].startswith("/api/artifacts/"))
        download = self.client.get(artifact_event["download_url"])
        self.assertEqual(200, download.status_code)
        self.assertEqual(
            'attachment; filename="brief.md"',
            download.headers["content-disposition"],
        )
        self.assertIn("prepared", download.text)

        history_detail = self.client.get("/api/history/artifact-1")
        self.assertEqual(200, history_detail.status_code)
        assistant_messages = [
            message
            for message in history_detail.json()["messages"]
            if message["role"] == "assistant"
        ]
        self.assertEqual(1, len(assistant_messages))
        self.assertEqual(
            "brief.md",
            assistant_messages[0]["artifacts"][0]["filename"],
        )

        missing = self.client.get("/api/artifacts/art-missing")
        self.assertEqual(404, missing.status_code)
        self.assertEqual(ARTIFACT_NOT_FOUND, missing.json()["code"])

    def test_history_endpoints_cover_empty_missing_delete_and_delete_all(self) -> None:
        empty_list = self.client.get("/api/history")
        self.assertEqual(200, empty_list.status_code)
        self.assertEqual({"sessions": []}, empty_list.json())

        missing = self.client.get("/api/history/not-found")
        self.assertEqual(404, missing.status_code)
        mj = missing.json()
        self.assertEqual("Session not found", mj["detail"])
        self.assertEqual(NOT_FOUND, mj["code"])

        for session_id in ("hist-a", "hist-b"):
            self.client.post(
                "/api/chat",
                json={
                    "model": "qwen3:4b",
                    "session_id": session_id,
                    "messages": [{"role": "user", "content": f"Hello {session_id}"}],
                },
            )

        listed = self.client.get("/api/history")
        self.assertEqual(2, len(listed.json()["sessions"]))
        for item in listed.json()["sessions"]:
            self.assertEqual(SESSION_PAYLOAD_VERSION, item["schema_version"])

        delete_one = self.client.delete("/api/history/hist-a")
        self.assertEqual(204, delete_one.status_code)
        self.assertEqual(404, self.client.get("/api/history/hist-a").status_code)

        delete_all = self.client.delete("/api/history")
        self.assertEqual(204, delete_all.status_code)
        self.assertEqual({"sessions": []}, self.client.get("/api/history").json())

    def test_chat_session_append_idempotency_replays_same_sse_and_avoids_double_write(
        self,
    ) -> None:
        headers = {"Idempotency-Key": "chat-key-1"}
        payload = {
            "model": "qwen3:4b",
            "session_id": "idem-chat-1",
            "messages": [{"role": "user", "content": "Hello idempotent chat"}],
        }
        first = self.client.post("/api/chat", json=payload, headers=headers)
        second = self.client.post("/api/chat", json=payload, headers=headers)

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(first.text, second.text)

        detail = self.client.get("/api/history/idem-chat-1")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(
            [
                {
                    "role": "user",
                    "content": "Hello idempotent chat",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
                {
                    "role": "assistant",
                    "content": "Hello from GOAT",
                    "image_attachment_ids": [],
                    "artifacts": [],
                },
            ],
            detail.json()["messages"],
        )
        with sqlite3.connect(self.settings.log_db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE session_id = ?",
                ("idem-chat-1",),
            ).fetchone()[0]
        self.assertEqual(1, total)

    def test_system_endpoints_cover_gpu_inference_and_runtime_target_contracts(
        self,
    ) -> None:
        self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
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
        self.assertIn("deploy_mode", runtime_body)
        self.assertIn("deploy_mode_name", runtime_body)
        self.assertIn("current", runtime_body)
        self.assertIn("ordered_targets", runtime_body)
        self.assertGreaterEqual(len(runtime_body["ordered_targets"]), 1)

        features = self.client.get("/api/system/features")
        self.assertEqual(200, features.status_code)
        feat_body = features.json()
        self.assertIn("code_sandbox", feat_body)
        self.assertIn("workbench", feat_body)
        self.assertTrue(feat_body["code_sandbox"]["policy_allowed"])
        self.assertFalse(feat_body["code_sandbox"]["effective_enabled"])
        self.assertIn(
            feat_body["code_sandbox"]["isolation_level"], {"container", "host"}
        )
        self.assertFalse(feat_body["workbench"]["agent_tasks"]["effective_enabled"])
        self.assertFalse(feat_body["workbench"]["plan_mode"]["effective_enabled"])
        self.assertFalse(feat_body["workbench"]["browse"]["effective_enabled"])

        desktop = self.client.get("/api/system/desktop")
        self.assertEqual(200, desktop.status_code)
        desktop_body = desktop.json()
        self.assertFalse(desktop_body["desktop_mode"])
        self.assertEqual([], desktop_body["failing_checks"])
        self.assertIsNone(desktop_body["backend_base_url"])

        exec_stub = self.client.post("/api/code-sandbox/exec", json={})
        self.assertEqual(503, exec_stub.status_code)
        ej = exec_stub.json()
        self.assertEqual(FEATURE_UNAVAILABLE, ej["code"])

        workbench_stub = self.client.post(
            "/api/workbench/tasks",
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(503, workbench_stub.status_code)
        self.assertEqual(FEATURE_UNAVAILABLE, workbench_stub.json()["code"])

    def test_vision_media_upload_and_chat_contract(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500001d0d4e0aea0000000049454e44ae426082"
        )
        up = self.client.post(
            "/api/media/uploads",
            files={"file": ("t.png", png, "image/png")},
        )
        self.assertEqual(200, up.status_code)
        body = up.json()
        self.assertTrue(body["attachment_id"].startswith("att-"))
        aid = body["attachment_id"]

        chat = self.client.post(
            "/api/chat",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": "What is this?"}],
                "image_attachment_ids": [aid],
            },
        )
        self.assertEqual(200, chat.status_code)
        payloads = parse_sse_payloads(chat.text)
        text = "".join(p["token"] for p in payloads if p.get("type") == "token")
        self.assertIn("VisionOK", text.replace(" ", ""))

    def test_chat_vision_with_non_vision_model_returns_422(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500001d0d4e0aea0000000049454e44ae426082"
        )
        up = self.client.post(
            "/api/media/uploads",
            files={"file": ("t.png", png, "image/png")},
        )
        aid = up.json()["attachment_id"]
        resp = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "messages": [{"role": "user", "content": "Hi"}],
                "image_attachment_ids": [aid],
            },
        )
        self.assertEqual(422, resp.status_code)
        err = resp.json()
        self.assertEqual(VISION_NOT_SUPPORTED, err["code"])

    def test_chat_missing_image_attachment_returns_404(self) -> None:
        resp = self.client.post(
            "/api/chat",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": "Hi"}],
                "image_attachment_ids": ["att-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
            },
        )
        self.assertEqual(404, resp.status_code)
        self.assertEqual(MEDIA_NOT_FOUND, resp.json()["code"])

    def test_chat_knowledge_and_image_conflict_returns_422(self) -> None:
        resp = self.client.post(
            "/api/chat",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": "Hi"}],
                "knowledge_document_ids": ["doc-1"],
                "image_attachment_ids": ["att-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
            },
        )
        self.assertEqual(422, resp.status_code)
        self.assertEqual(REQUEST_VALIDATION_ERROR, resp.json()["code"])

    def test_media_upload_rejects_invalid_image(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        bad = self.client.post(
            "/api/media/uploads",
            files={"file": ("x.bin", b"not an image", "application/octet-stream")},
        )
        self.assertEqual(400, bad.status_code)

    def test_workbench_enabled_creates_and_reads_durable_task(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        features = self.client.get("/api/system/features")
        self.assertEqual(200, features.status_code)
        feature_body = features.json()
        self.assertTrue(feature_body["workbench"]["agent_tasks"]["effective_enabled"])
        self.assertTrue(feature_body["workbench"]["plan_mode"]["effective_enabled"])
        self.assertTrue(feature_body["workbench"]["browse"]["effective_enabled"])
        self.assertTrue(feature_body["workbench"]["deep_research"]["effective_enabled"])
        self.assertTrue(
            feature_body["workbench"]["artifact_workspace"]["effective_enabled"]
        )
        self.assertTrue(
            feature_body["workbench"]["project_memory"]["effective_enabled"]
        )
        self.assertFalse(feature_body["workbench"]["connectors"]["effective_enabled"])

        sources_response = self.client.get("/api/workbench/sources")
        self.assertEqual(200, sources_response.status_code)
        sources_body = sources_response.json()
        self.assertEqual(
            ["web", "knowledge", "project_memory"],
            [source["source_id"] for source in sources_body["sources"]],
        )
        self.assertTrue(sources_body["sources"][0]["runtime_ready"])
        self.assertIsNone(sources_body["sources"][0]["deny_reason"])
        self.assertIn("DDGS", sources_body["sources"][0]["description"])
        self.assertTrue(sources_body["sources"][1]["runtime_ready"])
        self.assertEqual(
            ["plan", "browse", "deep_research"],
            sources_body["sources"][1]["task_kinds"],
        )
        self.assertEqual("project_memory", sources_body["sources"][2]["kind"])
        self.assertEqual("project_scope", sources_body["sources"][2]["scope_kind"])
        self.assertTrue(sources_body["sources"][2]["runtime_ready"])

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "plan",
                "prompt": "Draft a plan",
                "session_id": "chat-1",
                "project_id": "project-1",
                "source_ids": ["knowledge"],
            },
        )

        self.assertEqual(202, create_response.status_code)
        created = create_response.json()
        self.assertTrue(created["task_id"].startswith("wb-"))
        self.assertEqual("plan", created["task_kind"])
        self.assertEqual("queued", created["status"])
        self.assertIn("created_at", created)
        self.assertNotIn("result", created)

        status_response = self.client.get(f"/api/workbench/tasks/{created['task_id']}")
        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual(created["task_id"], status_body["task_id"])
        self.assertEqual("plan", status_body["task_kind"])
        self.assertEqual("completed", status_body["status"])
        self.assertEqual(created["created_at"], status_body["created_at"])
        self.assertGreaterEqual(status_body["updated_at"], status_body["created_at"])
        self.assertIsNone(status_body["error_detail"])
        self.assertEqual("markdown", status_body["result"]["format"])
        self.assertIn("Goal", status_body["result"]["content"])

        events_response = self.client.get(
            f"/api/workbench/tasks/{created['task_id']}/events"
        )
        self.assertEqual(200, events_response.status_code)
        events_body = events_response.json()
        self.assertEqual(created["task_id"], events_body["task_id"])
        self.assertEqual(
            ["task.queued", "task.started", "task.completed"],
            [event["event_type"] for event in events_body["events"]],
        )
        self.assertEqual(
            [1, 2, 3], [event["sequence"] for event in events_body["events"]]
        )
        self.assertEqual("queued", events_body["events"][0]["status"])
        self.assertEqual("completed", events_body["events"][-1]["status"])
        self.assertEqual(
            ["knowledge"], events_body["events"][0]["metadata"]["source_ids"]
        )
        self.assertEqual(
            "markdown", events_body["events"][-1]["metadata"]["result_format"]
        )

        missing = self.client.get("/api/workbench/tasks/wb-missing")
        self.assertEqual(404, missing.status_code)
        self.assertEqual("Workbench task not found", missing.json()["detail"])

    def test_workbench_sources_endpoint_respects_runtime_gate_and_current_visible_inventory(
        self,
    ) -> None:
        unavailable = self.client.get("/api/workbench/sources")
        self.assertEqual(503, unavailable.status_code)
        self.assertEqual(FEATURE_UNAVAILABLE, unavailable.json()["code"])

        self.settings = replace(
            self.settings,
            feature_agent_workbench_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-workbench-reader",
                "secret": "workbench-reader",
                "principal_id": "principal:reader",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read"]
              },
              {
                "credential_id": "cred-workbench-writer",
                "secret": "workbench-writer",
                "principal_id": "principal:writer",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read", "workbench:write"]
              },
              {
                "credential_id": "cred-workbench-exporter",
                "secret": "workbench-exporter",
                "principal_id": "principal:exporter",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["artifact:write", "history:read", "workbench:export", "workbench:read"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        for api_key in ("workbench-reader", "workbench-writer", "workbench-exporter"):
            response = self.client.get(
                "/api/workbench/sources",
                headers={"X-GOAT-API-Key": api_key},
            )
            self.assertEqual(200, response.status_code)
            body = response.json()
            source_ids = {source["source_id"] for source in body["sources"]}

            self.assertIn("web", source_ids)
            self.assertIn("project_memory", source_ids)
            self.assertTrue(source_ids.issubset({"web", "knowledge", "project_memory"}))
            self.assertNotIn("connectors", source_ids)

            for source in body["sources"]:
                self.assertIn("display_name", source)
                self.assertIn("kind", source)
                self.assertIn("scope_kind", source)
                self.assertIn("read_only", source)
                self.assertIn("runtime_ready", source)
                self.assertIn("task_kinds", source)
                self.assertTrue(source["runtime_ready"])
                self.assertTrue(source["read_only"])
                self.assertIsNone(source["deny_reason"])

    def test_system_features_workbench_entries_are_caller_scoped_capability_view(
        self,
    ) -> None:
        self.settings = replace(
            self.settings,
            feature_agent_workbench_enabled=True,
            api_key="bootstrap-auth-enabled",
            api_key_write="",
            api_credentials_json="""
            [
              {
                "credential_id": "cred-workbench-reader",
                "secret": "workbench-reader",
                "principal_id": "principal:reader",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read"]
              },
              {
                "credential_id": "cred-workbench-writer",
                "secret": "workbench-writer",
                "principal_id": "principal:writer",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["history:read", "workbench:read", "workbench:write"]
              },
              {
                "credential_id": "cred-workbench-exporter",
                "secret": "workbench-exporter",
                "principal_id": "principal:exporter",
                "tenant_id": "tenant:default",
                "status": "active",
                "scopes": ["artifact:write", "history:read", "workbench:export", "workbench:read"]
              }
            ]
            """,
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        reader_features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "workbench-reader"},
        )
        writer_features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "workbench-writer"},
        )
        exporter_features = self.client.get(
            "/api/system/features",
            headers={"X-GOAT-API-Key": "workbench-exporter"},
        )
        self.assertEqual(200, reader_features.status_code)
        self.assertEqual(200, writer_features.status_code)
        self.assertEqual(200, exporter_features.status_code)
        reader_workbench = reader_features.json()["workbench"]
        writer_workbench = writer_features.json()["workbench"]
        exporter_workbench = exporter_features.json()["workbench"]

        self.assert_workbench_feature_state(
            reader_workbench,
            "agent_tasks",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "browse",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "deep_research",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "artifact_workspace",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "artifact_exports",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "project_memory",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            reader_workbench,
            "connectors",
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason="permission_denied",
        )

        self.assert_workbench_feature_state(
            writer_workbench,
            "agent_tasks",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "browse",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "deep_research",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "artifact_workspace",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "artifact_exports",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "project_memory",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            writer_workbench,
            "connectors",
            allowed_by_config=True,
            available_on_host=False,
            effective_enabled=False,
            deny_reason="not_implemented",
        )
        self.assert_workbench_feature_state(
            exporter_workbench,
            "agent_tasks",
            allowed_by_config=False,
            available_on_host=True,
            effective_enabled=False,
            deny_reason="permission_denied",
        )
        self.assert_workbench_feature_state(
            exporter_workbench,
            "artifact_workspace",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            exporter_workbench,
            "artifact_exports",
            allowed_by_config=True,
            available_on_host=True,
            effective_enabled=True,
            deny_reason=None,
        )
        self.assert_workbench_feature_state(
            exporter_workbench,
            "connectors",
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason="permission_denied",
        )

        self.assertNotEqual(
            reader_workbench["agent_tasks"],
            writer_workbench["agent_tasks"],
        )
        self.assertNotEqual(
            reader_workbench["browse"],
            writer_workbench["browse"],
        )
        self.assertNotEqual(
            writer_workbench["artifact_exports"],
            exporter_workbench["artifact_exports"],
        )

    def test_workbench_rejects_incompatible_source_for_task_kind(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "plan",
                "prompt": "Draft a plan",
                "source_ids": ["web"],
            },
        )

        self.assertEqual(422, create_response.status_code)
        body = create_response.json()
        self.assertEqual(REQUEST_VALIDATION_ERROR, body["code"])
        self.assertIn("do not support task kind", body["detail"])

    def test_workbench_task_cancel_cancels_queued_task(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_workbench_task_dispatcher] = lambda: (
            NoopWorkbenchTaskDispatcher()
        )

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={"task_kind": "plan", "prompt": "Draft a plan"},
        )
        self.assertEqual(202, create_response.status_code)
        task_id = create_response.json()["task_id"]
        self.assertEqual("queued", create_response.json()["status"])

        cancel_response = self.client.post(f"/api/workbench/tasks/{task_id}/cancel")
        self.assertEqual(200, cancel_response.status_code)
        cancel_body = cancel_response.json()
        self.assertEqual("cancelled", cancel_body["status"])
        self.assertEqual(
            "Task cancelled before execution.", cancel_body["error_detail"]
        )
        self.assertIsNone(cancel_body["result"])

        status_response = self.client.get(f"/api/workbench/tasks/{task_id}")
        self.assertEqual(200, status_response.status_code)
        self.assertEqual("cancelled", status_response.json()["status"])

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        self.assertEqual(
            ["task.queued", "task.cancelled"],
            [event["event_type"] for event in events_response.json()["events"]],
        )

        conflict = self.client.post(f"/api/workbench/tasks/{task_id}/cancel")
        self.assertEqual(409, conflict.status_code)
        self.assertEqual(RESOURCE_CONFLICT, conflict.json()["code"])

    def test_workbench_task_retry_creates_new_task_with_lineage(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "deep_research",
                "prompt": "Investigate launches",
                "source_ids": ["web"],
            },
        )
        self.assertEqual(202, create_response.status_code)
        original_id = create_response.json()["task_id"]

        status_response = self.client.get(f"/api/workbench/tasks/{original_id}")
        self.assertEqual(200, status_response.status_code)
        self.assertEqual("completed", status_response.json()["status"])

        self.client.app.dependency_overrides[get_workbench_task_dispatcher] = lambda: (
            NoopWorkbenchTaskDispatcher()
        )
        retry_response = self.client.post(f"/api/workbench/tasks/{original_id}/retry")
        self.assertEqual(202, retry_response.status_code)
        retry_body = retry_response.json()
        self.assertNotEqual(original_id, retry_body["task_id"])
        self.assertEqual("queued", retry_body["status"])

        retried_status = self.client.get(
            f"/api/workbench/tasks/{retry_body['task_id']}"
        )
        self.assertEqual(200, retried_status.status_code)
        self.assertEqual("queued", retried_status.json()["status"])
        self.assertIsNone(retried_status.json()["result"])

        original_events = self.client.get(f"/api/workbench/tasks/{original_id}/events")
        self.assertEqual(200, original_events.status_code)
        self.assertEqual(
            "task.retry_requested",
            original_events.json()["events"][-1]["event_type"],
        )
        self.assertEqual(
            retry_body["task_id"],
            original_events.json()["events"][-1]["metadata"]["retry_task_id"],
        )

        retried_events = self.client.get(
            f"/api/workbench/tasks/{retry_body['task_id']}/events"
        )
        self.assertEqual(200, retried_events.status_code)
        self.assertEqual(
            "task.retry_created",
            retried_events.json()["events"][1]["event_type"],
        )
        self.assertEqual(
            original_id,
            retried_events.json()["events"][1]["metadata"]["source_task_id"],
        )

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_enabled_executes_and_reads_durable_record(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        features = self.client.get("/api/system/features")
        self.assertEqual(200, features.status_code)
        self.assertTrue(features.json()["code_sandbox"]["effective_enabled"])
        self.assertEqual(
            "container", features.json()["code_sandbox"]["isolation_level"]
        )

        response = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "runtime_preset": "shell",
                "code": "echo sandbox ok",
                "command": "touch outputs/report.txt",
            },
        )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["execution_id"].startswith("cs-"))
        self.assertEqual("completed", body["status"])
        self.assertEqual("sync", body["execution_mode"])
        self.assertEqual(0, body["exit_code"])
        self.assertEqual("sandbox ok", body["stdout"])
        self.assertEqual("fake-docker", body["provider_name"])
        self.assertEqual(
            [{"path": "report.txt", "byte_size": 12}], body["output_files"]
        )

        status = self.client.get(f"/api/code-sandbox/executions/{body['execution_id']}")
        self.assertEqual(200, status.status_code)
        self.assertEqual(body["execution_id"], status.json()["execution_id"])
        self.assertEqual("completed", status.json()["status"])

        events = self.client.get(
            f"/api/code-sandbox/executions/{body['execution_id']}/events"
        )
        self.assertEqual(200, events.status_code)
        self.assertEqual(
            [
                "execution.queued",
                "execution.started",
                "execution.log.stdout",
                "execution.completed",
            ],
            [event["event_type"] for event in events.json()["events"]],
        )

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_async_exec_returns_accepted_and_streams_logs(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        response = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "execution_mode": "async",
                "code": "echo sandbox ok",
                "command": "printf async",
            },
        )
        self.assertEqual(202, response.status_code)
        body = response.json()
        self.assertEqual("async", body["execution_mode"])
        self.assertIn(body["status"], {"queued", "running", "completed"})

        logs = self.client.get(
            f"/api/code-sandbox/executions/{body['execution_id']}/logs"
        )
        self.assertEqual(200, logs.status_code)
        payloads = parse_sse_payloads(logs.text)
        event_types = [item.get("type") for item in payloads]
        self.assertIn("status", event_types)
        self.assertIn("stdout", event_types)
        self.assertIn("done", event_types)

        final_status = self.client.get(
            f"/api/code-sandbox/executions/{body['execution_id']}"
        )
        self.assertEqual(200, final_status.status_code)
        self.assertEqual("completed", final_status.json()["status"])
        self.assertIn("async log line", final_status.json()["stdout"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_cancel_can_stop_running_execution(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        created = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "execution_mode": "async",
                "code": "echo sandbox ok",
                "command": "hold-cancellable",
            },
        )
        self.assertEqual(202, created.status_code)
        execution_id = created.json()["execution_id"]

        status = self.client.get(f"/api/code-sandbox/executions/{execution_id}")
        deadline = time.monotonic() + 2.0
        while status.status_code == 200 and status.json()["status"] != "running":
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
            status = self.client.get(f"/api/code-sandbox/executions/{execution_id}")

        self.assertEqual(200, status.status_code)
        self.assertEqual("running", status.json()["status"])

        cancel = self.client.post(f"/api/code-sandbox/executions/{execution_id}/cancel")
        self.assertEqual(200, cancel.status_code)
        self.assertEqual("cancelled", cancel.json()["status"])
        self.assertEqual(
            "Execution cancelled by request.",
            cancel.json()["error_detail"],
        )

        events = self.client.get(f"/api/code-sandbox/executions/{execution_id}/events")
        self.assertEqual(200, events.status_code)
        self.assertEqual(
            [
                "execution.queued",
                "execution.started",
                "execution.log.stdout",
                "execution.cancel_requested",
                "execution.cancelled",
            ],
            [event["event_type"] for event in events.json()["events"]],
        )

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_cancel_cancels_queued_execution_and_finishes_logs(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )
        self.client.app.dependency_overrides[get_code_sandbox_execution_dispatcher] = (
            lambda: NoopCodeSandboxDispatcher()
        )

        created = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "execution_mode": "async",
                "code": "echo sandbox ok",
                "command": "printf async",
            },
        )
        self.assertEqual(202, created.status_code)
        execution_id = created.json()["execution_id"]
        self.assertEqual("queued", created.json()["status"])

        cancel = self.client.post(f"/api/code-sandbox/executions/{execution_id}/cancel")
        self.assertEqual(200, cancel.status_code)
        cancel_body = cancel.json()
        self.assertEqual("cancelled", cancel_body["status"])
        self.assertEqual(
            "Execution cancelled before start.", cancel_body["error_detail"]
        )

        logs = self.client.get(f"/api/code-sandbox/executions/{execution_id}/logs")
        self.assertEqual(200, logs.status_code)
        payloads = parse_sse_payloads(logs.text)
        self.assertEqual(["status", "done"], [item["type"] for item in payloads])
        self.assertEqual("cancelled", payloads[0]["status"])

        events = self.client.get(f"/api/code-sandbox/executions/{execution_id}/events")
        self.assertEqual(200, events.status_code)
        self.assertEqual(
            ["execution.queued", "execution.cancelled"],
            [event["event_type"] for event in events.json()["events"]],
        )

        conflict = self.client.post(
            f"/api/code-sandbox/executions/{execution_id}/cancel"
        )
        self.assertEqual(409, conflict.status_code)
        self.assertEqual(RESOURCE_CONFLICT, conflict.json()["code"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_retry_rejects_running_execution(self, _mock: object) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        created = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "execution_mode": "async",
                "code": "echo sandbox ok",
                "command": "hold-cancellable",
            },
        )
        self.assertEqual(202, created.status_code)
        execution_id = created.json()["execution_id"]

        status = self.client.get(f"/api/code-sandbox/executions/{execution_id}")
        deadline = time.monotonic() + 2.0
        while status.status_code == 200 and status.json()["status"] != "running":
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
            status = self.client.get(f"/api/code-sandbox/executions/{execution_id}")

        self.assertEqual(200, status.status_code)
        self.assertEqual("running", status.json()["status"])

        retry = self.client.post(f"/api/code-sandbox/executions/{execution_id}/retry")
        self.assertEqual(409, retry.status_code)
        self.assertEqual(RESOURCE_CONFLICT, retry.json()["code"])

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_retry_creates_new_execution_with_lineage(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        created = self.client.post(
            "/api/code-sandbox/exec",
            json={
                "runtime_preset": "shell",
                "code": "echo sandbox ok",
                "command": "touch outputs/report.txt",
            },
        )
        self.assertEqual(200, created.status_code)
        original_id = created.json()["execution_id"]

        retry = self.client.post(f"/api/code-sandbox/executions/{original_id}/retry")
        self.assertEqual(200, retry.status_code)
        retry_body = retry.json()
        self.assertNotEqual(original_id, retry_body["execution_id"])
        self.assertEqual("completed", retry_body["status"])
        self.assertEqual(
            [{"path": "report.txt", "byte_size": 12}], retry_body["output_files"]
        )

        original_events = self.client.get(
            f"/api/code-sandbox/executions/{original_id}/events"
        )
        self.assertEqual(200, original_events.status_code)
        self.assertEqual(
            "execution.retry_requested",
            original_events.json()["events"][-1]["event_type"],
        )
        self.assertEqual(
            retry_body["execution_id"],
            original_events.json()["events"][-1]["metadata"]["retry_execution_id"],
        )

        retried_events = self.client.get(
            f"/api/code-sandbox/executions/{retry_body['execution_id']}/events"
        )
        self.assertEqual(200, retried_events.status_code)
        self.assertEqual(
            "execution.retry_created",
            retried_events.json()["events"][1]["event_type"],
        )
        self.assertEqual(
            original_id,
            retried_events.json()["events"][1]["metadata"]["source_execution_id"],
        )

    @patch("goat_ai.config.feature_gates.probe_docker_available", return_value=True)
    def test_code_sandbox_exec_rejects_invalid_network_policy(
        self, _mock: object
    ) -> None:
        self.settings = replace(self.settings, feature_code_sandbox_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            FakeCodeSandboxProvider()
        )

        response = self.client.post(
            "/api/code-sandbox/exec",
            json={"code": "echo sandbox ok", "network_policy": "enabled"},
        )
        self.assertEqual(422, response.status_code)
        self.assertEqual(REQUEST_VALIDATION_ERROR, response.json()["code"])

    def test_workbench_task_rejects_unknown_source_ids(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "plan",
                "prompt": "Draft a plan",
                "source_ids": ["unknown-source"],
            },
        )
        self.assertEqual(422, response.status_code)
        body = response.json()
        self.assertEqual("REQUEST_VALIDATION_ERROR", body["code"])
        self.assertIn("Unknown or unavailable workbench sources", body["detail"])

    def test_workbench_task_infers_knowledge_source_from_attached_docs(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "plan",
                "prompt": "Draft a plan",
                "knowledge_document_ids": ["doc-123"],
            },
        )
        self.assertEqual(202, create_response.status_code)
        task_id = create_response.json()["task_id"]

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        self.assertEqual(
            ["knowledge"], events_response.json()["events"][0]["metadata"]["source_ids"]
        )

    def test_workbench_plan_task_surfaces_failed_status_when_execution_fails(
        self,
    ) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_llm_client] = lambda: UnavailableLLM()
        try:
            create_response = self.client.post(
                "/api/workbench/tasks",
                json={"task_kind": "plan", "prompt": "Draft a plan"},
            )
            self.assertEqual(202, create_response.status_code)
            task_id = create_response.json()["task_id"]

            status_response = self.client.get(f"/api/workbench/tasks/{task_id}")
        finally:
            self.client.app.dependency_overrides[get_llm_client] = lambda: (
                ContractFakeLLM()
            )

        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual("failed", status_body["status"])
        self.assertEqual("AI backend unavailable.", status_body["error_detail"])
        self.assertIsNone(status_body["result"])

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        self.assertEqual(
            ["task.queued", "task.started", "task.failed"],
            [event["event_type"] for event in events_response.json()["events"]],
        )

    def test_workbench_browse_task_uses_knowledge_source_and_returns_citations(
        self,
    ) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        upload = self.client.post(
            "/api/knowledge/uploads",
            files={
                "file": (
                    "strategy.txt",
                    b"Porter Five Forces explains competitive pressure.",
                    "text/plain",
                )
            },
        )
        self.assertEqual(200, upload.status_code)
        document_id = upload.json()["document_id"]
        ingest = self.client.post(
            "/api/knowledge/ingestions",
            json={
                "document_id": document_id,
                "parser_profile": "default",
                "chunking_profile": "default",
                "embedding_profile": "default",
            },
        )
        self.assertEqual(200, ingest.status_code)

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "browse",
                "prompt": "competitive pressure",
                "knowledge_document_ids": [document_id],
            },
        )
        self.assertEqual(202, create_response.status_code)
        task_id = create_response.json()["task_id"]

        status_response = self.client.get(f"/api/workbench/tasks/{task_id}")
        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual("completed", status_body["status"])
        self.assertIsNone(status_body["error_detail"])
        self.assertIn("Browse Summary", status_body["result"]["content"])
        self.assertGreaterEqual(len(status_body["result"]["citations"]), 1)
        self.assertEqual(
            "Porter Five Forces explains competitive pressure.",
            status_body["result"]["citations"][0]["snippet"],
        )

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        event_types = [
            event["event_type"] for event in events_response.json()["events"]
        ]
        self.assertEqual("task.queued", event_types[0])
        self.assertEqual("task.started", event_types[1])
        self.assertIn("retrieval.sources_resolved", event_types)
        self.assertIn("research.plan.created", event_types)
        self.assertIn("retrieval.step.started", event_types)
        self.assertIn("retrieval.step.completed", event_types)
        self.assertIn("research.synthesis.completed", event_types)
        self.assertEqual("task.completed", event_types[-1])
        knowledge_events = [
            event
            for event in events_response.json()["events"]
            if event["event_type"] == "retrieval.step.completed"
            and event["metadata"].get("source_id") == "knowledge"
        ]
        self.assertGreaterEqual(len(knowledge_events), 1)

    def test_workbench_deep_research_with_web_only_completes_with_web_citations(
        self,
    ) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        with patch(
            "backend.services.workbench_execution_service.search_public_web",
            return_value=[
                WorkbenchWebSearchHit(
                    title="OpenClaw note",
                    url="https://example.com/openclaw",
                    snippet="DuckDuckGo-backed retrieval is enabled.",
                    rank=1,
                )
            ],
        ):
            response = self.client.post(
                "/api/workbench/tasks",
                json={
                    "task_kind": "deep_research",
                    "prompt": "Look something up",
                    "source_ids": ["web"],
                },
            )
        self.assertEqual(202, response.status_code)
        task_id = response.json()["task_id"]

        status_response = self.client.get(f"/api/workbench/tasks/{task_id}")
        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual("completed", status_body["status"])
        self.assertIn("Research Brief", status_body["result"]["content"])
        self.assertIn(
            "[OpenClaw note](https://example.com/openclaw)",
            status_body["result"]["content"],
        )
        self.assertEqual(
            "https://example.com/openclaw",
            status_body["result"]["citations"][0]["document_id"],
        )

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        web_events = [
            event
            for event in events_response.json()["events"]
            if event["event_type"] == "retrieval.step.completed"
            and event["metadata"].get("source_id") == "web"
        ]
        self.assertGreaterEqual(len(web_events), 1)
        self.assertTrue(
            all(event["metadata"]["provider"] == "duckduckgo" for event in web_events)
        )

    def test_workbench_canvas_task_completes_with_workspace_output(self) -> None:
        self.settings = replace(self.settings, feature_agent_workbench_enabled=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings

        session_seed = self.client.post(
            "/api/chat",
            json={
                "model": "qwen3:4b",
                "session_id": "canvas-session-1",
                "messages": [{"role": "user", "content": "Seed session"}],
            },
        )
        self.assertEqual(200, session_seed.status_code)

        create_response = self.client.post(
            "/api/workbench/tasks",
            json={
                "task_kind": "canvas",
                "prompt": "Draft something",
                "session_id": "canvas-session-1",
                "project_id": "project-canvas-1",
            },
        )
        self.assertEqual(202, create_response.status_code)
        task_id = create_response.json()["task_id"]

        status_response = self.client.get(f"/api/workbench/tasks/{task_id}")
        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual("completed", status_body["status"])
        self.assertIsNone(status_body["error_detail"])
        self.assertEqual("markdown", status_body["result"]["format"])
        self.assertEqual(1, len(status_body["workspace_outputs"]))
        self.assertEqual(
            "canvas_document", status_body["workspace_outputs"][0]["output_kind"]
        )
        self.assertEqual(
            status_body["result"]["content"],
            status_body["workspace_outputs"][0]["content"],
        )
        output_id = status_body["workspace_outputs"][0]["output_id"]

        events_response = self.client.get(f"/api/workbench/tasks/{task_id}/events")
        self.assertEqual(200, events_response.status_code)
        self.assertEqual(
            [
                "task.queued",
                "task.started",
                "workspace_output.created",
                "task.completed",
            ],
            [event["event_type"] for event in events_response.json()["events"]],
        )

        output_response = self.client.get(
            f"/api/workbench/workspace-outputs/{output_id}"
        )
        self.assertEqual(200, output_response.status_code)
        self.assertEqual(output_id, output_response.json()["output_id"])
        self.assertEqual([], output_response.json()["artifacts"])

        export_response = self.client.post(
            f"/api/workbench/workspace-outputs/{output_id}/exports",
            json={"format": "markdown"},
        )
        self.assertEqual(201, export_response.status_code)
        artifact = export_response.json()
        self.assertTrue(artifact["artifact_id"].startswith("art-"))
        self.assertTrue(artifact["filename"].endswith(".md"))
        self.assertTrue(artifact["download_url"].startswith("/api/artifacts/"))

        exported_output_response = self.client.get(
            f"/api/workbench/workspace-outputs/{output_id}"
        )
        self.assertEqual(200, exported_output_response.status_code)
        self.assertEqual(
            artifact["artifact_id"],
            exported_output_response.json()["artifacts"][0]["artifact_id"],
        )

        download_response = self.client.get(artifact["download_url"])
        self.assertEqual(200, download_response.status_code)
        self.assertIn("## Goal", download_response.text)

        session_outputs = self.client.get(
            "/api/workbench/workspace-outputs",
            params={"session_id": "canvas-session-1"},
        )
        self.assertEqual(200, session_outputs.status_code)
        self.assertEqual(
            [output_id],
            [item["output_id"] for item in session_outputs.json()["outputs"]],
        )
        self.assertEqual(
            artifact["artifact_id"],
            session_outputs.json()["outputs"][0]["artifacts"][0]["artifact_id"],
        )

        project_outputs = self.client.get(
            "/api/workbench/workspace-outputs",
            params={"project_id": "project-canvas-1"},
        )
        self.assertEqual(200, project_outputs.status_code)
        self.assertEqual(
            [output_id],
            [item["output_id"] for item in project_outputs.json()["outputs"]],
        )

        history_response = self.client.get("/api/history/canvas-session-1")
        self.assertEqual(200, history_response.status_code)
        self.assertEqual(
            [output_id],
            [
                item["output_id"]
                for item in history_response.json()["workspace_outputs"]
            ],
        )


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiProtectedBlackboxContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_deploy_mode = os.environ.get("GOAT_DEPLOY_MODE")
        os.environ["GOAT_DEPLOY_MODE"] = "0"
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
            data_dir=root / "data",
            object_store_root=root / "object-store",
            api_key="secret-123",
            rate_limit_window_sec=60,
            rate_limit_max_requests=2,
            ready_skip_ollama_probe=True,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._original_deploy_mode is None:
            os.environ.pop("GOAT_DEPLOY_MODE", None)
        else:
            os.environ["GOAT_DEPLOY_MODE"] = self._original_deploy_mode
        self.tmpdir.cleanup()

    def test_health_stays_public_and_other_apis_require_api_key(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(200, health.status_code)
        self.assertIn("X-Request-ID", health.headers)

        ready = self.client.get("/api/ready")
        self.assertEqual(200, ready.status_code)
        self.assertTrue(ready.json().get("ready"))
        self.assertIn("X-Request-ID", ready.headers)

        protected_requests: list[tuple[str, str, dict[str, object]]] = [
            ("GET", "/api/models", {}),
            ("GET", "/api/models/capabilities?model=qwen3:4b", {}),
            (
                "POST",
                "/api/chat",
                {
                    "json": {
                        "model": "qwen3:4b",
                        "messages": [{"role": "user", "content": "hello"}],
                    }
                },
            ),
            (
                "POST",
                "/api/upload",
                {"files": {"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")}},
            ),
            (
                "POST",
                "/api/upload/analyze",
                {"files": {"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")}},
            ),
            (
                "POST",
                "/api/knowledge/uploads",
                {"files": {"file": ("strategy.pdf", b"%PDF-1.4", "application/pdf")}},
            ),
            (
                "POST",
                "/api/knowledge/ingestions",
                {
                    "json": {
                        "document_id": "doc-1",
                        "parser_profile": "default",
                        "chunking_profile": "default",
                        "embedding_profile": "default",
                    }
                },
            ),
            ("GET", "/api/knowledge/ingestions/ing-1", {}),
            (
                "POST",
                "/api/knowledge/search",
                {"json": {"query": "competitive strategy"}},
            ),
            (
                "POST",
                "/api/knowledge/answers",
                {"json": {"query": "competitive strategy"}},
            ),
            ("GET", "/api/history", {}),
            ("GET", "/api/history/missing", {}),
            ("DELETE", "/api/history/missing", {}),
            ("DELETE", "/api/history", {}),
            ("GET", "/api/system/gpu", {}),
            ("GET", "/api/system/inference", {}),
            ("GET", "/api/system/runtime-target", {}),
            ("GET", "/api/system/features", {}),
            ("GET", "/api/system/desktop", {}),
            ("POST", "/api/code-sandbox/exec", {}),
            ("POST", "/api/code-sandbox/executions/cs-1/cancel", {}),
            ("POST", "/api/code-sandbox/executions/cs-1/retry", {}),
            (
                "POST",
                "/api/workbench/tasks",
                {"json": {"task_kind": "plan", "prompt": "Draft a plan"}},
            ),
            ("POST", "/api/workbench/tasks/wb-1/cancel", {}),
            ("POST", "/api/workbench/tasks/wb-1/retry", {}),
            ("GET", "/api/workbench/sources", {}),
            ("GET", "/api/workbench/workspace-outputs?session_id=sess-1", {}),
            ("GET", "/api/workbench/workspace-outputs/wbo-1", {}),
            ("GET", "/api/workbench/tasks/wb-1", {}),
            ("GET", "/api/workbench/tasks/wb-1/events", {}),
            ("GET", "/api/system/metrics", {}),
        ]

        for method, path, kwargs in protected_requests:
            response = self.client.request(method, path, **kwargs)
            self.assertEqual(
                401, response.status_code, f"{method} {path} should require API key"
            )
            rj = response.json()
            self.assertEqual("Invalid or missing API key.", rj["detail"])
            self.assertEqual(AUTH_INVALID_API_KEY, rj["code"])
            self.assertIn("request_id", rj)
            self.assertIn("X-Request-ID", response.headers)

        ok = self.client.get("/api/history", headers={"X-GOAT-API-Key": "secret-123"})
        self.assertEqual(200, ok.status_code)
        self.assertEqual({"sessions": []}, ok.json())

    def test_metrics_endpoint_prometheus_text(self) -> None:
        headers = {"X-GOAT-API-Key": "secret-123"}
        response = self.client.get("/api/system/metrics", headers=headers)
        self.assertEqual(200, response.status_code)
        text = response.text
        self.assertIn("# HELP http_requests_total", text)
        self.assertIn("http_requests_total", text)
        self.assertIn("# TYPE http_request_duration_seconds histogram", text)
        self.assertIn("http_request_duration_seconds_bucket", text)
        self.assertIn("chat_stream_completed_total", text)
        self.assertIn("ollama_errors_total", text)
        self.assertIn("sqlite_log_write_failures_total", text)
        self.assertIn("feature_gate_denials_total", text)
        self.assertIn("knowledge_retrieval_requests_total", text)
        self.assertIn("knowledge_query_rewrite_applied_total", text)

    def test_rate_limit_contract_applies_after_threshold(self) -> None:
        headers = {"X-GOAT-API-Key": "secret-123"}

        first = self.client.get("/api/history", headers=headers)
        second = self.client.get("/api/history", headers=headers)
        limited = self.client.get("/api/history", headers=headers)

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(429, limited.status_code)
        lj = limited.json()
        self.assertEqual("Too many requests. Please try again shortly.", lj["detail"])
        self.assertEqual(RATE_LIMITED, lj["code"])
        self.assertIn("request_id", lj)
        self.assertIn("Retry-After", limited.headers)
        self.assertIn("X-Request-ID", limited.headers)


if __name__ == "__main__":
    unittest.main()
