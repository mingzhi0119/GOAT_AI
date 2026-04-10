"""Ollama model listing and capability queries for HTTP APIs."""

from __future__ import annotations

import logging

from goat_ai.exceptions import OllamaUnavailable

from backend.models.chat import ModelCapabilitiesResponse, ModelsResponse
from backend.services.exceptions import InferenceBackendUnavailable
from backend.types import LLMClient

logger = logging.getLogger(__name__)


def list_models_for_api(llm: LLMClient) -> ModelsResponse:
    """Return installed model names, or raise ``InferenceBackendUnavailable`` if Ollama is down."""
    try:
        names = llm.list_model_names()
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable: %s", exc)
        raise InferenceBackendUnavailable from exc
    return ModelsResponse(models=names or ["gemma4:26b"])


def model_capabilities_for_api(llm: LLMClient, model: str) -> ModelCapabilitiesResponse:
    """Return Ollama-reported capabilities for one model."""
    try:
        capabilities, context_length = llm.describe_model_for_api(model)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable during model capability lookup: %s", exc)
        raise InferenceBackendUnavailable from exc
    supports_tool_calling = "tools" in capabilities
    supports_vision = "vision" in capabilities
    supports_thinking = "thinking" in capabilities
    return ModelCapabilitiesResponse(
        model=model,
        capabilities=capabilities,
        supports_tool_calling=supports_tool_calling,
        supports_chart_tools=supports_tool_calling,
        supports_vision=supports_vision,
        supports_thinking=supports_thinking,
        context_length=context_length,
    )
