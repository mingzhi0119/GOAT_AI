"""Public model allowlist helpers for HTTP-facing model selection."""

from __future__ import annotations

from goat_ai.llm.public_model_policy import (
    filter_public_model_names,
    public_model_allowlist_text,
    resolve_public_model_name,
)

from backend.services.exceptions import ModelNotAllowed
from backend.types import Settings


def filter_model_names_for_deployment(
    names: list[str], *, settings: Settings
) -> list[str]:
    if not settings.is_remote_deploy:
        return names
    return filter_public_model_names(names)


def require_model_name_for_deployment(model: str, *, settings: Settings) -> str:
    if not settings.is_remote_deploy:
        return model
    resolved = resolve_public_model_name(model)
    if resolved is not None:
        return resolved
    raise ModelNotAllowed(
        "Selected model is not enabled on this deployment. "
        f"Allowed models: {public_model_allowlist_text()}."
    )


__all__ = [
    "filter_model_names_for_deployment",
    "require_model_name_for_deployment",
]
