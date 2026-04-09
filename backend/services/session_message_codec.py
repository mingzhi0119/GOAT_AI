"""Helpers for persisted session payload encoding and legacy compatibility."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)


class SessionSchemaError(ValueError):
    """Raised when a session payload carries an unrecognized schema version.

    Callers that need strict version gating can catch this; the default
    ``decode_session_payload`` path logs a warning and continues decoding
    because older-versioned sessions are still structurally compatible.
    """

from backend.domain.chart_types import ChartDataSource
from backend.domain.invariants import chart_spec_requires_version_field
from backend.models.artifact import ChatArtifact
from backend.models.chat import ChatMessage
from goat_ai.tools import FILE_CONTEXT_UPLOAD_PREFIX, LEGACY_CSV_FENCE_SUBSTRING

STORED_CHART_ROLE = "__chart__"
STORED_FILE_CONTEXT_ROLE = "__file_context__"
STORED_FILE_CONTEXT_ACK_ROLE = "__file_context_ack__"
FILE_CONTEXT_REPLY = "I have loaded the file context."
SESSION_PAYLOAD_VERSION = 4

# Alternate upload-analysis header (legacy compatibility / future prompts).
FILE_CONTEXT_REQUESTED_PREFIX = "[User requested analysis of uploaded tabular data]"


@dataclass(frozen=True)
class DecodedSessionPayload:
    """Normalized session payload exposed above the storage layer."""

    messages: list[dict[str, Any]]
    chart_spec: dict[str, object] | None
    file_context_prompt: str | None
    knowledge_documents: list[dict[str, str]]
    chart_data_source: ChartDataSource = "none"


def is_file_context_message(message: ChatMessage) -> bool:
    """Return whether this message should be stored as file context (explicit flag or legacy sniff)."""
    if message.role != "user":
        return False
    if message.file_context:
        return bool(message.content.strip())
    return _legacy_sniff_file_context_content(message.content)


def _legacy_sniff_file_context_content(content: str) -> bool:
    """Detect legacy upload prompts that relied on embedded CSV markers (no API flag)."""
    return LEGACY_CSV_FENCE_SUBSTRING in content and (
        content.startswith(FILE_CONTEXT_UPLOAD_PREFIX)
        or content.startswith(FILE_CONTEXT_REQUESTED_PREFIX)
    )


def _normalize_message_dict(message: object) -> dict[str, Any] | None:
    """Normalize a raw storage row into a standard chat message."""
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    content = message.get("content")
    if role not in {"user", "assistant", "system"} or not isinstance(content, str):
        return None
    out: dict[str, Any] = {"role": str(role), "content": content}
    raw_ids = message.get("image_attachment_ids")
    if isinstance(raw_ids, list) and raw_ids:
        ids: list[str] = []
        for item in raw_ids:
            if isinstance(item, str) and item.strip():
                ids.append(item.strip())
        if ids:
            out["image_attachment_ids"] = ids
    raw_artifacts = message.get("artifacts")
    if isinstance(raw_artifacts, list) and raw_artifacts:
        artifacts: list[dict[str, object]] = []
        for item in raw_artifacts:
            if not isinstance(item, dict):
                continue
            try:
                artifacts.append(
                    ChatArtifact.model_validate(item).model_dump(mode="json")
                )
            except Exception:
                continue
        if artifacts:
            out["artifacts"] = artifacts
    return out


def build_session_payload(
    *,
    messages: list[ChatMessage],
    assistant_text: str,
    chart_spec: dict[str, object] | None,
    knowledge_documents: list[dict[str, str]] | None = None,
    assistant_artifacts: list[dict[str, object]] | None = None,
    chart_data_source: ChartDataSource = "none",
) -> dict[str, object]:
    """Build the versioned storage payload for new session snapshots."""
    visible_messages: list[dict[str, object]] = []
    file_context_prompt: str | None = None

    for message in [*messages, ChatMessage(role="assistant", content=assistant_text)]:
        if is_file_context_message(message):
            file_context_prompt = message.content
            continue
        if message.role == "assistant" and message.content == FILE_CONTEXT_REPLY:
            continue
        row: dict[str, object] = {"role": message.role, "content": message.content}
        if message.image_attachment_ids:
            row["image_attachment_ids"] = list(message.image_attachment_ids)
        if (
            message.role == "assistant"
            and message.content == assistant_text
            and assistant_artifacts
        ):
            row["artifacts"] = assistant_artifacts
        visible_messages.append(row)

    payload: dict[str, object] = {
        "version": SESSION_PAYLOAD_VERSION,
        "messages": visible_messages,
        "chart_data_source": chart_data_source,
    }
    if chart_spec is not None:
        chart_spec_requires_version_field(chart_spec)
        payload["chart_spec"] = chart_spec
    if file_context_prompt is not None:
        payload["file_context_prompt"] = file_context_prompt
    if knowledge_documents:
        payload["knowledge_documents"] = knowledge_documents
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
        knowledge_documents=[],
        chart_data_source="uploaded" if file_context_prompt else "none",
    )


def decode_session_payload(raw_payload: Any) -> DecodedSessionPayload:
    """Decode either the new versioned payload or the legacy list payload."""
    if isinstance(raw_payload, list):
        return _decode_legacy_session_payload(raw_payload)

    if isinstance(raw_payload, dict):
        raw_version = raw_payload.get("version")
        if isinstance(raw_version, int) and raw_version > SESSION_PAYLOAD_VERSION:
            _log.warning(
                "session_payload_version_unknown",
                extra={
                    "stored_version": raw_version,
                    "supported_version": SESSION_PAYLOAD_VERSION,
                },
            )
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
        file_context_prompt = (
            raw_file_context if isinstance(raw_file_context, str) else None
        )
        raw_knowledge_documents = raw_payload.get("knowledge_documents", [])
        knowledge_documents: list[dict[str, str]] = []
        if isinstance(raw_knowledge_documents, list):
            for item in raw_knowledge_documents:
                if not isinstance(item, dict):
                    continue
                document_id = item.get("document_id")
                filename = item.get("filename")
                mime_type = item.get("mime_type")
                if (
                    isinstance(document_id, str)
                    and document_id.strip()
                    and isinstance(filename, str)
                    and filename.strip()
                    and isinstance(mime_type, str)
                    and mime_type.strip()
                ):
                    knowledge_documents.append(
                        {
                            "document_id": document_id,
                            "filename": filename,
                            "mime_type": mime_type,
                        }
                    )
        raw_source = raw_payload.get("chart_data_source")
        chart_data_source: ChartDataSource = (
            raw_source
            if isinstance(raw_source, str)
            and raw_source in {"uploaded", "demo", "none"}
            else ("uploaded" if file_context_prompt else "none")
        )
        return DecodedSessionPayload(
            messages=messages,
            chart_spec=chart_spec,
            file_context_prompt=file_context_prompt,
            knowledge_documents=knowledge_documents,
            chart_data_source=chart_data_source,
        )

    return DecodedSessionPayload(
        messages=[],
        chart_spec=None,
        file_context_prompt=None,
        knowledge_documents=[],
        chart_data_source="none",
    )
