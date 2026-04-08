from __future__ import annotations

import unittest
from dataclasses import replace

from goat_ai.config import load_settings

from backend.services.knowledge_pipeline import KnowledgeSearchHit
from backend.services.retrieval_quality.policy import resolve_query_rewrite_enabled, resolve_rerank_mode
from backend.services.retrieval_quality.query_rewrite import conservative_rewrite_query
from backend.services.retrieval_quality.rerank import lexical_rerank_hits


class TestRagRetrievalQuality(unittest.TestCase):
    def test_conservative_rewrite_collapses_whitespace(self) -> None:
        self.assertEqual("a b", conservative_rewrite_query("  a   b  "))

    def test_lexical_rerank_prefers_overlap(self) -> None:
        hits = [
            KnowledgeSearchHit(
                chunk_id="low",
                document_id="d1",
                filename="f.txt",
                snippet="unrelated gamma text",
                score=0.95,
            ),
            KnowledgeSearchHit(
                chunk_id="high",
                document_id="d1",
                filename="f.txt",
                snippet="alpha beta and more",
                score=0.1,
            ),
        ]
        ranked = lexical_rerank_hits(query="alpha beta", hits=hits)
        self.assertEqual("high", ranked[0].chunk_id)

    def test_resolve_rerank_mode_default_profile(self) -> None:
        base = load_settings()
        lexical = replace(base, rag_rerank_mode="lexical")
        self.assertEqual("lexical", resolve_rerank_mode(retrieval_profile="default", settings=lexical))
        passthrough = replace(base, rag_rerank_mode="passthrough")
        self.assertEqual("passthrough", resolve_rerank_mode(retrieval_profile="default", settings=passthrough))

    def test_resolve_rerank_mode_explicit_profiles(self) -> None:
        base = load_settings()
        self.assertEqual("lexical", resolve_rerank_mode(retrieval_profile="rag3_lexical", settings=base))
        self.assertEqual("lexical", resolve_rerank_mode(retrieval_profile="rag3_quality", settings=base))

    def test_resolve_query_rewrite_only_rag3_quality(self) -> None:
        self.assertTrue(resolve_query_rewrite_enabled(retrieval_profile="rag3_quality"))
        self.assertFalse(resolve_query_rewrite_enabled(retrieval_profile="rag3_lexical"))
        self.assertFalse(resolve_query_rewrite_enabled(retrieval_profile="default"))


if __name__ == "__main__":
    unittest.main()
