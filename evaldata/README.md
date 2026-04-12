# RAG evaluation golden set (`evaldata/`)

## Purpose

JSONL cases consumed by **`python -m tools.quality.run_rag_eval`** (from the repository root) for **Phase 14.7** regression: conservative query rewrite, lexical rerank, and passthrough rerank. CI runs this module on every backend pipeline; **merge is blocked** if the runner exits non-zero.

## File

| File | Role |
|------|------|
| `rag_eval_cases.jsonl` | One JSON object per line (`op`: `rewrite` \| `lexical_rerank` \| `passthrough`). Schema is defined by `tools/run_rag_eval.py`. |

## Versioning

- Bump **`evaldata/VERSION`** (single line, ISO date or semver) when you **add, remove, or materially change** cases.
- PRs that touch `rag_eval_cases.jsonl` should state **why** the golden set changed (new behavior, bug fix, expanded coverage).

## Review checklist

1. Each case has a stable string **`id`** for failure messages.
2. **`expected`** / **`expect_top_chunk_id`** reflect **intended** product behavior, not accidental current output.
3. Run locally: `python -m tools.quality.run_rag_eval` (exit 0).

## Related docs

- [docs/operations/OPERATIONS.md](../docs/operations/OPERATIONS.md) — `GOAT_RAG_RERANK_MODE`, `retrieval_profile`, metrics.
- [docs/governance/ROADMAP.md](../docs/governance/ROADMAP.md) — §14.7 RAG quality closure.
