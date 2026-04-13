from __future__ import annotations

import os
from typing import Final

_PUBLIC_MODEL_ALLOWLIST_ENV: Final = "GOAT_PUBLIC_MODEL_ALLOWLIST"
_DEFAULT_PUBLIC_MODEL_ALLOWLIST: Final[tuple[str, ...]] = (
    "qwen3:4b",
    "llama3.2:3b",
    "gemma3:4b",
    "qwen2.5-coder:3b",
    "gemma4:26b",
)


def normalize_public_model_name(model: str) -> str:
    return model.strip().lower()


def public_model_allowlist() -> tuple[str, ...]:
    raw = os.environ.get(_PUBLIC_MODEL_ALLOWLIST_ENV, "").strip()
    if not raw:
        return _DEFAULT_PUBLIC_MODEL_ALLOWLIST

    ordered: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        normalized = normalize_public_model_name(item)
        if not normalized or normalized in seen:
            continue
        ordered.append(normalized)
        seen.add(normalized)
    return tuple(ordered) or _DEFAULT_PUBLIC_MODEL_ALLOWLIST


def resolve_public_model_name(model: str) -> str | None:
    normalized = normalize_public_model_name(model)
    if not normalized:
        return None

    allowed_by_normalized = {
        normalize_public_model_name(item): item for item in public_model_allowlist()
    }
    return allowed_by_normalized.get(normalized)


def public_model_allowlist_text() -> str:
    return ", ".join(public_model_allowlist())


def filter_public_model_names(names: list[str]) -> list[str]:
    installed = {normalize_public_model_name(name) for name in names}
    filtered: list[str] = []
    for allowed in public_model_allowlist():
        if normalize_public_model_name(allowed) in installed:
            filtered.append(allowed)
    return filtered
