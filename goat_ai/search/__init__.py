"""Shared public-web search provider helpers."""

from goat_ai.search.providers import (
    WebSearchError,
    WebSearchHit,
    build_web_search_description,
    get_web_search_runtime_status,
    search_web,
)
from goat_ai.search.tool import WEB_SEARCH_TOOL_NAME, WEB_SEARCH_TOOL_SCHEMA

__all__ = [
    "WebSearchError",
    "WebSearchHit",
    "build_web_search_description",
    "get_web_search_runtime_status",
    "search_web",
    "WEB_SEARCH_TOOL_NAME",
    "WEB_SEARCH_TOOL_SCHEMA",
]
