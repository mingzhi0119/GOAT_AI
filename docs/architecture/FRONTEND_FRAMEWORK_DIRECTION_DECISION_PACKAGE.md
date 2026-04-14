# Frontend Framework Direction Decision Package

Last updated: 2026-04-13

## Purpose

Record the repository-level decision boundary for keeping the shipped frontend
 on Vite versus migrating to Next.js, so the team can discuss the tradeoff with
 one durable source of truth instead of revisiting the same assumptions in each
 planning thread.

## Context

The current shipped frontend is a React 19 + TypeScript + Vite 8 single-page
 application under `frontend/`, with FastAPI serving the built SPA from
 `frontend/dist/` and Tauri consuming the same build output for the desktop
 shell. This is not just a framework choice inside the browser layer; it is a
 delivery-chain contract that currently touches:

- backend static mounting from `frontend/dist`
- Tauri `frontendDist` and desktop dev/build commands
- CI jobs for lint, tests, build, Playwright, and desktop packaging
- release bundle tooling that currently requires `frontend/dist/index.html`
- sub-path portability expectations for browser deployments

The team asked for an ADR-style conclusion plus a realistic four-week migration
 milestone, which means a lightweight decision record is insufficient. The
 migration cost is dominated by delivery compatibility, not by rewriting React
 components.

## Fixed constraints

- keep FastAPI as the current API/runtime system of record for `/api/*`
- keep the Tauri desktop shell and packaged desktop path non-regressive
- preserve sub-path deployment portability instead of assuming root-only hosting
- do not widen frontend promises to SSR-only or Node-middle-tier behavior unless
  the repo explicitly adopts those runtime dependencies
- keep migration work additive-first so rollback remains possible during the
  transition

## Decision

Keep Vite as the default shipped frontend for the current product phase.

Do not approve a Next.js migration as a framework-only cleanup task. Approve it
 only if the team explicitly needs one or more of the following outcomes:

- server-side rendering for public or indexable pages
- a Node-hosted frontend middle tier that must own auth/session logic
- framework-standard routing/layout/data-loading conventions that materially
  reduce future product cost
- a broader web platform strategy that justifies reworking the FastAPI/Tauri
  delivery chain

If the team later chooses to migrate anyway, the first migration target should
 be a conservative Next.js App Router shell that keeps the app mostly
 client-rendered and preserves the current FastAPI API ownership. The initial
 migration should not bundle SSR, BFF consolidation, or auth redesign into the
 same slice.

## Options considered

- Keep Vite as the shipped frontend baseline:
  - chosen because it aligns with the current browser shell, FastAPI static
    serving, desktop packaging, and release tooling with the least delivery
    risk
- Migrate to Next.js as a mostly client-rendered shell with static-export or
  export-compatible output:
  - viable if the team wants future Next.js conventions, but it still requires
    meaningful work across Tauri, FastAPI, CI, and release tooling before it is
    better than the current baseline
- Migrate to Next.js and also adopt SSR/BFF patterns immediately:
  - rejected for now because it combines framework migration with runtime and
    deployment redesign, which would hide risk and exceed a clean four-week
    brownfield slice

## Compatibility strategy

- Read compatibility:
  - preserve the current `/api/*` contract family and frontend runtime adapter
    boundaries during any migration
  - keep the existing client-side state model, including `localStorage`,
    browser-only UI effects, and SSE stream handling, until a separate decision
    explicitly changes them
- Write compatibility:
  - do not move chat, upload, history, system, sandbox, or workbench writes
    into new Next.js server actions during the initial migration
- Downgrade behavior:
  - the migration must remain reversible to the Vite build path until FastAPI,
    Tauri, CI, and release-bundle proof are all green on the new output shape
- Additive-first posture:
  - migrate by introducing a parallel Next.js build/output path first, then
    switch the consumers of the built assets only after the new path is proven

## Migration or rollout sequence

The four-week plan below is a conditional migration plan, not the current
 recommendation.

