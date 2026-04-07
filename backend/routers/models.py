"""GET /api/models — return names of available Ollama models."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.models.common import ErrorResponse
from backend.dependencies import get_llm_client
from backend.models.chat import ModelCapabilitiesResponse, ModelsResponse
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
    return ModelsResponse(models=names or ["gemma4:26b"])


@router.get(
    "/models/capabilities",
    response_model=ModelCapabilitiesResponse,
    summary="Read capabilities for one Ollama model",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def get_model_capabilities(
    model: str,
    llm: LLMClient = Depends(get_llm_client),
) -> ModelCapabilitiesResponse:
    """Return Ollama-reported capabilities for the selected model."""
    try:
        capabilities = llm.get_model_capabilities(model)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable during model capability lookup: %s", exc)
        raise HTTPException(status_code=503, detail="AI backend unavailable") from exc

    supports_tool_calling = "tools" in capabilities
    return ModelCapabilitiesResponse(
        model=model,
        capabilities=capabilities,
        supports_tool_calling=supports_tool_calling,
        supports_chart_tools=supports_tool_calling,
    )
