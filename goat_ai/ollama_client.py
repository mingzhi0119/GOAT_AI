from __future__ import annotations

import json
import logging
from typing import Any, Protocol, Sequence

import requests

from goat_ai.config import Settings
from goat_ai.tools import conversation_transcript, messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)


class _StreamPlaceholder(Protocol):
    def markdown(self, body: str) -> Any: ...


def _stream_line_tokens(chunk: dict) -> str:
    if "message" in chunk and isinstance(chunk["message"], dict):
        return chunk["message"].get("content") or ""
    return chunk.get("response", "") or ""


class OllamaService:
    """HTTP client for Ollama streaming APIs (chat + generate)."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def list_model_names(self) -> list[str]:
        res = requests.get(f"{self._s.ollama_base_url}/api/tags", timeout=5)
        res.raise_for_status()
        return [m["name"] for m in res.json().get("models", [])]

    def stream_chat(
        self,
        model: str,
        api_messages: list[dict[str, str]],
        placeholder: _StreamPlaceholder,
    ) -> str:
        full_response = ""
        res = requests.post(
            f"{self._s.ollama_base_url}/api/chat",
            json={"model": model, "messages": api_messages, "stream": True},
            stream=True,
            timeout=self._s.generate_timeout,
        )
        res.raise_for_status()
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = _stream_line_tokens(chunk)
                full_response += token
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response

    def stream_generate(self, model: str, prompt: str, placeholder: _StreamPlaceholder) -> str:
        full_response = ""
        res = requests.post(
            f"{self._s.ollama_base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
            timeout=self._s.generate_timeout,
        )
        res.raise_for_status()
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")
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
