"""Native chat tool schema and helpers for public-web search."""

from __future__ import annotations

import json
import re
from typing import Any

from goat_ai.search.providers import (
    SearchSettings,
    WebSearchError,
    WebSearchHit,
    search_web,
)

WEB_SEARCH_TOOL_NAME = "web_search"

WEB_SEARCH_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": WEB_SEARCH_TOOL_NAME,
        "description": (
            "Search the public web for current or externally verifiable facts. "
            "Use this when the user explicitly asks to search, look up, check, "
            "verify, or get the latest/current information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The web search query to run.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of search results to return.",
                },
            },
            "required": ["query"],
        },
    },
}

_SEARCH_INTENT_RE = re.compile(
    r"(\b(search|look up|lookup|google|web search|check online|verify online|"
    r"latest|current|recent|today|news)\b|搜索|查询|查一下|查找|联网|上网查|"
    r"最新|最近|今天|新闻)",
    re.IGNORECASE,
)

_WEB_SEARCH_PROTOCOL = """\
WEB SEARCH PROTOCOL:
- If the user explicitly asks to search, look up, check online, verify online, \
or asks for latest/current/recent external facts, use the `web_search` tool \
before answering.
- Base factual claims from search on the returned results and cite source URLs.
- If search is unavailable or returns no useful evidence, say that clearly and \
do not invent citations."""


def should_attempt_web_search(user_text: str) -> bool:
    """Return whether the latest user turn explicitly requests public-web search."""
    return bool(_SEARCH_INTENT_RE.search(user_text))


def web_search_protocol(enabled: bool) -> str:
    """Return prompt text for the platform web-search protocol when enabled."""
    return _WEB_SEARCH_PROTOCOL if enabled else ""


def build_web_search_context(hits: list[WebSearchHit]) -> str:
    """Serialize search hits into compact prompt context."""
    payload = {
        "results": [
            {
                "rank": hit.rank,
                "title": hit.title,
                "url": hit.url,
                "snippet": hit.snippet,
            }
            for hit in hits
        ]
    }
    return json.dumps(payload, ensure_ascii=False)


def run_chat_web_search(
    *,
    query: str,
    max_results: int,
    settings: SearchSettings,
) -> list[WebSearchHit]:
    """Run bounded public-web search for the chat tool path."""
    return search_web(query=query, settings=settings, max_results=max_results)


def parse_web_search_tool_args(
    arguments: dict[str, Any], fallback_query: str
) -> tuple[str, int]:
    """Extract a bounded query and result limit from native tool arguments."""
    raw_query = arguments.get("query")
    query = raw_query.strip() if isinstance(raw_query, str) else ""
    raw_max_results = arguments.get("max_results")
    max_results = _coerce_max_results(raw_max_results) or 5
    return (query or fallback_query.strip(), max_results)


def tool_result_message(*, tool_name: str, content: str) -> dict[str, object]:
    """Build the generic tool-result message accepted by Ollama."""
    return {
        "role": "tool",
        "tool_name": tool_name,
        "content": content,
    }


def web_search_unavailable_message(exc: WebSearchError) -> str:
    """Return the user-facing fallback text for search provider failures."""
    _ = exc
    return (
        "Search is currently unavailable, so I cannot provide verified current "
        "web results for this request."
    )


def _coerce_max_results(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int) and raw > 0:
        return min(raw, 10)
    if isinstance(raw, float) and raw > 0:
        return min(int(raw), 10)
    return None
