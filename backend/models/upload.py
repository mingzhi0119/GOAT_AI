"""Pydantic schemas for upload analysis endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field

class UploadAnalysisResponse(BaseModel):
    """JSON response for POST /api/upload/analyze."""

    filename: str
    document_id: str = Field(..., description="Indexed knowledge document identifier.")
    ingestion_id: str = Field(..., description="Knowledge ingestion identifier.")
    status: str = Field(..., description="Upload and ingestion lifecycle state.")
    retrieval_mode: str = Field(
        ...,
        description="Stable marker indicating the upload now routes through the RAG knowledge pipeline.",
    )
    chart: None = Field(
        default=None,
        description="Reserved for backward compatibility; charts are now created only during chat tool calls.",
    )
