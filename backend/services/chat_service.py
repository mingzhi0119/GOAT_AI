"""Chat service — orchestrates LLMClient + converts Pydantic models to goat_ai types."""
from __future__ import annotations

import json
import logging
from typing import Generator

from backend.models.chat import ChatMessage
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import LLMClient
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)

_DONE_SENTINEL = "[DONE]"


def _to_chat_turns(messages: list[ChatMessage]) -> list[ChatTurn]:
    """Convert Pydantic ChatMessage list to goat_ai ChatTurn dicts."""
    return [ChatTurn(role=m.role, content=m.content) for m in messages]


def sse_event(data: str) -> str:
    """Format a string payload as a Server-Sent Event line."""
    return f"data: {json.dumps(data)}\n\n"


def stream_chat_sse(
    *,
    llm: LLMClient,
    model: str,
    messages: list[ChatMessage],
    system_prompt: str,
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion.

    Each event carries a JSON-encoded token string.
    The final event carries the sentinel "[DONE]".
    On Ollama errors the stream emits "[ERROR] <message>" then "[DONE]".
    """
    turns = _to_chat_turns(messages)
    try:
        for token in llm.stream_tokens(model, turns, system_prompt):
            yield sse_event(token)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unavailable during chat stream: %s", exc)
        yield sse_event("[ERROR] AI service temporarily unavailable.")
    except Exception:
        logger.exception("Unexpected error during chat stream")
        yield sse_event("[ERROR] An unexpected error occurred.")
    finally:
        yield sse_event(_DONE_SENTINEL)
