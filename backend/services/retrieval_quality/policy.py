from __future__ import annotations

from typing import Literal

from goat_ai.config.settings import Settings


def resolve_rerank_mode(
    *, retrieval_profile: str, settings: Settings
) -> Literal["passthrough", "lexical"]:
    """Map client profile + env defaults to a rerank strategy."""
    p = retrieval_profile.strip().lower()
    if p in ("rag3_lexical", "rag3_quality"):
        return "lexical"
    if p == "default":
        return settings.rag_rerank_mode
    return "passthrough"


def resolve_query_rewrite_enabled(*, retrieval_profile: str) -> bool:
    """Query rewrite is opt-in via profile only (not env-always-on)."""
    return retrieval_profile.strip().lower() == "rag3_quality"
