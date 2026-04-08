"""Capacity guardrails for chat request size (Phase 13.3)."""
from __future__ import annotations

import json

from backend.models.chat import ChatRequest
from backend.types import Settings


class ChatCapacityError(ValueError):
    """Raised when a chat request exceeds configured capacity guardrails."""


def _chat_payload_bytes(req: ChatRequest) -> int:
    payload = req.model_dump(mode="json")
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return len(encoded)


def validate_chat_capacity(*, req: ChatRequest, settings: Settings) -> None:
    """Validate request-level message count and payload size bounds."""
    message_count = len(req.messages)
    if message_count > settings.max_chat_messages:
        raise ChatCapacityError(
            f"Chat request exceeds max message count ({message_count} > {settings.max_chat_messages})."
        )

    payload_bytes = _chat_payload_bytes(req)
    if payload_bytes > settings.max_chat_payload_bytes:
        raise ChatCapacityError(
            f"Chat request exceeds max payload bytes ({payload_bytes} > {settings.max_chat_payload_bytes})."
        )
