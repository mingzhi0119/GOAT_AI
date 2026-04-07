"""Helpers for persisted session payload encoding and legacy compatibility."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from backend.models.chat import ChatMessage

STORED_CHART_ROLE = "__chart__"
STORED_FILE_CONTEXT_ROLE = "__file_context__"
STORED_FILE_CONTEXT_ACK_ROLE = "__file_context_ack__"
FILE_CONTEXT_REPLY = "I have loaded the file context."
SESSION_PAYLOAD_VERSION = 2
ChartDataSource = Literal["uploaded", "demo", "none"]


@dataclass(frozen=True)
class DecodedSessionPayload:
    """Normalized session payload exposed above the storage layer."""

    messages: list[dict[str, str]]
    chart_spec: dict[str, object] | None
    file_context_prompt: str | None
    chart_data_source: ChartDataSource = "none"


def is_file_context_message(message: ChatMessage) -> bool:
    """Return whether a chat message is the injected file-context prompt."""
    return (
        message.role == "user"
        and "CHART_DATA_CSV:\n```" in message.content
        and (
            message.content.startswith("[User uploaded tabular data for analysis]")
            or message.content.startswith("[User requested analysis of uploaded tabular data]")
        )
    )


def _normalize_message_dict(message: object) -> dict[str, str] | None:
    """Normalize a raw storage row into a standard chat message."""
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    content = message.get("content")
    if role not in {"user", "assistant", "system"} or not isinstance(content, str):
        return None
    return {"role": str(role), "content": content}


def build_session_payload(
    *,
    messages: list[ChatMessage],
    assistant_text: str,
    chart_spec: dict[str, object] | None,
    chart_data_source: ChartDataSource = "none",
) -> dict[str, object]:
    """Build the versioned storage payload for new session snapshots."""
    visible_messages: list[dict[str, str]] = []
    file_context_prompt: str | None = None

    for message in [*messages, ChatMessage(role="assistant", content=assistant_text)]:
        if is_file_context_message(message):
            file_context_prompt = message.content
            continue
        if message.role == "assistant" and message.content == FILE_CONTEXT_REPLY:
            continue
        visible_messages.append({"role": message.role, "content": message.content})

    payload: dict[str, object] = {
        "version": SESSION_PAYLOAD_VERSION,
        "messages": visible_messages,
        "chart_data_source": chart_data_source,
    }
    if chart_spec is not None:
        payload["chart_spec"] = chart_spec
    if file_context_prompt is not None:
        payload["file_context_prompt"] = file_context_prompt
    return payload


def _decode_legacy_session_payload(raw_payload: list[object]) -> DecodedSessionPayload:
    """Decode the legacy role-tagged list payload format."""
    messages: list[dict[str, str]] = []
    chart_spec: dict[str, object] | None = None
    file_context_prompt: str | None = None

    for item in raw_payload:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        if role == STORED_FILE_CONTEXT_ROLE:
            file_context_prompt = content
            continue
        if role == STORED_FILE_CONTEXT_ACK_ROLE:
            continue
        if role == STORED_CHART_ROLE:
            try:
                decoded = json.loads(content)
                chart_spec = decoded if isinstance(decoded, dict) else None
            except Exception:
                chart_spec = None
            continue
        normalized = _normalize_message_dict(item)
        if normalized is not None:
            messages.append(normalized)

    return DecodedSessionPayload(
        messages=messages,
        chart_spec=chart_spec,
        file_context_prompt=file_context_prompt,
        chart_data_source="uploaded" if file_context_prompt else "none",
    )


def decode_session_payload(raw_payload: Any) -> DecodedSessionPayload:
    """Decode either the new versioned payload or the legacy list payload."""
    if isinstance(raw_payload, list):
        return _decode_legacy_session_payload(raw_payload)

    if isinstance(raw_payload, dict):
        raw_messages = raw_payload.get("messages", [])
        messages: list[dict[str, str]] = []
        if isinstance(raw_messages, list):
            for message in raw_messages:
                normalized = _normalize_message_dict(message)
                if normalized is not None:
                    messages.append(normalized)
        raw_chart = raw_payload.get("chart_spec")
        chart_spec = raw_chart if isinstance(raw_chart, dict) else None
        raw_file_context = raw_payload.get("file_context_prompt")
        file_context_prompt = raw_file_context if isinstance(raw_file_context, str) else None
        raw_source = raw_payload.get("chart_data_source")
        chart_data_source: ChartDataSource = (
            raw_source
            if isinstance(raw_source, str) and raw_source in {"uploaded", "demo", "none"}
            else ("uploaded" if file_context_prompt else "none")
        )
        return DecodedSessionPayload(
            messages=messages,
            chart_spec=chart_spec,
            file_context_prompt=file_context_prompt,
            chart_data_source=chart_data_source,
        )

    return DecodedSessionPayload(messages=[], chart_spec=None, file_context_prompt=None, chart_data_source="none")
