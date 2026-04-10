# GOAT AI - Engineering Standards

Single source of truth for repo-wide engineering rules. Keep [`AGENTS.md`](../AGENTS.md) aligned with this file.

## 0. Core Principles

1. Fail fast on invalid config.
2. Keep business logic out of route handlers.
3. Stay portable across Windows dev and Ubuntu prod.
4. Type every function boundary.
5. Test boundaries and mock external systems.

## 1. Python Standards

- Annotate every function and module-level variable.
- Prefer `Protocol` for injectable dependencies and `dataclass` or `pydantic.BaseModel` for structured data.
- Use `from __future__ import annotations` in Python files.
- FastAPI request and response bodies must be `BaseModel` subclasses.
- Validate settings at startup and fail immediately on bad config.
- Use `logging.getLogger(__name__)`; do not `print()` in production code.
- Use `pathlib.Path`; avoid hardcoded OS-specific paths.
- Route handlers validate input and translate domain errors to `HTTPException`.
- Services orchestrate work; models carry data only.

### Backend layout

- `backend/main.py`: app factory and router wiring
- `backend/config.py`: validated settings
- `backend/dependencies.py`: dependency factories
- `backend/routers/`: HTTP layer only
- `backend/services/`: orchestration and integrations
- `backend/models/`: Pydantic schemas only

### Import boundaries

- Run `lint-imports` from the repo root.
- Routers must not import `goat_ai` directly.
- Shared code under `goat_ai/` must not import `backend/`.
- Keep `tabular_context` and `log_service` usage behind the intended service boundaries.

### Session and ports

- Keep persisted session payloads versioned and backward compatible.
- Treat ports and injectable boundaries as first-class contracts.

## 2. TypeScript / React Standards

- Keep TypeScript strict.
- Do not use `any` or `@ts-ignore`.
- Define API types in `src/api/types.ts` and keep network calls inside `src/api/`.
- Keep components focused and hooks typed.
- Avoid business logic in JSX.
- Keep frontend accessibility at WCAG 2.2 AA by default.
- Use `lucide-react` for frontend UI icons.
- Default icon stroke width is `2`.
- Use `1.5` only when a dense utility icon looks too heavy at the default stroke.
- Use `1.25` only for cramped micro-icons when even `1.5` looks visually heavy.
- Avoid introducing new custom inline SVG icons for ordinary UI controls.

### Frontend layout

- `src/components/`: presentation
- `src/hooks/`: custom hooks
- `src/api/`: typed fetch wrappers
- `src/utils/`: shared helpers

## 3. Testing Standards

- Test behavior at the boundary.
- Mock external services in unit tests.
- Python tests use `pytest`.
- Frontend tests use `Vitest` and `React Testing Library`.
- Run the same checks CI runs when touching backend code.
- For frontend changes, run `cd frontend && npm ci && npm test -- --run`.
- Do not run frontend build or manual visual verification unless the user asks.

## 4. Cross-Environment Compatibility

- No hardcoded localhost-only assumptions.
- No hardcoded OS-specific paths or separators.
- Defaults should work in development and production without edits.
- Prefer startup validation over runtime surprises.

## 5. API Design Rules

- Keep request and response schemas explicit.
- Return structured errors, not ad hoc strings.
- Preserve API contracts when changing behavior.
- Update `docs/openapi.json` and `docs/api.llm.yaml` when the contract changes.

## 6. Dependency Management

- Python dependencies come from `requirements*.txt`.
- Frontend dependencies come from `frontend/package-lock.json`.
- Do not introduce hidden dependencies or untracked tool versions.

## 7. Git & Review Checklist

- Keep changes small and focused.
- Do not revert unrelated user changes.
- Use non-interactive git commands.
- For reviews, call out bugs, regressions, risk, and missing tests first.

## 8. API Contract Workflow

- Prefer contracts and tests over source spelunking.
- Check black-box tests first for API work.
- Keep generated artifacts in sync with the implementation.

## 9. Project Snapshot

- Follow the current repo layout and shipped inventory in `docs/PROJECT_STATUS.md`.
- Use `docs/ROADMAP.md` and `docs/OPERATIONS.md` for planning and ops context.

## 10. Production Constraints

- Production runs on Ubuntu.
- Keep filesystem, path, and process assumptions portable.
- Respect host limits and startup validation requirements.

## 11. Theme

- Keep frontend appearance behavior aligned with `docs/APPEARANCE.md`.
- Theme state persists in `localStorage`.
- Theme additions must extend the token registry and remain consistent across light and dark modes.

## 12. Documentation Updates

- `docs/` and `README.md` prose is English-only.
- Keep docs UTF-8 without BOM.
- Update related docs when user-visible semantics change.

## 13. API Artifacts

- Keep `docs/openapi.json` and `docs/api.llm.yaml` in sync with the codebase.
- Treat contract drift as a bug.

## 14. Recovery and Commit Hygiene

- Keep failures actionable and recoverable.
- Preserve commit history cleanliness.
- Prefer small fixes over broad rewrites.

## 15. Feature Gates

- Use capability-based gates for risky or optional features.
- Do not conflate UI availability with backend permission or execution safety.
- Document gate behavior and safe failure modes.
