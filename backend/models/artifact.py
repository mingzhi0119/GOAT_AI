"""Pydantic schemas for generated chat artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatArtifact(BaseModel):
    """One downloadable file generated during chat."""

    artifact_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    mime_type: str = Field(..., min_length=1)
    byte_size: int = Field(..., ge=0)
    download_url: str = Field(..., min_length=1)
    label: str | None = None
    source_message_id: str | None = None
