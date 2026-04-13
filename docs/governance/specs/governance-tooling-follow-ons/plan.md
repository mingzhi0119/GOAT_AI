# Governance Tooling Follow-ons Plan

Status: pilot landed

This is a non-canonical working artifact captured for one complex brownfield change.

## Slices

- Slice A
  Goal: add `docs/decisions/` templates, references, and PR guidance.
  Main files: `docs/decisions/`, `.github/pull_request_template.md`, docs references, governance tests.
  Risks: governance drift if docs and ownership pointers do not move with the new entrypoint.
  Validation: governance pytest coverage plus touched-file Ruff checks.
  Assumptions or decisions: keep existing architecture decision packages in place and link to them.

- Slice B
  Goal: add frontend-only `dependency-cruiser` with a minimal ruleset and CI hook.
  Main files: `frontend/.dependency-cruiser.cjs`, `frontend/package.json`, `.github/workflows/ci.yml`, shared type extraction, governance tests.
  Risks: too-strict rules could fail the existing frontend layout.
  Validation: `npm run depcruise`, `npm run lint`, governance tests, and `npm run build`.
  Assumptions or decisions: keep network calls behind `src/api/` and do not expand scope to Python imports.

- Slice C
  Goal: add `zod` runtime parsing for `/api/system/features` and code sandbox JSON, plus the smallest public contract tightening needed for parity.
  Main files: `backend/models/system.py`, `docs/api/*`, `frontend/src/api/*`, frontend tests, contract governance tests.
  Risks: frontend runtime parsing could drift from the public contract if it becomes stricter than the generated surface.
  Validation: contract sync, black-box API tests, `contract:check`, targeted frontend tests, `npm run build`.
  Assumptions or decisions: only tighten `CodeSandboxFeaturePayload.isolation_level`; normalize `deny_reason` instead of inventing a frontend-owned enum.

- Slice D
  Goal: add this lightweight `spec/plan/tasks` pilot.
  Main files: `docs/governance/specs/README.md`, `_template/`, example folder, governance tests.
  Risks: feature specs could be mistaken for the canonical governance layer.
  Validation: governance pytest coverage and docs language/path truth tests.
  Assumptions or decisions: keep the allowed file set narrow and include an explicit non-canonical disclaimer in every template.

- Slice E
  Goal: sync landed facts into status docs, keep residual work in the roadmap, and run the final validation matrix.
  Main files: `ROADMAP.md`, `PROJECT_STATUS.md`, `OPERATIONS.md`, README/docs references, governance tests.
  Risks: pilot work could be overstated as full repo-wide adoption.
  Validation: combined governance, contract, lint, build, depcruise, and targeted API proof checks.
  Assumptions or decisions: do not relabel already-landed OTel, gitleaks, or import-linter work as new follow-ons.
