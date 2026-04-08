"""GET /api/models — return names of available Ollama models."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_llm_client
from backend.models.chat import ModelCapabilitiesResponse, ModelsResponse
from backend.models.common import ErrorResponse
from backend.services.ollama_models_service import list_models_for_api, model_capabilities_for_api
from backend.types import LLMClient

router = APIRouter()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available Ollama models",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def list_models(llm: LLMClient = Depends(get_llm_client)) -> ModelsResponse:
    """Return the list of locally available Ollama model names."""
    return list_models_for_api(llm)


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
    return model_capabilities_for_api(llm, model)
