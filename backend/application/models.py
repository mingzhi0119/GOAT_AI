"""Model listing and capability use cases."""

from __future__ import annotations

from backend.application.ports import LLMClient, Settings
from backend.models.chat import ModelCapabilitiesResponse, ModelsResponse
from backend.services.ollama_models_service import (
    list_models_for_api,
    model_capabilities_for_api,
)


def list_models(llm: LLMClient, *, settings: Settings) -> ModelsResponse:
    return list_models_for_api(llm, settings=settings)


def get_model_capabilities(
    llm: LLMClient, model: str, *, settings: Settings
) -> ModelCapabilitiesResponse:
    return model_capabilities_for_api(llm, model, settings=settings)
