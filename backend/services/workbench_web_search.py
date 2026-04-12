"""Public-web retrieval helpers for browse/deep-research workbench tasks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

from goat_ai.config.feature_gate_reasons import RUNTIME_DISABLED_BY_OPERATOR
from goat_ai.config.settings import Settings


class WorkbenchWebSearchError(RuntimeError):
    """Raised when the configured public-web provider cannot return results."""


@dataclass(frozen=True, kw_only=True)
class WorkbenchWebSearchHit:
    """One normalized public-web search result."""

    title: str
    url: str
    snippet: str
    rank: int


def get_workbench_web_runtime_status(settings: Settings) -> tuple[bool, str | None]:
    """Return whether the configured public-web source is runnable."""
    if settings.workbench_web_provider == "disabled":
        return False, RUNTIME_DISABLED_BY_OPERATOR
    return True, None


def build_workbench_web_description(settings: Settings) -> str:
    """Return the current operator-facing description for the public-web source."""
    if settings.workbench_web_provider == "disabled":
        return (
            "Public-web retrieval is disabled on this deployment. Enable "
            "GOAT_WORKBENCH_WEB_PROVIDER to allow browse and deep-research tasks "
            "to search the public web."
        )
    return (
        "Experimental public-web retrieval backed by the DDGS DuckDuckGo-style "
        "provider. "
        "Browse and deep-research currently run a single retrieval pass and return "
        "bounded evidence briefs with citations."
    )


def search_public_web(
    *,
    query: str,
    settings: Settings,
    max_results: int,
) -> list[WorkbenchWebSearchHit]:
    """Search the configured public-web provider and normalize the top hits."""
    runtime_ready, deny_reason = get_workbench_web_runtime_status(settings)
    if not runtime_ready:
        raise WorkbenchWebSearchError(
            f"Public web search is disabled ({deny_reason or 'disabled'})."
        )
    if settings.workbench_web_provider != "duckduckgo":
        raise WorkbenchWebSearchError(
            f"Unsupported workbench web provider: {settings.workbench_web_provider}"
        )
    bounded_results = min(max(1, max_results), settings.workbench_web_max_results)
    return _search_duckduckgo(
        query=query,
        max_results=bounded_results,
        settings=settings,
    )


def _search_duckduckgo(
    *,
    query: str,
    max_results: int,
    settings: Settings,
) -> list[WorkbenchWebSearchHit]:
    try:
        raw_results = DDGS(timeout=settings.workbench_web_timeout_sec).text(
            query,
            region=settings.workbench_web_region,
            safesearch=settings.workbench_web_safesearch,
            max_results=max_results,
        )
    except (DDGSException, RatelimitException, TimeoutException) as exc:
        raise WorkbenchWebSearchError("DuckDuckGo search failed.") from exc
    return _normalize_hits(raw_results, max_results=max_results)


def _normalize_hits(
    raw_results: Iterable[dict[str, object]],
    *,
    max_results: int,
) -> list[WorkbenchWebSearchHit]:
    normalized: list[WorkbenchWebSearchHit] = []
    seen_urls: set[str] = set()
    bounded_results = max(1, max_results)
    for item in raw_results:
        url = _clean_text(item.get("href"))
        if not url or url in seen_urls:
            continue
        title = _clean_text(item.get("title")) or _fallback_title(url)
        snippet = _clean_text(item.get("body"))
        if not snippet:
            continue
        seen_urls.add(url)
        normalized.append(
            WorkbenchWebSearchHit(
                title=title,
                url=url,
                snippet=snippet,
                rank=len(normalized) + 1,
            )
        )
        if len(normalized) >= bounded_results:
            break
    return normalized


def _clean_text(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    collapsed = " ".join(raw.split())
    return collapsed.strip()


def _fallback_title(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.strip()
    return host or url
