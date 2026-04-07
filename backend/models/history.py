"""Pydantic schemas for chat history endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HistorySessionMessage(BaseModel):
    """Stored message row for persisted session history."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class HistorySessionFileContext(BaseModel):
    """Normalized stored file-context metadata for one session."""

    prompt: str


class HistorySessionSummary(BaseModel):
    """Lightweight session metadata for sidebar/history list views."""

    id: str
    title: str
    model: str
    created_at: str
    updated_at: str


class HistorySessionListResponse(BaseModel):
    """Body for GET /api/history."""

    sessions: list[HistorySessionSummary]


class HistorySessionDetailResponse(HistorySessionSummary):
    """Body for GET /api/history/{session_id}."""

    messages: list[HistorySessionMessage]
    chart_spec: dict[str, object] | None = None
    file_context: HistorySessionFileContext | None = None
    chart_data_source: str | None = Field(default=None, pattern="^(uploaded|demo|none)$")
