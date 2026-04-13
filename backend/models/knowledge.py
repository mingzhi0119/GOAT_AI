from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeUploadResponse(BaseModel):
    """Contract skeleton for a persisted knowledge upload."""

    upload_id: str = Field(..., description="Opaque upload identifier.")
    document_id: str = Field(..., description="Logical knowledge document identifier.")
    status: Literal["uploaded"] = Field(..., description="Upload lifecycle state.")
    filename: str = Field(..., description="Original uploaded filename.")
    mime_type: str = Field(..., description="Declared upload MIME type.")
    byte_size: int = Field(..., ge=0, description="Raw uploaded file size in bytes.")


class KnowledgeIngestionRequest(BaseModel):
    """Contract-first request body for knowledge ingestion."""

    document_id: str = Field(
        ..., min_length=1, description="Document to ingest into the knowledge index."
    )
    parser_profile: str = Field(default="default", min_length=1)
    chunking_profile: str = Field(default="default", min_length=1)
    embedding_profile: str = Field(default="default", min_length=1)
    force_reindex: bool = Field(
        default=False, description="Rebuild index artifacts even if one already exists."
    )


class KnowledgeIngestionResponse(BaseModel):
    """Queued/running ingestion job response."""

    ingestion_id: str = Field(..., description="Opaque ingestion job identifier.")
    document_id: str = Field(
        ..., description="Document associated with this ingestion."
    )
    status: Literal["queued", "running", "completed", "failed"] = Field(
        ..., description="Current ingestion lifecycle state."
    )


class KnowledgeIngestionStatusResponse(BaseModel):
    """Lifecycle/status view for one ingestion attempt."""

    ingestion_id: str = Field(..., description="Opaque ingestion job identifier.")
    document_id: str = Field(
        ..., description="Document associated with this ingestion."
    )
    status: Literal["queued", "running", "completed", "failed"] = Field(...)
    chunk_count: int = Field(default=0, ge=0)
    error_code: str | None = Field(
        default=None,
        description="Stable machine-readable failure code when status=failed.",
    )
    error_detail: str | None = Field(
        default=None,
        description="Sanitized human-readable failure reason when status=failed.",
    )


class KnowledgeSearchRequest(BaseModel):
    """Pure retrieval request contract."""

    query: str = Field(..., min_length=1, description="Natural-language search query.")
    document_ids: list[str] = Field(
        default_factory=list, description="Optional search scope filter."
    )
    top_k: int = Field(
        default=5, ge=1, le=50, description="Maximum number of ranked hits to return."
    )
    retrieval_profile: str = Field(default="default", min_length=1)


class KnowledgeCitation(BaseModel):
    """Citation payload returned from knowledge retrieval."""

    document_id: str
    chunk_id: str
    filename: str
    snippet: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    """Pure retrieval response contract."""

    query: str
    hits: list[KnowledgeCitation] = Field(default_factory=list)
    effective_query: str | None = Field(
        default=None,
        description="When query rewrite is active, the normalized string used for retrieval.",
    )


class KnowledgeAnswerRequest(BaseModel):
    """Retrieval-backed answer request contract."""

    query: str = Field(..., min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=50)
    session_id: str | None = Field(
        default=None, description="Optional chat session correlation id."
    )


class KnowledgeAnswerResponse(BaseModel):
    """Retrieval-backed answer contract."""

    answer: str = Field(
        ...,
        description="Synthesized answer grounded in the retrieved knowledge context.",
    )
    citations: list[KnowledgeCitation] = Field(
        default_factory=list,
        description="Retrieved citations used as evidence for the synthesized answer.",
    )


class KnowledgeUploadStatusResponse(BaseModel):
    """Lookup response for one persisted knowledge upload."""

    upload_id: str
    document_id: str
    status: Literal["uploaded", "indexed", "failed"]
    filename: str
    mime_type: str
    byte_size: int = Field(..., ge=0)
