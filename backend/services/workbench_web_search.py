"""Public-web retrieval helpers for browse/deep-research workbench tasks."""

from __future__ import annotations

from goat_ai.config.settings import Settings
from goat_ai.search import (
    WebSearchError,
    WebSearchHit,
    build_web_search_description,
    get_web_search_runtime_status,
    search_web,
)

WorkbenchWebSearchError = WebSearchError
WorkbenchWebSearchHit = WebSearchHit


def get_workbench_web_runtime_status(settings: Settings) -> tuple[bool, str | None]:
    """Return whether the configured public-web source is runnable."""
    return get_web_search_runtime_status(settings)


def build_workbench_web_description(settings: Settings) -> str:
    """Return the current operator-facing description for the public-web source."""
    return build_web_search_description(settings)


def search_public_web(
    *,
    query: str,
    settings: Settings,
    max_results: int,
) -> list[WorkbenchWebSearchHit]:
    """Search the configured public-web provider and normalize the top hits."""
    return search_web(query=query, settings=settings, max_results=max_results)


def resolve_workbench_web_provider(
    hits: list[WorkbenchWebSearchHit],
    settings: Settings,
) -> str:
    """Return the actual provider used for a normalized search result set."""
    for hit in hits:
        if hit.provider:
            return hit.provider
    return settings.workbench_web_provider
