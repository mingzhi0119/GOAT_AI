"""Public model allowlist helpers for HTTP-facing model selection."""

from __future__ import annotations

from goat_ai.llm.public_model_policy import (
    filter_public_model_names,
    public_model_allowlist_text,
    resolve_public_model_name,
)

from backend.services.exceptions import ModelNotAllowed


def require_public_model_name(model: str) -> str:
    resolved = resolve_public_model_name(model)
    if resolved is not None:
        return resolved
    raise ModelNotAllowed(
        "Selected model is not enabled on this deployment. "
        f"Allowed models: {public_model_allowlist_text()}."
    )


__all__ = ["filter_public_model_names", "require_public_model_name"]
