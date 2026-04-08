from __future__ import annotations

from typing import Protocol

from backend.services.knowledge_pipeline import KnowledgeSearchHit


class KnowledgeReranker(Protocol):
    """Swappable rerank seam; implementations stay free of HTTP concerns."""

    def rerank(self, *, query: str, hits: list[KnowledgeSearchHit]) -> list[KnowledgeSearchHit]: ...


class KnowledgeQueryRewriter(Protocol):
    """Opt-in query normalization; profile-gated at the service boundary."""

    def rewrite_for_retrieval(self, *, query: str) -> str: ...
