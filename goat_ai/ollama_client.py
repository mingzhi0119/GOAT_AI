"""Ollama HTTP client — streaming APIs for SSE (FastAPI)."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Generator, Protocol

import requests

from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.telemetry_counters import OLLAMA_ERROR_API_CODE, inc_ollama_error
from goat_ai.tools import conversation_transcript, messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)


def _stream_line_tokens(chunk: dict) -> str:  # type: ignore[type-arg]
    if "message" in chunk and isinstance(chunk["message"], dict):
        return chunk["message"].get("content") or ""
    return chunk.get("response", "") or ""


@dataclass(frozen=True)
class ToolCallPlan:
    """Single native tool call requested by the model."""

    assistant_message: dict[str, Any]
    tool_name: str
    arguments: dict[str, Any]


# ── LLM client protocol (FastAPI / test injection) ────────────────────────────
class LLMClient(Protocol):
    """Structural interface satisfied by OllamaService (and test fakes)."""

    def list_model_names(self) -> list[str]: ...

    def get_model_capabilities(self, model: str) -> list[str]: ...

    def supports_tool_calling(self, model: str) -> bool: ...

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]: ...

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]: ...

    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> ToolCallPlan | None: ...

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]: ...

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        """Non-streaming /api/generate response body (session titles, etc.)."""
        ...


# ── Implementation ─────────────────────────────────────────────────────────────
class OllamaService:
    """HTTP client for Ollama streaming APIs (chat + generate)."""

    _cap_cache: dict[str, tuple[float, list[str]]] = {}
    _cache_lock = threading.Lock()

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._read_failure_count = 0
        self._breaker_open_until_monotonic = 0.0
        self._breaker_state = "closed"
        self._breaker_lock = threading.Lock()

    def _is_retryable_http_status(self, status_code: int) -> bool:
        return status_code in {408, 425, 429, 500, 502, 503, 504}

    def _before_read_call(self) -> None:
        now = time.monotonic()
        with self._breaker_lock:
            if self._breaker_state != "open":
                return
            if now >= self._breaker_open_until_monotonic:
                self._breaker_state = "half_open"
                return
        raise OllamaUnavailable("Ollama read circuit breaker is open")

    def _mark_read_success(self) -> None:
        with self._breaker_lock:
            self._read_failure_count = 0
            self._breaker_state = "closed"
            self._breaker_open_until_monotonic = 0.0

    def _mark_read_failure(self) -> None:
        with self._breaker_lock:
            if self._breaker_state == "half_open":
                self._breaker_state = "open"
                self._breaker_open_until_monotonic = time.monotonic() + float(
                    self._s.ollama_circuit_breaker_open_sec
                )
                self._read_failure_count = self._s.ollama_circuit_breaker_failures
                return

            self._read_failure_count += 1
            if self._read_failure_count >= self._s.ollama_circuit_breaker_failures:
                self._breaker_state = "open"
                self._breaker_open_until_monotonic = time.monotonic() + float(
                    self._s.ollama_circuit_breaker_open_sec
                )

    def _sleep_before_retry(self, attempt_index: int) -> None:
        base_sec = float(self._s.ollama_read_retry_base_ms) / 1000.0
        jitter_sec = random.uniform(
            0.0, float(self._s.ollama_read_retry_jitter_ms) / 1000.0
        )
        backoff_sec = base_sec * (2 ** max(0, attempt_index - 1))
        time.sleep(max(0.0, backoff_sec + jitter_sec))

    def _post_chat(
        self,
        payload: dict[str, Any],
        *,
        stream: bool,
        stream_timeout_sec: int | None = None,
    ) -> requests.Response:
        timeout: float | tuple[float, float]
        if stream:
            read_timeout = float(
                stream_timeout_sec
                if stream_timeout_sec is not None
                else self._s.generate_timeout
            )
            timeout = (5.0, read_timeout)
        else:
            timeout = float(self._s.generate_timeout)
        try:
            res = requests.post(
                f"{self._s.ollama_base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=timeout,
            )
            res.raise_for_status()
            return res
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in {400, 404, 422, 500}:
                logger.info("Ollama tool calling unavailable or rejected: %s", exc)
                raise ValueError("tool calling unavailable") from exc
            st = str(status_code) if status_code is not None else "none"
            inc_ollama_error(
                code=OLLAMA_ERROR_API_CODE, endpoint="chat", http_status=st
            )
            raise OllamaUnavailable("Cannot reach Ollama /api/chat") from exc
        except requests.RequestException as exc:
            inc_ollama_error(
                code=OLLAMA_ERROR_API_CODE, endpoint="chat", http_status="none"
            )
            raise OllamaUnavailable("Cannot reach Ollama /api/chat") from exc

    # ── Model list ────────────────────────────────────────────────────────────
    def list_model_names(self) -> list[str]:
        """Return names of locally available Ollama models."""
        self._before_read_call()
        attempts = max(1, int(self._s.ollama_read_retry_attempts))
        last_exc: Exception | None = None
        last_http_status = "none"
        for attempt in range(1, attempts + 1):
            try:
                res = requests.get(f"{self._s.ollama_base_url}/api/tags", timeout=5)
                res.raise_for_status()
                self._mark_read_success()
                names = [m["name"] for m in res.json().get("models", [])]
                # Invalidate capability cache when model inventory is queried freshly.
                with self._cache_lock:
                    known = set(self._cap_cache.keys())
                    current = set(names)
                    for removed in known - current:
                        self._cap_cache.pop(removed, None)
                return names
            except requests.HTTPError as exc:
                status_code = (
                    exc.response.status_code if exc.response is not None else None
                )
                last_http_status = (
                    str(status_code) if status_code is not None else "none"
                )
                last_exc = exc
                retryable = status_code is not None and self._is_retryable_http_status(
                    status_code
                )
                if retryable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                break

        self._mark_read_failure()
        inc_ollama_error(
            code=OLLAMA_ERROR_API_CODE, endpoint="tags", http_status=last_http_status
        )
        raise OllamaUnavailable("Cannot reach Ollama /api/tags") from last_exc

    def get_model_capabilities(self, model: str) -> list[str]:
        """Return the Ollama-reported capability strings for a model."""
        ttl_sec = max(0, int(self._s.model_cap_cache_ttl_sec))
        now = time.monotonic()
        if ttl_sec > 0:
            with self._cache_lock:
                cached = self._cap_cache.get(model)
                if cached is not None:
                    expires_at, capabilities = cached
                    if now < expires_at:
                        return list(capabilities)

        self._before_read_call()
        attempts = max(1, int(self._s.ollama_read_retry_attempts))
        last_exc: Exception | None = None
        last_http_status = "none"
        for attempt in range(1, attempts + 1):
            try:
                res = requests.post(
                    f"{self._s.ollama_base_url}/api/show",
                    json={"model": model},
                    timeout=5,
                )
                res.raise_for_status()
                self._mark_read_success()
                capabilities = res.json().get("capabilities", [])
                if not isinstance(capabilities, list):
                    normalized: list[str] = []
                else:
                    normalized = [str(item) for item in capabilities]

                if ttl_sec > 0:
                    with self._cache_lock:
                        self._cap_cache[model] = (now + ttl_sec, list(normalized))
                return normalized
            except requests.HTTPError as exc:
                status_code = (
                    exc.response.status_code if exc.response is not None else None
                )
                last_http_status = (
                    str(status_code) if status_code is not None else "none"
                )
                last_exc = exc
                retryable = status_code is not None and self._is_retryable_http_status(
                    status_code
                )
                if retryable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                break

        self._mark_read_failure()
        inc_ollama_error(
            code=OLLAMA_ERROR_API_CODE, endpoint="show", http_status=last_http_status
        )
        raise OllamaUnavailable("Cannot reach Ollama /api/show") from last_exc

    def supports_tool_calling(self, model: str) -> bool:
        """Return whether Ollama reports native tool-calling support for the model."""
        return "tools" in self.get_model_capabilities(model)

    # ── SSE / generator streaming (FastAPI) ───────────────────────────────────
    def yield_chat_tokens(
        self,
        model: str,
        api_messages: list[dict[str, str]],
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        """Yield raw token strings from /api/chat (for SSE)."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
        }
        if ollama_options:
            payload["options"] = ollama_options
        res = self._post_chat(
            payload,
            stream=True,
            stream_timeout_sec=self._s.chat_first_event_timeout_sec,
        )
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = _stream_line_tokens(chunk)
                if token:
                    yield token

    def yield_generate_tokens(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        """Yield raw token strings from /api/generate (for SSE)."""
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": True}
        if ollama_options:
            payload["options"] = ollama_options
        try:
            res = requests.post(
                f"{self._s.ollama_base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self._s.generate_timeout,
            )
            res.raise_for_status()
        except requests.RequestException as exc:
            inc_ollama_error(
                code=OLLAMA_ERROR_API_CODE, endpoint="generate", http_status="none"
            )
            raise OllamaUnavailable("Cannot reach Ollama /api/generate") from exc
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")
                if token:
                    yield token

    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        """Return a single non-streaming completion from /api/generate."""
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if ollama_options:
            payload["options"] = ollama_options
        try:
            res = requests.post(
                f"{self._s.ollama_base_url}/api/generate",
                json=payload,
                stream=False,
                timeout=self._s.generate_timeout,
            )
            res.raise_for_status()
        except requests.RequestException as exc:
            inc_ollama_error(
                code=OLLAMA_ERROR_API_CODE, endpoint="generate", http_status="none"
            )
            raise OllamaUnavailable("Cannot reach Ollama /api/generate") from exc
        data = res.json()
        return str(data.get("response") or "").strip()

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        """Unified token stream for the FastAPI layer (satisfies LLMClient Protocol)."""
        if self._s.use_chat_api:
            api_messages = messages_for_ollama(messages, system_prompt)
            yield from self.yield_chat_tokens(
                model, api_messages, ollama_options=ollama_options
            )
        else:
            transcript = conversation_transcript(messages)
            prompt = f"{system_prompt}\n\n{transcript}"
            yield from self.yield_generate_tokens(
                model, prompt, ollama_options=ollama_options
            )

    def stream_tokens_with_tools(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str | ToolCallPlan, None, None]:
        """Stream assistant tokens and surface native tool calls when they occur."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages_for_ollama(messages, system_prompt),
            "tools": tools,
            "stream": True,
        }
        if ollama_options:
            payload["options"] = ollama_options

        try:
            res = self._post_chat(
                payload,
                stream=True,
                stream_timeout_sec=self._s.chat_first_event_timeout_sec,
            )
        except ValueError:
            return

        for line in res.iter_lines():
            if not line:
                continue

            chunk = json.loads(line.decode("utf-8"))
            message = chunk.get("message")
            if isinstance(message, dict):
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list) and tool_calls:
                    first_call = tool_calls[0]
                    if isinstance(first_call, dict):
                        function = first_call.get("function")
                        if isinstance(function, dict):
                            name = function.get("name")
                            arguments = function.get("arguments")
                            if isinstance(name, str) and isinstance(arguments, dict):
                                yield ToolCallPlan(
                                    assistant_message={
                                        "role": str(message.get("role") or "assistant"),
                                        "content": str(message.get("content") or ""),
                                        "tool_calls": tool_calls,
                                    },
                                    tool_name=name,
                                    arguments=arguments,
                                )

            token = _stream_line_tokens(chunk)
            if token:
                yield token

    def plan_tool_call(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> ToolCallPlan | None:
        """Ask Ollama for a single native tool call plan without streaming."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages_for_ollama(messages, system_prompt),
            "tools": tools,
            "stream": False,
        }
        if ollama_options:
            payload["options"] = ollama_options

        try:
            res = self._post_chat(payload, stream=False)
        except ValueError:
            return None

        data = res.json()
        message = data.get("message")
        if not isinstance(message, dict):
            return None

        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            return None

        first_call = tool_calls[0]
        if not isinstance(first_call, dict):
            return None
        function = first_call.get("function")
        if not isinstance(function, dict):
            return None

        name = function.get("name")
        arguments = function.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return None

        return ToolCallPlan(
            assistant_message=message,
            tool_name=name,
            arguments=arguments,
        )

    def stream_tool_followup(
        self,
        model: str,
        followup_messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]:
        """Stream the model's final response after a tool result is appended."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": followup_messages,
            "tools": tools,
            "stream": True,
        }
        if ollama_options:
            payload["options"] = ollama_options

        try:
            res = self._post_chat(
                payload,
                stream=True,
                stream_timeout_sec=self._s.chat_first_event_timeout_sec,
            )
        except ValueError:
            return

        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = _stream_line_tokens(chunk)
                if token:
                    yield token
