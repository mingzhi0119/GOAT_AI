"""Chat service — orchestrates LLMClient + converts Pydantic models to goat_ai types."""
from __future__ import annotations

import io
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import requests

from backend.models.chat import ChatMessage
from backend.services import log_service
from goat_ai.chart_tool import GENERATE_CHART_SCHEMA, build_chart_spec_from_tool_arguments
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.latency_metrics import record_chat_inference_ms
from goat_ai.ollama_client import LLMClient, ToolCallPlan
from goat_ai.tools import messages_for_ollama
from goat_ai.types import ChatTurn

logger = logging.getLogger(__name__)

_DONE_SENTINEL = "[DONE]"
_CHART_INTENT_RE = re.compile(
    r"\b(chart|plot|graph|visuali[sz]e|visualization|trend|compare|comparison)\b",
    re.IGNORECASE,
)


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


_CHART_BLOCK_RE = re.compile(r":::chart\s*\n(\{.*?\})\s*\n:::", re.DOTALL)
_CSV_EMBED_RE = re.compile(r"CHART_DATA_CSV:\n```\n(.*?)\n```", re.DOTALL)


def _find_csv_in_messages(messages: list[ChatMessage]) -> "pd.DataFrame | None":
    """Search the conversation history for an embedded CHART_DATA_CSV block."""
    import pandas as pd  # local import — pandas only needed when a chart block is found

    for msg in messages:
        if msg.role != "user":
            continue
        m = _CSV_EMBED_RE.search(msg.content)
        if m:
            try:
                return pd.read_csv(io.StringIO(m.group(1)))
            except Exception:
                logger.warning("Failed to parse embedded CSV from file-context message")
    return None


def _strip_chart_block(text: str) -> str:
    """Remove the legacy :::chart block from assistant text when present."""
    return _CHART_BLOCK_RE.sub("", text).strip()


def _should_attempt_native_chart_tool(messages: list[ChatMessage]) -> bool:
    """True when the latest user turn looks like a visualization request."""
    last_user = _last_user_message(messages)
    return bool(last_user and _CHART_INTENT_RE.search(last_user))


def _prepare_native_chart_tool_followup(
    *,
    llm: LLMClient,
    model: str,
    messages: list[ChatMessage],
    turns: list[ChatTurn],
    system_prompt: str,
    ollama_options: dict[str, float | int] | None,
) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    """Plan a native chart tool call and return chart spec + follow-up messages."""
    if not _should_attempt_native_chart_tool(messages):
        return None

    df = _find_csv_in_messages(messages)
    if df is None:
        return None

    tool_plan: ToolCallPlan | None = llm.plan_tool_call(
        model,
        turns,
        system_prompt,
        tools=[GENERATE_CHART_SCHEMA],
        ollama_options=ollama_options,
    )
    if tool_plan is None or tool_plan.tool_name != "generate_chart":
        return None

    chart_spec = build_chart_spec_from_tool_arguments(df, tool_plan.arguments)
    if chart_spec is None:
        return None

    followup_messages: list[dict[str, object]] = [
        *messages_for_ollama(turns, system_prompt),
        tool_plan.assistant_message,
        {
            "role": "tool",
            "tool_name": tool_plan.tool_name,
            "content": json.dumps({"chart": chart_spec}, ensure_ascii=False),
        },
    ]
    return chart_spec, followup_messages


