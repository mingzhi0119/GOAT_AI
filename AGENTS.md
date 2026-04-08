# GOAT AI Agent Memory

Short durable index for coding agents and contributors. Canonical engineering rules live in one place.

## Canonical standards

- [`docs/ENGINEERING_STANDARDS.md`](docs/ENGINEERING_STANDARDS.md) - full rules for Python, TypeScript, testing, API design, cross-env behavior, production host constraints, documentation workflow, API artifacts, and recovery. Section 15 covers capability-based feature gates for optional high-risk features such as a future code sandbox.
- [`docs/DOMAIN.md`](docs/DOMAIN.md) - ubiquitous domain language (Phase 15.1); update when user-visible chat, chart, or safeguard semantics change.
- Editor rules under `.cursor/rules/` must mirror the same principles; keep them aligned whenever either file changes.

## Documentation language

- `docs/` and `README.md` are English-only for committed prose.
- Keep docs UTF-8 without BOM.
- Keep the root `.editorconfig` in sync so editors default to `charset = utf-8`.
- Prefer ASCII-safe prose where practical, and avoid mojibake or replacement characters.

## Five non-negotiables (summary)

1. Fail fast, fail loud at startup for invalid config.
2. Decouple by boundary: handler -> service -> client; no business logic in route handlers.
3. Portable by default: Windows dev and Ubuntu prod without source edits.
4. Type everything at function boundaries.
5. Test the boundary, mock the world.

## Where to look first (API work)

- Black-box: `__tests__/test_api_blackbox_contract.py` (plus auth/security suites when relevant).
- Contracts: `docs/openapi.json`, `docs/api.llm.yaml`.

## Developer CLI (`tools/`)

Run from the repository root with `python -m tools.<module>` (for example `python -m tools.run_rag_eval`, `python -m tools.check_api_contract_sync`, `python -m tools.generate_llm_api_yaml`). See `.env.example` and do not rely on `PYTHONPATH` in `.env` for shell commands.

## Ops and roadmap pointers

- Runbook-style ops: [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- Phases and decisions: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- Current shipped inventory: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
