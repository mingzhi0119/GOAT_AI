"""Pydantic schemas for image attachment uploads (vision chat)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MediaUploadResponse(BaseModel):
    """Response for POST /api/media/uploads."""

    attachment_id: str = Field(..., min_length=1)
    filename: str
    mime_type: str
    byte_size: int
    width_px: int | None = None
    height_px: int | None = None
