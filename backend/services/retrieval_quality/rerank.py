from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.knowledge_pipeline import KnowledgeSearchHit

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class PassthroughReranker:
    """Preserves vector ordering (score-preserving passthrough)."""

    def rerank(self, *, query: str, hits: list[KnowledgeSearchHit]) -> list[KnowledgeSearchHit]:
        _ = query
        return list(hits)


@dataclass(frozen=True)
class LexicalOverlapReranker:
    """Lightweight lexical overlap re-ordering over the vector candidate pool."""

    def rerank(self, *, query: str, hits: list[KnowledgeSearchHit]) -> list[KnowledgeSearchHit]:
        return lexical_rerank_hits(query=query, hits=hits)


def lexical_rerank_hits(*, query: str, hits: list[KnowledgeSearchHit]) -> list[KnowledgeSearchHit]:
    """Boost chunks whose snippets share more token overlap with the query."""
    q_tokens = set(_TOKEN_RE.findall(query.lower()))
    if not q_tokens or not hits:
        return list(hits)

    def sort_key(hit: KnowledgeSearchHit) -> tuple[float, float]:
        s_tokens = set(_TOKEN_RE.findall(hit.snippet.lower()))
        overlap = len(q_tokens & s_tokens)
        lex_part = overlap / float(len(q_tokens))
        return (lex_part, hit.score)

    return sorted(hits, key=sort_key, reverse=True)
