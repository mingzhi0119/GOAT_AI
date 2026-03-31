"""Chat service — orchestrates LLMClient + converts Pydantic models to goat_ai types."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from backend.models.chat import ChatMessage
from backend.services import log_service
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


def _last_user_message(messages: list[ChatMessage]) -> str:
    """Return the content of the final role=user message, or empty string."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def _build_system_prompt(base_prompt: str, user_name: str) -> str:
    """Append a personalisation hint to the system prompt when a name is provided."""
    if not user_name:
        return base_prompt
    return f"{base_prompt}\n\nThe student's name is {user_name}. Feel free to address them by name."


def _build_session_title(messages: list[ChatMessage]) -> str:
    """Build a short sidebar title from the first user message."""
    for msg in messages:
        if msg.role == "user":
            text = msg.content.strip().replace("\n", " ")
            return text[:80] if len(text) > 80 else text
    return "New Chat"


def stream_chat_sse(
    *,
    llm: LLMClient,
    model: str,
    messages: list[ChatMessage],
    system_prompt: str,
    ip: str,
    log_db_path: Path,
    user_name: str = "",
    session_id: str | None = None,
    all_messages: list[ChatMessage] | None = None,
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion.

    Each event carries a JSON-encoded token string.
    The final event carries the sentinel "[DONE]".
    On Ollama errors the stream emits "[ERROR] <message>" then "[DONE]".
    After the stream completes the full conversation is appended to the log DB.
    """
    turns = _to_chat_turns(messages)
    effective_prompt = _build_system_prompt(system_prompt, user_name)
    buf: list[str] = []
    t_start = time.monotonic()

    try:
        for token in llm.stream_tokens(model, turns, effective_prompt):
            buf.append(token)
            yield sse_event(token)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unavailable during chat stream: %s", exc)
        yield sse_event("[ERROR] AI service temporarily unavailable.")
    except Exception:
        logger.exception("Unexpected error during chat stream")
        yield sse_event("[ERROR] An unexpected error occurred.")
    finally:
        yield sse_event(_DONE_SENTINEL)
        elapsed_ms = round((time.monotonic() - t_start) * 1000)
        log_service.log_conversation(
            db_path=log_db_path,
            ip=ip,
            model=model,
            turn_count=len(messages),
            user_message=_last_user_message(messages),
            assistant_response="".join(buf),
            response_ms=elapsed_ms,
            user_name=user_name,
            session_id=session_id,
        )
        if session_id:
            final_messages = all_messages if all_messages is not None else messages
            now_iso = datetime.now(timezone.utc).isoformat()
            existing = log_service.get_session(db_path=log_db_path, session_id=session_id)
            created_at = existing["created_at"] if existing else now_iso
            log_service.upsert_session(
                db_path=log_db_path,
                session_id=session_id,
                title=_build_session_title(final_messages),
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in final_messages],
                created_at=created_at,
                updated_at=now_iso,
            )