### Week 1 - Shell and runtime parity

- scaffold Next.js App Router inside `frontend/` without changing FastAPI API
  ownership
- port the current `main.tsx` and `App.tsx` entry pattern into a single client
  shell page
- migrate Tailwind, global CSS, and core client-only providers
- make the browser-only boundaries explicit for `localStorage`, `window`,
  `document`, and `crypto.randomUUID()`
- prove that chat, startup data loading, and appearance state still work in
  local development

### Week 2 - API adapters, SSE, and tests

- migrate `src/api/*` wrappers and keep `/api/*` requests pointed at FastAPI
- preserve typed runtime parsing and SSE boundaries for chat, upload, and
  sandbox logs
- update unit/integration tests so the existing protected browser flows still
  exercise the migrated shell
- replace the Vite dev proxy assumptions with a Next-compatible dev routing
  story

### Week 3 - Delivery-chain cutover

- rework FastAPI SPA/static mounting assumptions so the new frontend output is
  served correctly
- rework Tauri dev/build configuration so the desktop shell consumes the new
  frontend build output
- update CI commands for install, lint, tests, build, Playwright, and bundle
  checks
- update release-bundle tooling and any path-truth tests that assume
  `frontend/dist/index.html`

### Week 4 - Hardening and release proof

- run Windows and WSL/Linux validation for browser and desktop flows
- fix sub-path deployment regressions and static asset path issues
- update README, operations notes, and status/governance references as needed
- collect final regression proof before removing the Vite-first path
- keep rollback to Vite available until all CI-equivalent checks are green on
  the Next.js path

## Rollback strategy

- before delivery-chain cutover:
  - rollback is low-cost; the team can abandon the parallel Next.js path and
    keep the shipped Vite path untouched
- after FastAPI/Tauri/release-tooling cutover but before broad release:
  - rollback should restore the Vite build commands, Vite asset output
    expectations, and the previous static mount/package configuration as one
    coordinated change
- after release:
  - rollback requires restoring the previous frontend artifact contract used by
    FastAPI, Tauri, CI, and release packaging; this is exactly why the migration
    should not remove the proven Vite path until the new build chain is fully
    validated

## Validation and proof

- Current repository truth that favors keeping Vite:
  - `frontend/vite.config.ts`
  - `frontend/package.json`
  - `backend/main.py`
  - `frontend/src-tauri/tauri.conf.json`
  - `tools/release/build_release_bundle.py`
  - `README.md`
- Current validation gates that a migration would need to keep green:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run depcruise`
  - `cd frontend && npm run contract:check`
  - `cd frontend && npm run test -- --run`
  - `cd frontend && npm run build`
  - `cd frontend && npm run bundle:check`
  - `cd frontend && npm run test:e2e`
  - `cargo test --manifest-path frontend/src-tauri/Cargo.toml`
- Workflow or runbook links:
  - `.github/workflows/ci.yml`
  - `docs/operations/OPERATIONS.md`
  - `docs/standards/ENGINEERING_STANDARDS.md`
  - `docs/governance/PROJECT_STATUS.md`

## Open questions

- does the product roadmap actually need SSR, SEO, or a Node-owned web tier, or
  is the app still primarily a protected client shell
- if the team wants Next.js, should the first phase stay client-shell-only or
  intentionally adopt SSR/BFF behavior as a separate decision package
- what output contract should replace the current `frontend/dist` assumption
  across FastAPI, Tauri, and release bundling without breaking sub-path
  portability

## Related artifacts

- Roadmap item:
  - N/A for now; this package records a decision boundary rather than a landed
    roadmap slice
- Status or operations docs:
  - `README.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/operations/OPERATIONS.md`
  - `docs/governance/codex-logs/2026-04.md`
- Related PRs or follow-ups:
  - future frontend-platform decision to approve or reject a real Next.js
    migration
  - any later migration spec should link this package and define the exact
    FastAPI/Tauri/output compatibility contract before implementation starts
