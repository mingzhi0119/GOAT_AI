"""Pydantic schemas for chat history endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HistorySessionMessage(BaseModel):
    """Stored message row for persisted session history."""

    role: str = Field(
        ...,
        pattern="^(user|assistant|system|__chart__|__file_context__|__file_context_ack__)$",
    )
    content: str


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
