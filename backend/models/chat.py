"""Pydantic schemas for the /api/chat endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in the conversation (mirrors goat_ai.types.ChatTurn)."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    file_context: bool = Field(
        default=False,
        description="True when this user message is upload-derived tabular file context.",
    )
    image_attachment_ids: list[str] = Field(
        default_factory=list,
        description="Optional image attachment ids (vision) associated with this user turn.",
    )


class ChatRequest(BaseModel):
    """Body for POST /api/chat."""

    model: str = Field("gemma4:26b", min_length=1)
    messages: list[ChatMessage] = Field(..., min_length=1)
    knowledge_document_ids: list[str] = Field(
        default_factory=list,
        description="Optional indexed knowledge documents to use for retrieval-augmented answering.",
    )
    image_attachment_ids: list[str] = Field(
        default_factory=list,
        description="Optional uploaded image attachments for the current turn (last user message).",
    )
    session_id: str | None = None
    system_instruction: str | None = Field(
        default=None,
        max_length=8000,
        description="Optional user instructions merged after the base system prompt.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Ollama sampling temperature (optional).",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=131072,
        description="Max tokens to generate (Ollama num_predict).",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Ollama top_p nucleus sampling.",
    )


class ModelsResponse(BaseModel):
    """Body for GET /api/models."""

    models: list[str]


class ModelCapabilitiesResponse(BaseModel):
    """Capabilities for one Ollama model."""

    model: str
    capabilities: list[str]
    supports_tool_calling: bool
    supports_chart_tools: bool
    supports_vision: bool
