from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from goat_ai.openai_client import OpenAIService
from goat_ai.ollama_client import StreamTextPart
from goat_ai.types import ChatTurn


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="test-key",
        openai_models=("gpt-4.1-mini",),
        openai_vision_models=("gpt-4.1-mini",),
        openai_thinking_models=("gpt-4.1-mini",),
        openai_tool_models=("gpt-4.1-mini",),
        generate_timeout=30,
    )


class OpenAIServiceTests(unittest.TestCase):
    def test_list_model_names_comes_from_config(self) -> None:
        service = OpenAIService(_settings())
        self.assertEqual(["gpt-4.1-mini"], service.list_model_names())

    def test_stream_tokens_parses_content_and_reasoning_deltas(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.reasoning.delta","delta":"thinking..."}',
                "",
                'data: {"type":"response.output_text.delta","delta":"Hello"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" world"}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        with patch(
            "goat_ai.openai_client.requests.post", return_value=response
        ) as post_mock:
            service = OpenAIService(_settings())
            items = list(
                service.stream_tokens(
                    "gpt-4.1-mini",
                    [ChatTurn(role="user", content="Hi")],
                    "system",
                    ollama_options={"think": "medium", "num_predict": 64},
                )
            )

        self.assertEqual(
            [
                StreamTextPart("thinking", "thinking..."),
                StreamTextPart("content", "Hello"),
                StreamTextPart("content", " world"),
            ],
            items,
        )
        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual("gpt-4.1-mini", payload["model"])
        self.assertEqual({"effort": "medium"}, payload["reasoning"])
        self.assertEqual(64, payload["max_output_tokens"])

    def test_stream_tokens_attaches_images_for_vision_requests(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.output_text.delta","delta":"Vision"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" ok"}',
                "",
                "data: [DONE]",
                "",
            ]
        )

        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
            "/x8AAwMCAO+aX1cAAAAASUVORK5CYII="
        )
        with patch(
            "goat_ai.openai_client.requests.post", return_value=response
        ) as post_mock:
            service = OpenAIService(_settings())
            items = list(
                service.stream_tokens(
                    "gpt-4.1-mini",
                    [ChatTurn(role="user", content="What is in this image?")],
                    "system",
                    last_user_images_base64=[png_b64],
                )
            )

        self.assertEqual(
            [StreamTextPart("content", "Vision"), StreamTextPart("content", " ok")],
            items,
        )
        payload = post_mock.call_args.kwargs["json"]
        content = payload["input"][1]["content"]
        self.assertEqual("input_text", content[0]["type"])
        self.assertEqual("input_image", content[1]["type"])
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))

    def test_stream_tokens_with_tools_surfaces_function_call_plan(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "id": "resp_123",
            "output": [
                {
                    "type": "function_call",
                    "name": "generate_chart_v2",
                    "call_id": "call_456",
                    "arguments": '{"version":"2.0","chart_type":"line","title":"Revenue trend","x_key":"month","series":[{"key":"revenue","name":"Revenue","aggregate":"none"}]}',
                }
            ],
        }

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_chart_v2",
                    "description": "Create a chart intent.",
                    "parameters": {"type": "object"},
                },
            }
        ]
        with patch(
            "goat_ai.openai_client.requests.post", return_value=response
        ) as post_mock:
            service = OpenAIService(_settings())
            items = list(
                service.stream_tokens_with_tools(
                    "gpt-4.1-mini",
                    [ChatTurn(role="user", content="Chart the revenue trend.")],
                    "system",
                    tools=tools,
                )
            )

        self.assertEqual(1, len(items))
        tool_plan = items[0]
        self.assertEqual("generate_chart_v2", tool_plan.tool_name)
        self.assertEqual(
            "resp_123", tool_plan.assistant_message["_openai_previous_response_id"]
        )
        self.assertEqual(
            "call_456", tool_plan.assistant_message["_openai_function_call_id"]
        )
        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual(
            [
                {
                    "type": "function",
                    "name": "generate_chart_v2",
                    "description": "Create a chart intent.",
                    "parameters": {"type": "object"},
                }
            ],
            payload["tools"],
        )

    def test_stream_tool_followup_uses_previous_response_and_function_output(
        self,
    ) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.iter_lines.return_value = iter(
            [
                'data: {"type":"response.reasoning.delta","delta":"thinking"}',
                "",
                'data: {"type":"response.output_text.delta","delta":"Chart"}',
                "",
                'data: {"type":"response.output_text.delta","delta":" answer"}',
                "",
                "data: [DONE]",
                "",
            ]
        )
        followup_messages = [
            {
                "role": "assistant",
                "_openai_previous_response_id": "resp_123",
                "_openai_function_call_id": "call_456",
                "tool_calls": [
                    {
                        "id": "call_456",
                        "type": "function",
                        "function": {"name": "generate_chart_v2", "arguments": {}},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_name": "generate_chart_v2",
                "content": '{"chart":{"title":"Revenue trend"}}',
            },
        ]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_chart_v2",
                    "parameters": {"type": "object"},
                },
            }
        ]
        with patch(
            "goat_ai.openai_client.requests.post", return_value=response
        ) as post_mock:
            service = OpenAIService(_settings())
            items = list(
                service.stream_tool_followup(
                    "gpt-4.1-mini",
                    followup_messages,
                    tools=tools,
                )
            )

        self.assertEqual(
            [
                StreamTextPart("thinking", "thinking"),
                StreamTextPart("content", "Chart"),
                StreamTextPart("content", " answer"),
            ],
            items,
        )
        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual("resp_123", payload["previous_response_id"])
        self.assertEqual("call_456", payload["input"][0]["call_id"])
        self.assertEqual(
            '{"chart":{"title":"Revenue trend"}}',
            payload["input"][0]["output"],
        )

    def test_generate_completion_extracts_output_text(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "Generated title"},
                    ],
                }
            ]
        }

        with patch("goat_ai.openai_client.requests.post", return_value=response):
            service = OpenAIService(_settings())
            out = service.generate_completion("gpt-4.1-mini", "Summarize this.")

        self.assertEqual("Generated title", out)


if __name__ == "__main__":
    unittest.main()
