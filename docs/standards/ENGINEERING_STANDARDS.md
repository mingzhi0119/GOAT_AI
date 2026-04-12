# GOAT AI - Engineering Standards

Single source of truth for repo-wide engineering rules. Keep [`AGENTS.md`](../../AGENTS.md) aligned with this file.

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

## 0B. Canonical Repository Layout

Treat the repository structure as an engineering contract, not as a convenience suggestion.

- Root tracked directories have fixed roles:
  - `backend/`: FastAPI application code and backend-only layers
  - `frontend/`: React/Vite app and `src-tauri/` desktop shell
  - `goat_ai/`: shared runtime packages that must not import `backend/`
  - `tools/`: canonical Python CLIs grouped by `contracts/`, `desktop/`, `ops/`, `quality/`, and `release/`
  - `ops/`: checked-in operator assets grouped by `deploy/`, `observability/`, `systemd/`, and `verification/`
  - `docs/`: canonical documentation grouped by `api/`, `architecture/`, `governance/`, `operations/`, and `standards/`
  - `__tests__/`: automated checks grouped by `backend/`, `contracts/`, `desktop/`, `governance/`, `helpers/`, `integration/`, and `ops/`
  - `scripts/`: shell or PowerShell entrypoints only; canonical Python CLIs belong under `tools/`
- Root files should stay limited to entrypoints, manifests, and repo-governance files such as `README.md`, `AGENTS.md`, `CLAUDE.md`, `server.py`, `pyproject.toml`, `requirements*.txt`, and `.env.example`.
- Do not add new deploy wrappers, service units, ad-hoc migration helpers, or one-off ops artifacts at the repo root when `ops/` or `tools/` already owns that concern.
- Backend placement rules:
  - `backend/application/`: use cases and router-facing orchestration
  - `backend/domain/`: core policy, value, and ownership semantics
  - `backend/platform/`: config, middleware, dependency factories, and runtime adapters
  - `backend/routers/`: HTTP-only translation layer
  - `backend/services/`: orchestration, persistence adapters, and integration logic
  - `backend/models/`: API-facing Pydantic contracts
  - `backend/migrations/`: numbered schema artifacts
- Shared-package placement rules:
  - `goat_ai/charts/`, `chat/`, `config/`, `llm/`, `runtime/`, `sandbox/`, `shared/`, `telemetry/`, and `uploads/` are the canonical shared-package subtrees; do not reintroduce flat `goat_ai/*.py` convenience modules for these concerns.
- Runtime-generated paths are not canonical source locations. `var/`, `data/`, `logs/`, build outputs, package caches, and local virtualenv directories must remain disposable and must not become homes for checked-in source assets.
- When adding a new file, place it by concern and ownership first. If no canonical home exists, extend the nearest existing subtree and update `README.md`, `AGENTS.md`, `.github/CODEOWNERS`, and any path-truth tests in the same change.

## 0C. Industrial Score Gate Map

Every change should preserve or improve the ten industrial-score dimensions below. The named gates are part of the repository contract, not optional hygiene.

- `Correctness`: preserve boundary behavior with direct tests, black-box API contracts, and contract-sync truth (`__tests__/contracts/test_api_blackbox_contract.py`, `docs/api/openapi.json`, `docs/api/api.llm.yaml`).
- `Testability`: keep injectable boundaries and deterministic tests; touched core paths require happy-path, failure-path, and boundary-case coverage with the relevant local CI-equivalent command green.
- `Maintainability`: keep code in canonical directories, avoid mixed-concern hotspot growth, and prefer extraction before extending oversized modules inline.
- `Readability`: keep routers thin, names explicit, function boundaries typed, and user-visible semantics mirrored in docs when behavior changes.
- `Architecture & Decoupling`: keep `lint-imports` green, preserve `backend/` vs `goat_ai/` boundaries, and keep process-local seams behind replaceable interfaces.
- `Reliability & Fault Tolerance`: preserve readiness semantics, startup recovery, rollback/runbook paths, recovery drills, and failure-state tests for durable tasks, persistence, or deploy flows.
- `Performance & Resource Efficiency`: keep latency gates, load smoke, bundle budgets, and polling discipline healthy (`python -m tools.quality.run_pr_latency_gate`, `python -m tools.quality.load_chat_smoke`, `cd frontend && npm run bundle:check`).
- `Security`: preserve validation, authz, secret handling, dependency-review evidence, secret scanning, and auditability; do not log raw credentials or weaken scoped capability gates.
- `Observability`: preserve `X-Request-ID`, structured logs, metrics, smoke diagnostics, and incident/runbook evidence; changes to operator-facing telemetry must update the corresponding docs and assets together.
- `Delivery Maturity`: keep CI, release governance, provenance, and fault-injection gates aligned (`.github/workflows/ci.yml`, `release-governance.yml`, `desktop-provenance.yml`, `fault-injection.yml`).
- If a change touches one of these dimensions, update the matching gate, workflow, test, or runbook in the same change instead of leaving the repo in a temporarily inconsistent state.

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
- `backend/application/`: router-facing use cases and orchestration
- `backend/domain/`: core policy and value semantics
- `backend/platform/config.py`: validated settings
- `backend/platform/dependencies.py`: dependency factories
- `backend/platform/`: middleware, runtime adapters, and platform-specific boundaries
- `backend/routers/`: HTTP layer only
- `backend/services/`: orchestration and integrations
- `backend/models/`: Pydantic schemas only
- `backend/migrations/`: numbered schema artifacts

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
- Keep generated contract types under `src/api/generated/` and regenerate them from `docs/api/openapi.json`.
- Use `src/api/types.ts` only for frontend-specific adapters or UI-only unions that cannot come straight from OpenAPI.
- Keep network calls inside `src/api/`.
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
- For frontend changes, run `cd frontend && npm ci && npm run lint && npm run contract:check && npm test -- --run`.
- CI also runs `cd frontend && npm run build && npm run bundle:check && npm run test:e2e`; run those locally for frontend changes that touch types, build inputs, protected browser flows, packaging, or any path that may compile differently from `vitest`.
- Desktop shell changes must keep `cargo test --manifest-path frontend/src-tauri/Cargo.toml` green.
- Delivery and desktop wrapper changes must keep the scripted smoke coverage green (`python -m pytest __tests__/desktop/test_desktop_smoke.py` and any affected script tests).
- Prefer coverage reporting and fail-under thresholds for backend and frontend; do not lower thresholds without an explicit documented exception.
- Do not run manual visual verification unless the user asks.
- Keep recurring quality snapshot automation healthy when changing coverage paths, workflow names, or artifact locations.

