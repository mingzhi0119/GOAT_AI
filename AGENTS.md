# GOAT AI Agent Memory

Short index for coding agents. Canonical rules live in the docs below.

## Read if Needed

- [`docs/ENGINEERING_STANDARDS.md`](docs/ENGINEERING_STANDARDS.md)
- [`docs/DOMAIN.md`](docs/DOMAIN.md)
- [`docs/APPEARANCE.md`](docs/APPEARANCE.md)

- Frontend UI icons use `lucide-react`; default stroke width is `2` unless a dense or cramped case needs an exception.

## Keep in mind

1. Fail fast on invalid config.
2. Keep logic out of route handlers.
3. Support Windows dev and Ubuntu prod without source edits.
4. Type every function boundary.
5. Test the boundary, mock external systems.

## Before delivering code

- Follow the same checks as GitHub Actions in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
- Use Python 3.14 and `requirements-ci.txt` for backend work.
- For frontend changes, run `cd frontend && npm ci && npm test -- --run`.
- Do not run frontend build or manual visual verification unless the user asks.

## Quick pointers

- API work: `__tests__/test_api_blackbox_contract.py`, `docs/openapi.json`, `docs/api.llm.yaml`
- CLI helpers: `python -m tools.<module>`
- Keep `.cursor/rules/` aligned with these standards
