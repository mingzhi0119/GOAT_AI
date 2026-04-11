from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]

from goat_ai.config import Settings

if TestClient is not None:
    from backend.config import get_settings
    from backend.dependencies import get_code_sandbox_provider
    from backend.main import create_app
    from backend.services import log_service
    from backend.services.code_sandbox_provider import (
        SandboxProviderRequest,
        SandboxProviderResult,
    )


class _FakeSandboxProvider:
    provider_name = "localhost"
    isolation_level = "host"
    network_policy_enforced = False

    def run_stream(self, request: SandboxProviderRequest):
        _ = request
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="sandbox ok",
            stderr="",
            timed_out=False,
            error_detail=None,
            output_files=[],
        )


def _parse_sse_payloads(body: str) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class OpenAIProviderIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            llm_provider="openai",
            ollama_base_url="http://127.0.0.1:11434",
            openai_base_url="https://api.openai.com/v1",
            openai_api_key="test-key",
            openai_models=("gpt-4.1-mini", "gpt-4.1"),
            openai_vision_models=("gpt-4.1",),
            openai_tool_models=("gpt-4.1",),
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
        )
        log_service.init_db(self.settings.log_db_path)
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_models_ready_and_chat_follow_openai_provider(self) -> None:
        ready_response = MagicMock()
        ready_response.raise_for_status.return_value = None
        ready_response.status_code = 200

        chat_response = MagicMock()
        chat_response.raise_for_status.return_value = None
        chat_response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Hello"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" from OpenAI"}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        with (
            patch(
                "backend.readiness_service.requests.get",
                return_value=ready_response,
            ) as get_mock,
            patch(
                "goat_ai.openai_client.requests.post",
                return_value=chat_response,
            ) as post_mock,
        ):
            ready = self.client.get("/api/ready")
            models = self.client.get("/api/models")
            caps = self.client.get(
                "/api/models/capabilities", params={"model": "gpt-4.1"}
            )
            chat = self.client.post(
                "/api/chat",
                json={
                    "model": "gpt-4.1-mini",
                    "messages": [{"role": "user", "content": "Hello there"}],
                },
            )

        self.assertEqual(200, ready.status_code)
        ready_body = ready.json()
        self.assertTrue(ready_body["ready"])
        self.assertEqual(
            "openai",
            ready_body["checks"]["inference_backend"]["provider"],
        )
        self.assertEqual(
            "https://api.openai.com/v1/models",
            get_mock.call_args.args[0],
        )

        self.assertEqual(200, models.status_code)
        self.assertEqual(["gpt-4.1-mini", "gpt-4.1"], models.json()["models"])

        self.assertEqual(200, caps.status_code)
        caps_body = caps.json()
        self.assertEqual("gpt-4.1", caps_body["model"])
        self.assertTrue(caps_body["supports_vision"])
        self.assertTrue(caps_body["supports_tool_calling"])

        self.assertEqual(200, chat.status_code)
        events = _parse_sse_payloads(chat.text)
        self.assertEqual(
            ["token", "token", "done"], [event["type"] for event in events]
        )
        self.assertEqual("Hello", events[0]["token"])
        self.assertEqual(" from OpenAI", events[1]["token"])

        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual("gpt-4.1-mini", payload["model"])
        self.assertTrue(payload["stream"])

    def test_openai_provider_supports_vision_chat(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500001d0d4e0aea0000000049454e44ae426082"
        )
        upload = self.client.post(
            "/api/media/uploads",
            files={"file": ("vision.png", png, "image/png")},
        )
        self.assertEqual(200, upload.status_code)
        attachment_id = upload.json()["attachment_id"]

        chat_response = MagicMock()
        chat_response.raise_for_status.return_value = None
        chat_response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Vision"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" works"}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        with patch(
            "goat_ai.openai_client.requests.post",
            return_value=chat_response,
        ) as post_mock:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "What is in this image?"}],
                    "image_attachment_ids": [attachment_id],
                },
            )

        self.assertEqual(200, response.status_code)
        events = _parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "token", "done"], [event["type"] for event in events]
        )
        payload = post_mock.call_args.kwargs["json"]
        content = payload["input"][1]["content"]
        self.assertEqual("input_text", content[0]["type"])
        self.assertEqual("input_image", content[1]["type"])

    def test_openai_provider_chart_tool_path_uses_function_calls(self) -> None:
        tool_plan_response = MagicMock()
        tool_plan_response.raise_for_status.return_value = None
        tool_plan_response.json.return_value = {
            "id": "resp_chart_1",
            "output": [
                {
                    "type": "function_call",
                    "name": "generate_chart_v2",
                    "call_id": "call_chart_1",
                    "arguments": json.dumps(
                        {
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
                        }
                    ),
                }
            ],
        }
        followup_response = MagicMock()
        followup_response.raise_for_status.return_value = None
        followup_response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Here is"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" the chart-driven answer."}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        file_context = (
            "[User uploaded tabular data for analysis]\n\n"
            "Column names: month, revenue.\n\n"
            "CHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\nFeb,12\n```\n"
        )
        with patch(
            "goat_ai.openai_client.requests.post",
            side_effect=[tool_plan_response, followup_response],
        ) as post_mock:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "gpt-4.1",
                    "messages": [
                        {"role": "user", "content": file_context},
                        {
                            "role": "assistant",
                            "content": "I have loaded the file context.",
                        },
                        {"role": "user", "content": "Please chart the revenue trend."},
                    ],
                },
            )

        self.assertEqual(200, response.status_code)
        events = _parse_sse_payloads(response.text)
        self.assertTrue(any(event["type"] == "chart_spec" for event in events))
        text = "".join(
            event.get("token", "") for event in events if event["type"] == "token"
        )
        self.assertIn("chart-driven answer", text)
        first_payload = post_mock.call_args_list[0].kwargs["json"]
        self.assertEqual("generate_chart_v2", first_payload["tools"][0]["name"])
        second_payload = post_mock.call_args_list[1].kwargs["json"]
        self.assertEqual("resp_chart_1", second_payload["previous_response_id"])
        self.assertEqual("call_chart_1", second_payload["input"][0]["call_id"])

    def test_openai_provider_code_sandbox_tool_path_executes_tool(self) -> None:
        self.settings = replace(
            self.settings,
            feature_code_sandbox_enabled=True,
            code_sandbox_provider="localhost",
        )
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        self.client.app.dependency_overrides[get_code_sandbox_provider] = lambda: (
            _FakeSandboxProvider()
        )

        tool_plan_response = MagicMock()
        tool_plan_response.raise_for_status.return_value = None
        tool_plan_response.json.return_value = {
            "id": "resp_sandbox_1",
            "output": [
                {
                    "type": "function_call",
                    "name": "execute_code_sandbox",
                    "call_id": "call_sandbox_1",
                    "arguments": json.dumps(
                        {
                            "runtime_preset": "shell",
                            "command": "echo sandbox ok",
                            "timeout_sec": 4,
                        }
                    ),
                }
            ],
        }
        followup_response = MagicMock()
        followup_response.raise_for_status.return_value = None
        followup_response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Sandbox"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" result confirmed."}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        try:
            with patch(
                "goat_ai.openai_client.requests.post",
                side_effect=[tool_plan_response, followup_response],
            ) as post_mock:
                response = self.client.post(
                    "/api/chat",
                    json={
                        "model": "gpt-4.1",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Use code sandbox to run a quick command and report the result.",
                            }
                        ],
                    },
                )

            self.assertEqual(200, response.status_code)
            events = _parse_sse_payloads(response.text)
            text = "".join(
                event.get("token", "") for event in events if event["type"] == "token"
            )
            self.assertIn("Sandbox result confirmed.", text)
            first_payload = post_mock.call_args_list[0].kwargs["json"]
            self.assertEqual(
                "execute_code_sandbox",
                first_payload["tools"][0]["name"],
            )
            second_payload = post_mock.call_args_list[1].kwargs["json"]
            self.assertEqual("resp_sandbox_1", second_payload["previous_response_id"])
            self.assertEqual("call_sandbox_1", second_payload["input"][0]["call_id"])
            self.assertIn('"status": "completed"', second_payload["input"][0]["output"])
        finally:
            self.client.app.dependency_overrides.pop(get_code_sandbox_provider, None)

    def test_session_chat_generates_title_through_openai_provider(self) -> None:
        stream_response = MagicMock()
        stream_response.raise_for_status.return_value = None
        stream_response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Planned"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" answer"}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        title_response = MagicMock()
        title_response.raise_for_status.return_value = None
        title_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "OpenAI title"}],
                }
            ]
        }

        with patch(
            "goat_ai.openai_client.requests.post",
            side_effect=[stream_response, title_response],
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "model": "gpt-4.1-mini",
                    "session_id": "openai-session-1",
                    "messages": [{"role": "user", "content": "Draft a plan"}],
                },
            )

        self.assertEqual(200, response.status_code)
        events = _parse_sse_payloads(response.text)
        self.assertEqual(
            ["token", "token", "done"], [event["type"] for event in events]
        )

        history = self.client.get("/api/history/openai-session-1")
        self.assertEqual(200, history.status_code)
        body = history.json()
        self.assertEqual("OpenAI title", body["title"])
        self.assertEqual("Planned answer", body["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
