"""Public-web search providers used by chat and Workbench retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import requests
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

from goat_ai.config.feature_gate_reasons import RUNTIME_DISABLED_BY_OPERATOR

SERPER_SEARCH_URL = "https://google.serper.dev/search"


class SearchSettings(Protocol):
    workbench_web_provider: str
    workbench_web_max_results: int
    workbench_web_timeout_sec: int
    workbench_web_region: str
    workbench_web_safesearch: str
    serper_api_key: str
    serper_gl: str
    serper_hl: str


class WebSearchError(RuntimeError):
    """Raised when the configured public-web provider cannot return results."""


@dataclass(frozen=True, kw_only=True)
class WebSearchHit:
    """One normalized public-web search result."""

    title: str
    url: str
    snippet: str
    rank: int
    provider: str = ""


def get_web_search_runtime_status(settings: SearchSettings) -> tuple[bool, str | None]:
    """Return whether the configured public-web source is runnable."""
    provider = settings.workbench_web_provider
    if provider == "disabled":
        return False, RUNTIME_DISABLED_BY_OPERATOR
    return True, None


def build_web_search_description(settings: SearchSettings) -> str:
    """Return the current operator-facing description for the public-web source."""
    provider = settings.workbench_web_provider
    if provider == "disabled":
        return (
            "Public-web retrieval is disabled on this deployment. Enable "
            "GOAT_WORKBENCH_WEB_PROVIDER to allow browse and deep-research tasks "
            "to search the public web."
        )
    if provider == "serper":
        return (
            "Public-web retrieval defaults to Serper.dev Google Search results "
            "with automatic DuckDuckGo fallback when Serper is unavailable. "
            "Browse, deep-research, and chat search requests return bounded "
            "evidence briefs with citations."
        )
    if provider == "duckduckgo":
        return (
            "Experimental public-web retrieval backed by the DDGS "
            "DuckDuckGo-style provider. Browse and deep-research currently run "
            "bounded retrieval and return evidence briefs with citations."
        )
    return f"Unsupported public-web retrieval provider: {provider}."


def search_web(
    *,
    query: str,
    settings: SearchSettings,
    max_results: int,
) -> list[WebSearchHit]:
    """Search the configured public-web provider and normalize the top hits."""
    runtime_ready, deny_reason = get_web_search_runtime_status(settings)
    if not runtime_ready:
        raise WebSearchError(
            f"Public web search is disabled ({deny_reason or 'disabled'})."
        )

    bounded_results = min(max(1, max_results), settings.workbench_web_max_results)
    provider = settings.workbench_web_provider
    if provider == "serper":
        try:
            return _search_serper(
                query=query,
                max_results=bounded_results,
                settings=settings,
            )
        except WebSearchError as serper_exc:
            try:
                return _search_duckduckgo(
                    query=query,
                    max_results=bounded_results,
                    settings=settings,
                )
            except WebSearchError as duckduckgo_exc:
                raise WebSearchError(
                    "Serper search unavailable "
                    f"({serper_exc}); DuckDuckGo fallback failed "
                    f"({duckduckgo_exc})."
                ) from duckduckgo_exc
    if provider == "duckduckgo":
        return _search_duckduckgo(
            query=query,
            max_results=bounded_results,
            settings=settings,
        )
    raise WebSearchError(f"Unsupported workbench web provider: {provider}")


def _search_serper(
    *,
    query: str,
    max_results: int,
    settings: SearchSettings,
) -> list[WebSearchHit]:
    api_key = settings.serper_api_key.strip()
    if not api_key:
        raise WebSearchError("Serper API key is not configured.")

    payload: dict[str, object] = {
        "q": query,
        "num": max_results,
    }
    if settings.serper_gl.strip():
        payload["gl"] = settings.serper_gl.strip().lower()
    if settings.serper_hl.strip():
        payload["hl"] = settings.serper_hl.strip().lower()

    try:
        response = requests.post(
            SERPER_SEARCH_URL,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.workbench_web_timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as exc:
        raise WebSearchError("Serper search timed out.") from exc
    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code if exc.response is not None else "unknown"
        )
        if status_code == 429:
            raise WebSearchError("Serper search rate limit exceeded.") from exc
        raise WebSearchError(f"Serper search failed with HTTP {status_code}.") from exc
    except requests.RequestException as exc:
        raise WebSearchError("Serper search request failed.") from exc
    except ValueError as exc:
        raise WebSearchError("Serper search returned malformed JSON.") from exc

    if not isinstance(data, dict):
        raise WebSearchError("Serper search returned malformed JSON.")
    raw_results = data.get("organic")
    if raw_results is None:
        return []
    if not isinstance(raw_results, list):
        raise WebSearchError("Serper search returned malformed response.")
    return _normalize_serper_hits(raw_results, max_results=max_results)


def _search_duckduckgo(
    *,
    query: str,
    max_results: int,
    settings: SearchSettings,
) -> list[WebSearchHit]:
    try:
        raw_results = DDGS(timeout=settings.workbench_web_timeout_sec).text(
            query,
            region=settings.workbench_web_region,
            safesearch=settings.workbench_web_safesearch,
            max_results=max_results,
        )
    except (DDGSException, RatelimitException, TimeoutException) as exc:
        raise WebSearchError("DuckDuckGo search failed.") from exc
    return _normalize_duckduckgo_hits(raw_results, max_results=max_results)


def _normalize_serper_hits(
    raw_results: Iterable[dict[str, Any]],
    *,
    max_results: int,
) -> list[WebSearchHit]:
    return _normalize_hits(
        raw_results,
        max_results=max_results,
        url_key="link",
        snippet_key="snippet",
        rank_key="position",
        provider="serper",
    )


def _normalize_duckduckgo_hits(
    raw_results: Iterable[dict[str, object]],
    *,
    max_results: int,
) -> list[WebSearchHit]:
    return _normalize_hits(
        raw_results,
        max_results=max_results,
        url_key="href",
        snippet_key="body",
        rank_key=None,
        provider="duckduckgo",
    )


def _normalize_hits(
    raw_results: Iterable[dict[str, object]],
    *,
    max_results: int,
    url_key: str,
    snippet_key: str,
    rank_key: str | None,
    provider: str,
) -> list[WebSearchHit]:
    normalized: list[WebSearchHit] = []
    seen_urls: set[str] = set()
    bounded_results = max(1, max_results)
    for item in raw_results:
        url = _clean_text(item.get(url_key))
        if not url or url in seen_urls:
            continue
        title = _clean_text(item.get("title")) or _fallback_title(url)
        snippet = _clean_text(item.get(snippet_key))
        if not snippet:
            continue
        rank = _coerce_rank(item.get(rank_key)) if rank_key is not None else None
        seen_urls.add(url)
        normalized.append(
            WebSearchHit(
                title=title,
                url=url,
                snippet=snippet,
                rank=rank or len(normalized) + 1,
                provider=provider,
            )
        )
        if len(normalized) >= bounded_results:
            break
    return normalized


def _coerce_rank(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int) and raw > 0:
        return raw
    if isinstance(raw, float) and raw > 0:
        return int(raw)
    return None


def _clean_text(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    collapsed = " ".join(raw.split())
    return collapsed.strip()


def _fallback_title(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.strip()
    return host or url
