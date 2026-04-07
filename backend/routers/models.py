"""GET /api/models — return names of available Ollama models."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.models.common import ErrorResponse
from backend.dependencies import get_llm_client
from backend.models.chat import ModelsResponse
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available Ollama models",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def list_models(llm: LLMClient = Depends(get_llm_client)) -> ModelsResponse:
    """Return the list of locally available Ollama model names."""
    try:
        names = llm.list_model_names()
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable: %s", exc)
        raise HTTPException(status_code=503, detail="AI backend unavailable") from exc
    return ModelsResponse(models=names or ["llama3:latest"])
