# Governance Tooling Follow-ons

Status: pilot landed

This is a non-canonical working artifact captured for one complex brownfield change.

## Summary

Land the roadmap follow-ons for decision records, frontend dependency boundaries, high-risk API runtime parsing, and lightweight feature work products without replacing the repository's existing governance skeleton.

## Scope

- In scope: `docs/decisions/`, frontend-only `dependency-cruiser`, `zod` runtime parsing for `/api/system/features` and code sandbox JSON, and this lightweight `spec/plan/tasks` pilot.
- Out of scope: GitHub Spec Kit as a full framework, OpenAPI Generator, replacing Python `import-linter`, or introducing a second constitution/process system.

## Constraints

- Keep `docs/api/openapi.json -> openapi-typescript -> contract:check` as the only frontend contract generation chain.
- Keep `dependency-cruiser` scoped to `frontend/`.
- Treat `ROADMAP.md` as planned work and `PROJECT_STATUS.md` as landed fact.
- Preserve the existing `docs/architecture/*DECISION*.md` files in place while adding a unified decision entrypoint.

## Acceptance

- Decision records have a canonical entrypoint, templates, and PR guidance.
- Frontend dependency boundaries are mechanically checked in CI.
- High-risk frontend API boundaries parse runtime JSON instead of relying on unchecked casts.
- This example remains obviously subordinate to the canonical governance files.