### Test layout

- `__tests__/backend/`: backend unit and service/application/platform tests
- `__tests__/contracts/`: black-box API and contract-governance tests
- `__tests__/desktop/`: desktop shell, packaging, and release-governance tests
- `__tests__/governance/`: structure/path-truth and docs/governance tests
- `__tests__/helpers/`: shared test utilities only
- `__tests__/integration/`: cross-layer integration tests
- `__tests__/ops/`: deploy, rollback, backup, recovery, and operator-asset tests
- Keep new tests in the narrowest canonical subtree that matches the behavior under test.

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
- Update `docs/api/openapi.json` and `docs/api/api.llm.yaml` when the contract changes.

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
- Keep `.github/workflows/release-governance.yml` and the GitHub Environment approval rules aligned with the documented release process in `docs/operations/RELEASE_GOVERNANCE.md`.
- Keep `.github/workflows/quality-trends.yml`, `tools/quality/quality_snapshot.py`, and `docs/governance/QUALITY_TRENDS.md` aligned when quality-trend inputs change.
- Keep `.github/workflows/fault-injection.yml` aligned with the targeted resilience drills it is expected to prove.
- Use four long-lived Codex owner lanes: Lead/Platform, Frontend, Backend, Docs/Assets.
- Shared contracts and cross-layer boundaries must be jointly reviewed by the owning lanes.
- Lead/Platform owns CI, governance boundaries, shared-boundary arbitration, and the final merge recommendation.
- Keep the sync policy stable: `main` rebases `origin/main`; owner branches rebase `main`; do not default to `git merge origin/main` inside owner threads.

## 8. API Contract Workflow

- Prefer contracts and tests over source spelunking.
- Check black-box tests first for API work.
- Keep generated artifacts in sync with the implementation.
- Treat `docs/api/openapi.json`, `docs/api/api.llm.yaml`, and other shared contract surfaces as joint review boundaries, not single-owner files.
- Do not merge public API behavior changes without matching boundary tests and updated error semantics where applicable.

## 9. Project Snapshot

- Follow the current repo layout and shipped inventory in `docs/governance/PROJECT_STATUS.md`.
- Use `docs/governance/ROADMAP.md` and `docs/operations/OPERATIONS.md` for planning and ops context.
- Treat Section `0B. Canonical Repository Layout` in this file as the placement authority when deciding where new code, docs, tests, tools, or ops assets belong.

## 10. Production Constraints

- Production runs on Ubuntu.
- Keep filesystem, path, and process assumptions portable.
- Respect host limits and startup validation requirements.
- Linux-facing operational scripts and Linux-targeted desktop validation must be exercised under WSL or Ubuntu when developed from Windows.

## 11. Theme

- Keep frontend appearance behavior aligned with `docs/standards/APPEARANCE.md`.
- Theme state persists in `localStorage`.
- Theme additions must extend the token registry and remain consistent across light and dark modes.

## 12. Documentation Updates

- `docs/` and `README.md` prose is English-only.
- Keep docs UTF-8 without BOM.
- Update related docs when user-visible semantics change.
- Update roadmap, operations, or project-status docs when release gates, runbooks, or score-protection policies materially change.
- Update `docs/governance/SECURITY_RESPONSE.md` when vulnerability response targets, dependency-refresh cadence, or credential-rotation expectations change.
- When changing operator-facing metrics, update the versioned observability assets under `ops/observability/` and any affected incident runbooks in the same change.
- When changing performance budgets or smoke-test semantics, update `tools/quality/load_chat_smoke.py`, the scheduled workflow, and `docs/operations/OPERATIONS.md` together.
- When changing coverage output paths or recurring quality-capture semantics, update `tools/quality/quality_snapshot.py`, `.github/workflows/quality-trends.yml`, and `docs/governance/QUALITY_TRENDS.md` together.
- When changing dependency-audit evidence or credential-rotation review inputs, update `tools/quality/security_review_snapshot.py`, `.github/workflows/quality-trends.yml`, and `docs/governance/SECURITY_RESPONSE.md` together.
- When changing backup, restore, rollback, or SQLite persistence semantics, update the recovery drill (`tools/ops/exercise_recovery_drill.py`), its tests, and the linked runbooks in the same change.

## 13. API Artifacts

- Keep `docs/api/openapi.json` and `docs/api/api.llm.yaml` in sync with the codebase.
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
