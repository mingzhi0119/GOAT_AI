"""Merge wire-level chat fields into message rows for persistence and streaming."""

from __future__ import annotations

from backend.models.chat import ChatMessage, ChatRequest


def merge_request_image_attachments(req: ChatRequest) -> list[ChatMessage]:
    """Attach ``ChatRequest.image_attachment_ids`` to the last user message for storage."""
    if not req.image_attachment_ids:
        return req.messages
    msgs = list(req.messages)
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].role == "user":
            merged_ids = list(req.image_attachment_ids)
            if msgs[i].image_attachment_ids:
                merged_ids = list(
                    dict.fromkeys([*msgs[i].image_attachment_ids, *merged_ids]),
                )
            msgs[i] = ChatMessage(
                role=msgs[i].role,
                content=msgs[i].content,
                file_context=msgs[i].file_context,
                image_attachment_ids=merged_ids,
            )
            break
    return msgs
