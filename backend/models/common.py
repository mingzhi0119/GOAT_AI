"""Shared API schema components."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard JSON error envelope (Phase 13 §13.0)."""

    detail: str | list[Any] | dict[str, Any] = Field(
        ...,
        description="Human-readable message or structured validation errors.",
    )
    code: str = Field(..., description="Stable machine-readable error code.")
    request_id: str | None = Field(
        default=None,
        description="Echo of X-Request-ID when the server generated or accepted one.",
    )
