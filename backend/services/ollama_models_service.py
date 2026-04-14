"""Ollama model listing and capability queries for HTTP APIs."""

from __future__ import annotations

import logging

from goat_ai.shared.exceptions import OllamaUnavailable

from backend.models.chat import ModelCapabilitiesResponse, ModelsResponse
from backend.services.exceptions import InferenceBackendUnavailable
from backend.services.public_model_policy import (
    filter_model_names_for_deployment,
    require_model_name_for_deployment,
)
from backend.types import LLMClient, Settings

logger = logging.getLogger(__name__)


def list_models_for_api(llm: LLMClient, *, settings: Settings) -> ModelsResponse:
    """Return installed model names, or raise ``InferenceBackendUnavailable`` if Ollama is down."""
    try:
        names = llm.list_model_names()
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable: %s", exc)
        raise InferenceBackendUnavailable from exc
    return ModelsResponse(
        models=filter_model_names_for_deployment(names, settings=settings)
    )


def model_capabilities_for_api(
    llm: LLMClient, model: str, *, settings: Settings
) -> ModelCapabilitiesResponse:
    """Return Ollama-reported capabilities for one model."""
    resolved_model = require_model_name_for_deployment(model, settings=settings)
    try:
        capabilities, context_length = llm.describe_model_for_api(resolved_model)
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable during model capability lookup: %s", exc)
        raise InferenceBackendUnavailable from exc
    supports_tool_calling = "tools" in capabilities
    supports_vision = "vision" in capabilities
    supports_thinking = "thinking" in capabilities
    return ModelCapabilitiesResponse(
        model=resolved_model,
        capabilities=capabilities,
        supports_tool_calling=supports_tool_calling,
        supports_chart_tools=supports_tool_calling,
        supports_vision=supports_vision,
        supports_thinking=supports_thinking,
        context_length=context_length,
    )
