"""Helpers for encoding persisted session-only message rows."""
from __future__ import annotations

from backend.models.chat import ChatMessage

STORED_CHART_ROLE = "__chart__"
STORED_FILE_CONTEXT_ROLE = "__file_context__"
STORED_FILE_CONTEXT_ACK_ROLE = "__file_context_ack__"
FILE_CONTEXT_REPLY = "I have loaded the file context."


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


def encode_session_message(message: ChatMessage) -> dict[str, str]:
    """Convert a runtime chat message into the persisted session representation."""
    if is_file_context_message(message):
        return {"role": STORED_FILE_CONTEXT_ROLE, "content": message.content}
    if message.role == "assistant" and message.content == FILE_CONTEXT_REPLY:
        return {"role": STORED_FILE_CONTEXT_ACK_ROLE, "content": message.content}
    return {"role": message.role, "content": message.content}
