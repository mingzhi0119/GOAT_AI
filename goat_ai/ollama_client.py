"""Ollama HTTP client — streaming APIs for both Streamlit (placeholder) and SSE (generator)."""
from __future__ import annotations

import json
import logging
from typing import Any, Generator, Protocol, Sequence

import requests

from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.tools import conversation_transcript, messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)


# ── Streamlit-side protocol (markdown placeholder) ────────────────────────────
class _StreamPlaceholder(Protocol):
    def markdown(self, body: str) -> Any: ...


def _stream_line_tokens(chunk: dict) -> str:  # type: ignore[type-arg]
    if "message" in chunk and isinstance(chunk["message"], dict):
        return chunk["message"].get("content") or ""
    return chunk.get("response", "") or ""


# ── LLM client protocol (FastAPI / test injection) ────────────────────────────
class LLMClient(Protocol):
    """Structural interface satisfied by OllamaService (and test fakes)."""

    def list_model_names(self) -> list[str]: ...

    def stream_tokens(
        self,
        model: str,
        messages: list[ChatTurn],
        system_prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> Generator[str, None, None]: ...


# ── Implementation ─────────────────────────────────────────────────────────────
class OllamaService:
    """HTTP client for Ollama streaming APIs (chat + generate)."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    # ── Model list ────────────────────────────────────────────────────────────
    def list_model_names(self) -> list[str]:
        """Return names of locally available Ollama models."""
        try:
            res = requests.get(f"{self._s.ollama_base_url}/api/tags", timeout=5)
            res.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaUnavailable("Cannot reach Ollama /api/tags") from exc
        return [m["name"] for m in res.json().get("models", [])]

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
        try:
            res = requests.post(
                f"{self._s.ollama_base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self._s.generate_timeout,
            )
            res.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaUnavailable("Cannot reach Ollama /api/chat") from exc
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
            raise OllamaUnavailable("Cannot reach Ollama /api/generate") from exc
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")
                if token:
                    yield token

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

    # ── Streamlit placeholder streaming (kept for backward compat) ────────────
    def stream_chat(
        self,
        model: str,
        api_messages: list[dict[str, str]],
        placeholder: _StreamPlaceholder,
    ) -> str:
        full_response = ""
        for token in self.yield_chat_tokens(model, api_messages, ollama_options=None):
            full_response += token
            placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response

    def stream_generate(
        self, model: str, prompt: str, placeholder: _StreamPlaceholder
    ) -> str:
        full_response = ""
        for token in self.yield_generate_tokens(model, prompt, ollama_options=None):
            full_response += token
            placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response

    def stream_from_session(
        self,
        model: str,
        state_messages: Sequence[ChatTurn],
        placeholder: _StreamPlaceholder,
    ) -> str:
        if self._s.use_chat_api:
            msgs = messages_for_ollama(state_messages, self._s.system_prompt)
            return self.stream_chat(model, msgs, placeholder)
        transcript = conversation_transcript(state_messages)
        combined = f"{self._s.system_prompt}\n\n{transcript}"
        return self.stream_generate(model, combined, placeholder)
