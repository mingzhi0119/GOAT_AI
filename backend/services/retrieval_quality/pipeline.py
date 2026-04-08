from __future__ import annotations

from typing import Literal

from backend.services.knowledge_pipeline import KnowledgeSearchHit
from backend.services.retrieval_quality.query_rewrite import conservative_rewrite_query
from backend.services.retrieval_quality.rerank import LexicalOverlapReranker, PassthroughReranker


def prepare_search_query(*, original_query: str, rewrite_enabled: bool) -> str:
    """Return the query string used for embedding / lexical scoring."""
    if not rewrite_enabled:
        return original_query
    return conservative_rewrite_query(original_query)


def apply_rerank_hits(
    *,
    query: str,
    mode: Literal["passthrough", "lexical"],
    hits: list[KnowledgeSearchHit],
) -> list[KnowledgeSearchHit]:
    reranker = LexicalOverlapReranker() if mode == "lexical" else PassthroughReranker()
    return reranker.rerank(query=query, hits=hits)
