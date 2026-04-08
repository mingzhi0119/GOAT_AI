from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ConservativeQueryRewriter:
    """Whitespace-only normalization — safe default for opt-in retrieval profiles."""

    def rewrite_for_retrieval(self, *, query: str) -> str:
        return conservative_rewrite_query(query)


def conservative_rewrite_query(query: str) -> str:
    """Collapse runs of whitespace; trim ends. No semantic expansion."""
    stripped = query.strip()
    if not stripped:
        return query
    return re.sub(r"\s+", " ", stripped)
