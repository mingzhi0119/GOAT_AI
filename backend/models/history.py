"""Pydantic schemas for chat history endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.artifact import ChatArtifact


class HistorySessionMessage(BaseModel):
    """Stored message row for persisted session history."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    image_attachment_ids: list[str] = Field(
        default_factory=list,
        description="Vision image attachment ids stored for this user turn.",
    )
    artifacts: list[ChatArtifact] = Field(
        default_factory=list,
        description="Downloadable generated files associated with this assistant turn.",
    )


class HistorySessionFileContext(BaseModel):
    """Normalized stored file-context metadata for one session."""

    prompt: str


class HistorySessionKnowledgeDocument(BaseModel):
    """Indexed knowledge document attached to a chat session."""

    document_id: str
    filename: str
    mime_type: str


class HistorySessionSummary(BaseModel):
    """Lightweight session metadata for sidebar/history list views."""

    id: str
    title: str
    model: str
    schema_version: int = Field(..., ge=1)
    created_at: str
    updated_at: str
    owner_id: str = ""


class HistorySessionListResponse(BaseModel):
    """Body for GET /api/history."""

    sessions: list[HistorySessionSummary]


class HistorySessionDetailResponse(HistorySessionSummary):
    """Body for GET /api/history/{session_id}."""

    messages: list[HistorySessionMessage]
    chart_spec: dict[str, object] | None = None
    file_context: HistorySessionFileContext | None = None
    knowledge_documents: list[HistorySessionKnowledgeDocument] = Field(
        default_factory=list
    )
    chart_data_source: str | None = Field(
        default=None, pattern="^(uploaded|demo|none)$"
    )
