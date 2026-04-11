"""OpenAI-compatible HTTP client for provider-backed chat and completion flows."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Generator

import requests

from goat_ai.config import Settings
from goat_ai.exceptions import LLMBackendUnavailable
from goat_ai.otel_tracing import otel_span
from goat_ai.ollama_client import LLMClient, StreamTextPart, ToolCallPlan
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)


def _message_payload(
    messages: list[ChatTurn],
    *,
    system_prompt: str,
    last_user_images_base64: list[str] | None = None,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    if system_prompt.strip():
        payload.append({"role": "system", "content": system_prompt})
    last_user_index: int | None = None
    if last_user_images_base64:
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            role = (
                str(message.get("role", "user"))
                if isinstance(message, dict)
                else message.role
            )
            if role == "user":
                last_user_index = index
                break
    for message_index, message in enumerate(messages):
        if isinstance(message, dict):
            role = str(message.get("role", "user"))
            content = str(message.get("content", ""))
        else:
            role = message.role
            content = message.content
        if (
            role == "user"
            and last_user_index is not None
            and message_index == last_user_index
            and last_user_images_base64
        ):
            parts: list[dict[str, Any]] = []
            if content:
                parts.append({"type": "input_text", "text": content})
            for image_b64 in last_user_images_base64:
                parts.append(
                    {
                        "type": "input_image",
                        "image_url": (
                            f"data:{_guess_image_mime_type(image_b64)};base64,{image_b64}"
                        ),
                    }
                )
            payload.append({"role": role, "content": parts})
            continue
        payload.append({"role": role, "content": content})
    return payload


def _guess_image_mime_type(image_b64: str) -> str:
    try:
        raw = base64.b64decode(image_b64, validate=False)
    except Exception:
        return "image/png"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _iter_sse_json(
    response: requests.Response,
) -> Generator[dict[str, Any], None, None]:
    data_lines: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip()
        if not line:
            if not data_lines:
                continue
            data_text = "\n".join(data_lines)
            data_lines = []
            if data_text == "[DONE]":
                break
            try:
                yield json.loads(data_text)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping non-JSON SSE chunk from OpenAI-compatible stream"
                )
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())

    if data_lines:
        data_text = "\n".join(data_lines)
        if data_text != "[DONE]":
            try:
                yield json.loads(data_text)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping trailing non-JSON SSE chunk from OpenAI-compatible stream"
                )


def _extract_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        if parts:
            return "".join(parts)
    text = payload.get("output_text")
    if isinstance(text, str):
        return text
    return ""


def _apply_request_options(
    payload: dict[str, Any],
    *,
    ollama_options: dict[str, float | int | bool | str] | None,
) -> None:
    if not ollama_options:
        return
    if (temperature := ollama_options.get("temperature")) is not None:
        payload["temperature"] = temperature
    if (top_p := ollama_options.get("top_p")) is not None:
        payload["top_p"] = top_p
    if (max_tokens := ollama_options.get("num_predict")) is not None:
        payload["max_output_tokens"] = max_tokens
    if (think := ollama_options.get("think")) in {"low", "medium", "high"}:
        payload["reasoning"] = {"effort": think}


def _normalize_tools_for_responses(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function")
        if tool.get("type") == "function" and isinstance(function, dict):
            item: dict[str, Any] = {
                "type": "function",
                "name": str(function.get("name", "")),
                "parameters": function.get("parameters", {}),
            }
            description = function.get("description")
            if isinstance(description, str) and description:
                item["description"] = description
            normalized.append(item)
            continue
        normalized.append(tool)
    return normalized


def _extract_tool_call_plan(payload: dict[str, Any]) -> ToolCallPlan | None:
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    response_id = payload.get("id")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        tool_name = item.get("name")
        call_id = item.get("call_id")
        raw_arguments = item.get("arguments")
        if not isinstance(tool_name, str):
            continue
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping invalid JSON tool arguments from OpenAI response"
                )
                continue
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            continue
        if not isinstance(arguments, dict):
            continue
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": _extract_output_text(payload),
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }
            ],
        }
        if isinstance(response_id, str) and response_id:
            assistant_message["_openai_previous_response_id"] = response_id
        if isinstance(call_id, str) and call_id:
            assistant_message["_openai_function_call_id"] = call_id
        return ToolCallPlan(
            assistant_message=assistant_message,
            tool_name=tool_name,
            arguments=arguments,
        )
    return None


def _extract_openai_followup_context(
    followup_messages: list[dict[str, Any]],
) -> tuple[str | None, str | None, str | None]:
    previous_response_id: str | None = None
    call_id: str | None = None
    tool_output: str | None = None
    for message in followup_messages:
        role = str(message.get("role", ""))
        if role == "assistant":
            previous_response_id = message.get("_openai_previous_response_id")
            if not isinstance(previous_response_id, str):
                previous_response_id = None
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                first_call = tool_calls[0]
                if isinstance(first_call, dict):
                    raw_call_id = first_call.get("id") or message.get(
                        "_openai_function_call_id"
                    )
                    if isinstance(raw_call_id, str) and raw_call_id:
                        call_id = raw_call_id
        elif role == "tool":
            content = message.get("content")
            if isinstance(content, str):
                tool_output = content
    return previous_response_id, call_id, tool_output


class OpenAIService(LLMClient):
    """OpenAI-compatible inference client using the Responses API."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._s.openai_api_key}",
            "Content-Type": "application/json",
        }

    def _capabilities_for_model(self, model: str) -> list[str]:
        capabilities = ["completion"]
        if model in self._s.openai_vision_models:
            capabilities.append("vision")
        if model in self._s.openai_tool_models:
            capabilities.append("tools")
        if model in self._s.openai_thinking_models:
            capabilities.append("thinking")
        return capabilities

    def _post_responses(
        self,
        payload: dict[str, Any],
        *,
        stream: bool,
    ) -> requests.Response:
        try:
            with otel_span("openai.api.responses", stream=str(stream)):
                response = requests.post(
                    f"{self._s.openai_base_url}/responses",
                    headers=self._headers,
                    json=payload,
                    stream=stream,
                    timeout=(5.0, float(self._s.generate_timeout)),
                )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise LLMBackendUnavailable(
                "Cannot reach the configured OpenAI-compatible backend."
            ) from exc

    def list_model_names(self) -> list[str]:
        return list(self._s.openai_models)

    def describe_model_for_api(self, model: str) -> tuple[list[str], int | None]:
        return self._capabilities_for_model(model), None

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
        ollama_options: dict[str, float | int | bool | str] | None = None,
        last_user_images_base64: list[str] | None = None,
    ) -> Generator[str | StreamTextPart, None, None]:
        payload: dict[str, Any] = {
            "model": model,
            "input": _message_payload(
                messages,
                system_prompt=system_prompt,
                last_user_images_base64=last_user_images_base64,
            ),
            "stream": True,
        }
        _apply_request_options(payload, ollama_options=ollama_options)
        response = self._post_responses(payload, stream=True)
        for event in _iter_sse_json(response):
            event_type = str(event.get("type", ""))
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    yield StreamTextPart("content", delta)
            elif event_type in {
                "response.reasoning.delta",
                "response.reasoning_summary.delta",
            }:
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    yield StreamTextPart("thinking", delta)

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int | bool | str] | None = None,
    ) -> Generator[str | StreamTextPart | ToolCallPlan, None, None]:
        payload: dict[str, Any] = {
            "model": model,
            "input": _message_payload(messages, system_prompt=system_prompt),
            "tools": _normalize_tools_for_responses(tools),
            "stream": False,
        }
        _apply_request_options(payload, ollama_options=ollama_options)
        response = self._post_responses(payload, stream=False)
        response_json = response.json()
        tool_plan = _extract_tool_call_plan(response_json)
        if tool_plan is not None:
            yield tool_plan
            return
        output_text = _extract_output_text(response_json)
        if output_text:
            yield StreamTextPart("content", output_text)

    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int | bool | str] | None = None,
    ) -> ToolCallPlan | None:
        payload: dict[str, Any] = {
            "model": model,
            "input": _message_payload(messages, system_prompt=system_prompt),
            "tools": _normalize_tools_for_responses(tools),
            "stream": False,
        }
        _apply_request_options(payload, ollama_options=ollama_options)
        response = self._post_responses(payload, stream=False)
        return _extract_tool_call_plan(response.json())

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int | bool | str] | None = None,
    ) -> Generator[str | StreamTextPart, None, None]:
        previous_response_id, call_id, tool_output = _extract_openai_followup_context(
            followup_messages
        )
        if previous_response_id and call_id and tool_output is not None:
            payload: dict[str, Any] = {
                "model": model,
                "previous_response_id": previous_response_id,
                "input": [
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": tool_output,
                    }
                ],
                "tools": _normalize_tools_for_responses(tools),
                "stream": True,
            }
            _apply_request_options(payload, ollama_options=ollama_options)
            response = self._post_responses(payload, stream=True)
            for event in _iter_sse_json(response):
                event_type = str(event.get("type", ""))
                if event_type == "response.output_text.delta":
                    delta = event.get("delta")
                    if isinstance(delta, str) and delta:
                        yield StreamTextPart("content", delta)
                elif event_type in {
                    "response.reasoning.delta",
                    "response.reasoning_summary.delta",
                }:
                    delta = event.get("delta")
                    if isinstance(delta, str) and delta:
                        yield StreamTextPart("thinking", delta)
            return
        chat_turns = [
            ChatTurn(
                role=str(message.get("role", "user")),
                content=str(message.get("content", "")),
            )
            for message in followup_messages
            if str(message.get("role", "")) in {"user", "assistant", "system"}
        ]
        yield from self.stream_tokens(
            model,
            chat_turns,
            system_prompt="",
            ollama_options=ollama_options,
        )

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int | bool | str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "input": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        _apply_request_options(payload, ollama_options=ollama_options)
        response = self._post_responses(payload, stream=False)
        return _extract_output_text(response.json()).strip()
