# GOAT AI Agent Memory

Short durable index for coding agents and contributors. **Canonical engineering rules live in one place:**

## Canonical standards

**[`docs/ENGINEERING_STANDARDS.md`](docs/ENGINEERING_STANDARDS.md)** — full rules (Python/TS, testing, API design, cross-env, production host, documentation workflow, API artifacts, recovery). **§15** describes **capability-based feature gates** for optional high-risk features (e.g. future code sandbox).

Editor rules under `.cursor/rules/` mirror the same principles; keep them aligned when either file changes.

## Documentation language

- **`docs/`** and **`README.md`** are **English-only** for committed prose (no Chinese or other languages in those files).

## Five non-negotiables (summary)

1. Fail fast, fail loud at startup for invalid config.
2. Decouple by boundary: handler → service → client; no business logic in route handlers.
3. Portable by default: Windows dev and Ubuntu prod without source edits.
4. Type everything at function boundaries.
5. Test the boundary, mock the world.

## Where to look first (API work)

- Black-box: `__tests__/test_api_blackbox_contract.py` (plus auth/security suites when relevant).
- Contracts: `docs/openapi.json`, `docs/api.llm.yaml`.

## Developer CLI (`tools/`)

Run from the **repository root** with **`python -m tools.<module>`** (e.g. `python -m tools.run_rag_eval`, `python -m tools.check_api_contract_sync`, `python -m tools.generate_llm_api_yaml`). See `.env.example` — do not rely on `PYTHONPATH` in `.env` for shell commands.

## Ops and roadmap pointers

- Runbook-style ops: [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- Phases and decisions: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- Current shipped inventory: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
