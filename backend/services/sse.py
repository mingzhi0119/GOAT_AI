"""Typed SSE event helpers shared across streaming endpoints."""

from __future__ import annotations

import json
from typing import Any


def sse_event(payload: dict[str, Any]) -> str:
    """Format a JSON payload as a Server-Sent Event frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_token_event(token: str) -> str:
    """Emit one token frame."""
    return sse_event({"type": "token", "token": token})


def sse_done_event() -> str:
    """Emit a terminal done frame."""
    return sse_event({"type": "done"})


def sse_error_event(message: str) -> str:
    """Emit a structured error frame."""
    return sse_event({"type": "error", "message": message})