def _extract_chart_from_response(
    full_text: str,
    messages: list[ChatMessage],
) -> tuple[dict[str, object] | None, str]:
    """Find a :::chart JSON block in the LLM response and build a ChartSpec.

    Returns (chart_spec, clean_text) where clean_text has the block stripped.
    Returns (None, full_text) when no block is found or validation fails.
    """
    m = _CHART_BLOCK_RE.search(full_text)
    if not m:
        return None, full_text

    try:
        stub = json.loads(m.group(1))
    except json.JSONDecodeError:
        logger.warning("chart_service: :::chart block contained invalid JSON — skipping")
        return None, full_text

    x_key: str = stub.get("xKey", "")
    series: list[dict[str, str]] = stub.get("series", [])
    series_keys = [s.get("key", "") for s in series if isinstance(s, dict)]
    chart_type: str = stub.get("type", "line")
    title: str = stub.get("title", "")

    if not x_key or not series_keys:
        logger.warning("chart_service: :::chart block missing xKey or series — skipping")
        return None, full_text

    df = _find_csv_in_messages(messages)
    if df is None:
        logger.info("chart_service: no embedded CSV found in messages — skipping chart")
        return None, full_text

    from goat_ai.chart_tool import build_chart_spec_from_llm_selection

    chart = build_chart_spec_from_llm_selection(df, x_key, series_keys, chart_type, title)
    if chart is None:
        return None, full_text

    clean_text = (full_text[: m.start()].rstrip() + full_text[m.end() :]).strip()
    return chart, clean_text


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
    emitted_chart_spec: dict[str, object] | None = None
    native_tool_followup: list[dict[str, object]] | None = None

    native_chart_plan = _prepare_native_chart_tool_followup(
        llm=llm,
        model=model,
        messages=messages,
        turns=turns,
        system_prompt=effective_prompt,
        ollama_options=ollama_options,
    )
    if native_chart_plan is not None:
        emitted_chart_spec, native_tool_followup = native_chart_plan
        yield f'data: {json.dumps({"type": "chart_spec", "chart": emitted_chart_spec})}\n\n'

    try:
        if native_tool_followup is not None:
            token_stream = llm.stream_tool_followup(
                model,
                native_tool_followup,
                tools=[GENERATE_CHART_SCHEMA],
                ollama_options=ollama_options,
            )
        else:
            token_stream = llm.stream_tokens(
                model, turns, effective_prompt, ollama_options=ollama_options
            )

        for token in token_stream:
            buf.append(token)
            yield sse_event(token)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unavailable during chat stream: %s", exc)
        yield sse_event("[ERROR] AI service temporarily unavailable.")
    except Exception:
        logger.exception("Unexpected error during chat stream")
        yield sse_event("[ERROR] An unexpected error occurred.")
    finally:
        full_text = "".join(buf)
        if emitted_chart_spec is not None:
            chart_spec = emitted_chart_spec
            clean_text = _strip_chart_block(full_text)
        else:
            chart_spec, clean_text = _extract_chart_from_response(full_text, messages)
        if emitted_chart_spec is None and chart_spec is not None:
            yield f'data: {json.dumps({"type": "chart_spec", "chart": chart_spec})}\n\n'
        yield sse_event(_DONE_SENTINEL)
        elapsed_ms = round((time.monotonic() - t_start) * 1000)
        record_chat_inference_ms(float(elapsed_ms))
        log_service.log_conversation(
            db_path=log_db_path,
            ip=ip,
            model=model,
            turn_count=len(messages),
            user_message=_last_user_message(messages),
            assistant_response=clean_text,
            response_ms=elapsed_ms,
            user_name=user_name,
            session_id=session_id,
        )
        if session_id:
            final_messages = all_messages if all_messages is not None else messages
            assistant_content = clean_text
            stored_messages = list(final_messages) + [
                ChatMessage(role="assistant", content=assistant_content),
            ]
            now_iso = datetime.now(timezone.utc).isoformat()
            existing = log_service.get_session(db_path=log_db_path, session_id=session_id)
            created_at = existing["created_at"] if existing else now_iso
            title = _session_title_for_upsert(
                messages=final_messages,
                assistant_text=clean_text,
                session_id=session_id,
                log_db_path=log_db_path,
                ollama_base_url=ollama_base_url,
                generate_timeout=generate_timeout,
                model=model,
            )
            stored_dicts: list[dict[str, str]] = [
                {"role": m.role, "content": m.content} for m in stored_messages
            ]
            # Persist the last chart spec so the frontend can restore it when
            # loading this session from history (role "__chart__" is a sentinel;
            # it is filtered out before display and never sent to Ollama).
            if chart_spec is not None:
                stored_dicts.append(
                    {"role": "__chart__", "content": json.dumps(chart_spec, ensure_ascii=False)}
                )
            log_service.upsert_session(
                db_path=log_db_path,
                session_id=session_id,
                title=title,
                model=model,
                messages=stored_dicts,
                created_at=created_at,
                updated_at=now_iso,
            )
