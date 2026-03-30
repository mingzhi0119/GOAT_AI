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


class ModelsResponse(BaseModel):
    """Body for GET /api/models."""

    models: list[str]
