"""Pydantic schemas for upload analysis endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field

class UploadAnalysisResponse(BaseModel):
    """JSON response for POST /api/upload/analyze."""

    filename: str
    prompt: str = Field(..., description="Hidden analysis prompt derived from the uploaded table.")
    chart: None = Field(
        default=None,
        description="Reserved for backward compatibility; charts are now created only during chat tool calls.",
    )
