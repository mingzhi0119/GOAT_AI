"""Pydantic schemas for the /api/chat endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in the conversation (mirrors goat_ai.types.ChatTurn)."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Body for POST /api/chat."""

    model: str = Field("llama3:latest", min_length=1)
    messages: list[ChatMessage] = Field(..., min_length=1)
    session_id: str | None = None
    system_instruction: str | None = Field(
        default=None,
        max_length=8000,
        description="Optional user instructions merged after the base system prompt.",
    )


class ModelsResponse(BaseModel):
    """Body for GET /api/models."""

    models: list[str]
