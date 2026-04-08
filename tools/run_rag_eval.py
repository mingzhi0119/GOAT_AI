from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.knowledge_pipeline import KnowledgeSearchHit
from backend.services.retrieval_quality.query_rewrite import conservative_rewrite_query
from backend.services.retrieval_quality.rerank import lexical_rerank_hits
from backend.services.retrieval_quality.rerank import PassthroughReranker


def _load_cases(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _run_case(case: dict[str, object]) -> None:
    op = str(case["op"])
    if op == "rewrite":
        got = conservative_rewrite_query(str(case["input"]))
        assert got == str(case["expected"]), f"{case['id']}: expected {case['expected']!r}, got {got!r}"
        return
    if op == "lexical_rerank":
        hits = [
            KnowledgeSearchHit(
                chunk_id=str(h["chunk_id"]),
                document_id=str(h["document_id"]),
                filename=str(h["filename"]),
                snippet=str(h["snippet"]),
                score=float(h["score"]),
            )
            for h in case["hits"]  # type: ignore[assignment]
        ]
        ranked = lexical_rerank_hits(query=str(case["query"]), hits=hits)
        assert ranked[0].chunk_id == str(case["expect_top_chunk_id"]), f"{case['id']}: wrong top hit"
        return
    if op == "passthrough":
        hits = [
            KnowledgeSearchHit(
                chunk_id=str(h["chunk_id"]),
                document_id=str(h["document_id"]),
                filename=str(h["filename"]),
                snippet=str(h["snippet"]),
                score=float(h["score"]),
            )
            for h in case["hits"]  # type: ignore[assignment]
        ]
        out = PassthroughReranker().rerank(query=str(case["query"]), hits=hits)
        assert out[0].chunk_id == str(case["expect_top_chunk_id"]), f"{case['id']}: wrong top hit"
        return
    raise AssertionError(f"unknown op: {op}")


def main() -> int:
    cases_path = _REPO_ROOT / "evaldata" / "rag_eval_cases.jsonl"
    if not cases_path.is_file():
        print(f"missing eval cases: {cases_path}", file=sys.stderr)
        return 2
    cases = _load_cases(cases_path)
    for case in cases:
        _run_case(case)
    print(f"rag_eval: OK ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
