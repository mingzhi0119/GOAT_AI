"""Chat service — orchestrates LLMClient + converts Pydantic models to goat_ai types."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import requests

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


def _compose_system_prompt(base_prompt: str, user_name: str, system_instruction: str) -> str:
    """Merge base GOAT prompt, optional name, and optional user system instruction."""
    parts: list[str] = [base_prompt]
    if user_name.strip():
        parts.append(
            f"The student's name is {user_name.strip()}. Feel free to address them by name."
        )
    extra = system_instruction.strip()
    if extra:
        parts.append(
            "Additional instructions from the user (apply consistently):\n" + extra
        )
    return "\n\n".join(parts)


def _build_session_title_fallback(messages: list[ChatMessage]) -> str:
    """Fallback title from the last user message (no LLM).

    Uses the last user turn so that an injected file-context prompt at
    position 0 does not pollute the title.
    """
    for msg in reversed(messages):
        if msg.role == "user":
            text = msg.content.strip().replace("\n", " ")
            return (text[:80] + "…") if len(text) > 80 else text
    return "New Chat"


def _ollama_generate_session_title(
    ollama_base_url: str,
    timeout_sec: int,
    model: str,
    user_text: str,
    assistant_text: str,
) -> str | None:
    """Ask Ollama for a one-line summary title after the first Q&A; returns None on failure."""
    base = ollama_base_url.rstrip("/")
    prompt = (
        "Write ONE short line (maximum 12 words) summarizing this exchange for a chat sidebar title. "
        "Output only the title text, no quotes, no role labels.\n\n"
        f"User: {user_text[:4000]}\n\nAssistant: {assistant_text[:4000]}"
    )
    try:
        r = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=float(min(max(timeout_sec, 5), 90)),
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("response") or "").strip()
        one_line = " ".join(text.splitlines()).strip()
        if not one_line:
            return None
        return one_line[:120] if len(one_line) > 120 else one_line
    except Exception:
        logger.exception("Ollama session title generation failed")
        return None


def _session_title_for_upsert(
    *,
    messages: list[ChatMessage],
    assistant_text: str,
    session_id: str | None,
    log_db_path: Path,
    ollama_base_url: str,
    generate_timeout: int,
    model: str,
) -> str:
    """Sidebar title: generate once on the first exchange, keep it on all subsequent turns.

    Uses the *last* user message for the LLM title prompt so that an injected
    file-context prompt at position 0 is never used as the title source.
    The session is considered "already titled" if it already exists in the DB
    with a non-empty title, regardless of how many messages the history has.
    """
    existing = (
        log_service.get_session(db_path=log_db_path, session_id=session_id)
        if session_id
        else None
    )
    if existing and str(existing.get("title", "")).strip():
        return str(existing["title"])

    # First exchange for this session: generate a title using the real question.
    last_user = _last_user_message(messages)
    if last_user and assistant_text.strip() and ollama_base_url.strip():
        gen = _ollama_generate_session_title(
            ollama_base_url,
            generate_timeout,
            model,
            last_user,
            assistant_text,
        )
        if gen:
            return gen
    return _build_session_title_fallback(messages)


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
    ollama_base_url: str = "",
    generate_timeout: int = 120,
    system_instruction: str = "",
    ollama_options: dict[str, float | int] | None = None,
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat completion.

    Each event carries a JSON-encoded token string.
    The final event carries the sentinel "[DONE]".
    On Ollama errors the stream emits "[ERROR] <message>" then "[DONE]".
    After the stream completes the full conversation is appended to the log DB.
    """
    turns = _to_chat_turns(messages)
    effective_prompt = _compose_system_prompt(system_prompt, user_name, system_instruction)
    buf: list[str] = []
    t_start = time.monotonic()

    try:
        for token in llm.stream_tokens(
            model, turns, effective_prompt, ollama_options=ollama_options
        ):
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
            assistant_content = "".join(buf)
            stored_messages = list(final_messages) + [
                ChatMessage(role="assistant", content=assistant_content),
            ]
            now_iso = datetime.now(timezone.utc).isoformat()
            existing = log_service.get_session(db_path=log_db_path, session_id=session_id)
            created_at = existing["created_at"] if existing else now_iso
            title = _session_title_for_upsert(
                messages=final_messages,
                assistant_text=assistant_content,
                session_id=session_id,
                log_db_path=log_db_path,
                ollama_base_url=ollama_base_url,
                generate_timeout=generate_timeout,
                model=model,
            )
            log_service.upsert_session(
                db_path=log_db_path,
                session_id=session_id,
                title=title,
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in stored_messages],
                created_at=created_at,
                updated_at=now_iso,
            )
