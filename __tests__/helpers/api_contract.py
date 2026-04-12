from __future__ import annotations

import json
from typing import Any

from goat_ai.ollama_client import ToolCallPlan
from goat_ai.types import ChatTurn


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
        _ = (model, user_text, assistant_text)
        return self._title


class ContractFakeLLM:
    def list_model_names(self) -> list[str]:
        return ["blackbox-model", "viz-model"]

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        if model == "viz-model":
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
        _ = ollama_options
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
        _ = tools, ollama_options
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
        _ = (model, messages, system_prompt, tools, ollama_options)
        return None

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]],
        ollama_options: dict[str, float | int] | None = None,
    ):
        _ = (model, followup_messages, tools, ollama_options)
        yield "Chart answer"

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        _ = (model, prompt, ollama_options)
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
