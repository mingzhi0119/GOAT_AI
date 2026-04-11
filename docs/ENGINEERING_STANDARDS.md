# GOAT AI - Engineering Standards

Single source of truth for repo-wide engineering rules. Keep [`AGENTS.md`](../AGENTS.md) aligned with this file.

## 0. Core Principles

1. Fail fast on invalid config.
2. Keep business logic out of route handlers.
3. Stay portable across Windows dev and Ubuntu prod.
4. Type every function boundary.
5. Test boundaries and mock external systems.

## 0A. Industrial Score Guardrails

Engineering work must not silently lower the repo's correctness, testability, maintainability, readability, architecture, reliability, performance, security, observability, or delivery maturity.

- Treat a failing CI-equivalent local gate as a release blocker, not as follow-up cleanup.
- New feature work must not widen a public capability surface while the corresponding build, contract, or runtime gate is red.
- When touching a core path, add or update tests for:
  - normal flow
  - failure flow
  - at least one boundary or limit case
- Contract changes must update implementation, tests, and generated artifacts in the same change.
- Changes that add more logic to a known hotspot should first extract or isolate responsibilities instead of extending a large mixed-concern module inline.
- Security-sensitive changes must preserve or improve validation, authz, secret handling, and auditability.
- Runtime or deployment changes must preserve or improve observability, rollbackability, and failure diagnostics.
- Changes to process-local reliability seams such as rate limiting, idempotency, and background execution must stay behind replaceable interfaces and keep direct tests for the recovery/failure behavior.
- Desktop startup, sidecar boot, or first-run diagnostic changes must update both the Rust startup tests and the scripted desktop smoke path in the same change.
- Changes to release packaging or shipped desktop artifacts must preserve or improve provenance evidence (artifact digest, SBOM, and when available attestation) instead of weakening it.
- If a change would knowingly reduce one of the industrial-score dimensions, document the tradeoff explicitly in the PR and add a follow-up gate or remediation item before merge.

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
- Core-path tests must cover happy path, failure path, and at least one boundary condition.
- When fixing a bug, add or update the test that would have caught it before the fix.
- Prefer direct tests for decision-heavy modules; do not rely only on end-to-end or black-box coverage when the internal branch logic is complex.
- Run the relevant CI-equivalent checks for the layer you changed.
- For frontend changes, run `cd frontend && npm ci && npm test -- --run`.
- CI also runs `cd frontend && npm run build`; run that locally for frontend changes that touch types, build inputs, packaging, test utilities, or any path that may compile differently from `vitest`.
- Desktop shell changes must keep `cargo test --manifest-path frontend/src-tauri/Cargo.toml` green.
- Delivery and desktop wrapper changes must keep the scripted smoke coverage green (`python -m pytest __tests__/test_desktop_smoke.py` and any affected script tests).
- Prefer coverage reporting and fail-under thresholds for backend and frontend; do not lower thresholds without an explicit documented exception.
- Do not run manual visual verification unless the user asks.
- Keep recurring quality snapshot automation healthy when changing coverage paths, workflow names, or artifact locations.

## 4. Cross-Environment Compatibility

- No hardcoded localhost-only assumptions.
- No hardcoded OS-specific paths or separators.
- Defaults should work in development and production without edits.
- Prefer startup validation over runtime surprises.
- On Windows development hosts, run Linux-targeted compile, package, shell-script, and Ubuntu CI-parity checks through WSL rather than plain PowerShell.
- Treat PowerShell-only results as insufficient evidence for Linux correctness when the target artifact or runtime is Linux-specific.

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
- Reject changes that leave touched layers with red `lint`, `test`, `build`, `contract`, or security gates.
- Treat user-visible garbled text, encoding regressions, or broken diagnostics as correctness issues, not cosmetic follow-ups.
- Flag growing hotspot files early; if a touched mixed-concern file is already oversized, prefer extraction over further inline expansion.
- Keep `.github/CODEOWNERS` as the source of truth for default directory ownership.
- Keep `.github/workflows/release-governance.yml` and the GitHub Environment approval rules aligned with the documented release process in `docs/RELEASE_GOVERNANCE.md`.
- Keep `.github/workflows/quality-trends.yml`, `tools/quality_snapshot.py`, and `docs/QUALITY_TRENDS.md` aligned when quality-trend inputs change.
- Use four long-lived Codex owner lanes: Lead/Platform, Frontend, Backend, Docs/Assets.
- Shared contracts and cross-layer boundaries must be jointly reviewed by the owning lanes.
- Lead/Platform owns CI, governance boundaries, shared-boundary arbitration, and the final merge recommendation.
- Keep the sync policy stable: `main` rebases `origin/main`; owner branches rebase `main`; do not default to `git merge origin/main` inside owner threads.

## 8. API Contract Workflow

- Prefer contracts and tests over source spelunking.
- Check black-box tests first for API work.
- Keep generated artifacts in sync with the implementation.
- Treat `docs/openapi.json`, `docs/api.llm.yaml`, and other shared contract surfaces as joint review boundaries, not single-owner files.
- Do not merge public API behavior changes without matching boundary tests and updated error semantics where applicable.

## 9. Project Snapshot

- Follow the current repo layout and shipped inventory in `docs/PROJECT_STATUS.md`.
- Use `docs/ROADMAP.md` and `docs/OPERATIONS.md` for planning and ops context.

## 10. Production Constraints

- Production runs on Ubuntu.
- Keep filesystem, path, and process assumptions portable.
- Respect host limits and startup validation requirements.
- Linux-facing operational scripts and Linux-targeted desktop validation must be exercised under WSL or Ubuntu when developed from Windows.

## 11. Theme

- Keep frontend appearance behavior aligned with `docs/APPEARANCE.md`.
- Theme state persists in `localStorage`.
- Theme additions must extend the token registry and remain consistent across light and dark modes.

## 12. Documentation Updates

- `docs/` and `README.md` prose is English-only.
- Keep docs UTF-8 without BOM.
- Update related docs when user-visible semantics change.
- Update roadmap, operations, or project-status docs when release gates, runbooks, or score-protection policies materially change.
- Update `docs/SECURITY_RESPONSE.md` when vulnerability response targets, dependency-refresh cadence, or credential-rotation expectations change.
- When changing operator-facing metrics, update the versioned observability assets under `ops/observability/` and any affected incident runbooks in the same change.
- When changing performance budgets or smoke-test semantics, update `tools/load_chat_smoke.py`, the scheduled workflow, and `docs/OPERATIONS.md` together.
- When changing coverage output paths or recurring quality-capture semantics, update `tools/quality_snapshot.py`, `.github/workflows/quality-trends.yml`, and `docs/QUALITY_TRENDS.md` together.
- When changing backup, restore, rollback, or SQLite persistence semantics, update the recovery drill (`scripts/exercise_recovery_drill.py`), its tests, and the linked runbooks in the same change.

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
- Do not advertise a capability as ready in UI, docs, or release notes while build, runtime, or policy gates for that capability are known-red.
