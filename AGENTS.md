# GOAT AI Agent Memory

Short index for coding agents. Canonical rules live in the docs below.

## Read if Needed

- [`docs/standards/ENGINEERING_STANDARDS.md`](docs/standards/ENGINEERING_STANDARDS.md)
- [`docs/architecture/DOMAIN.md`](docs/architecture/DOMAIN.md)
- [`docs/standards/APPEARANCE.md`](docs/standards/APPEARANCE.md)

- Frontend UI icons use `lucide-react`; default stroke width is `2` unless a dense or cramped case needs an exception.

## Keep in mind

1. Fail fast on invalid config.
2. Keep logic out of route handlers.
3. Support Windows dev and Ubuntu prod without source edits.
4. Type every function boundary.
5. Test the boundary, mock external systems.
6. Do not let touched layers regress industrial score guardrails: green gates, boundary tests, and recoverable runtime behavior.
7. On Windows hosts, every Linux-targeted compile, package, shell-script validation, or Ubuntu CI-parity check must run through WSL, not plain PowerShell.

## Before delivering code

- Follow the relevant checks from GitHub Actions in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) when practical.
- Use Python 3.14 and `requirements-ci.txt` for backend work.
- For Python changes, run `python -m ruff check` on the touched backend/shared/test files before pushing.
- When formatting-sensitive Python files changed, also run `python -m ruff format --check` on the touched files.
- For frontend changes, run `cd frontend && npm ci && npm test -- --run`.
- CI also runs `cd frontend && npm run build`; run the local build for frontend changes that touch types, build inputs, packaging, test utilities, or any build-only failure path.
- For Linux-targeted validation from Windows, prefer the repo-local skills under [`.agents/skills`](.agents/skills): `$wsl-linux-build`, `$wsl-linux-rust-desktop`, and `$wsl-linux-ops-checks`.
- Repo-local `goat-*` skills under [`.agents/skills`](.agents/skills) are the governance/proof layer: use them to decide what truth to read, what gates matter, and what counts as landed evidence before editing or closing a slice.
- Treat the `wsl-*` skills as execution helpers rather than replacements for the `goat-*` workflows.
- High-frequency entry points:
  - use `$goat-engineering-audit` for readiness reviews and structured findings
  - use `$goat-api-contract-proof` for HTTP schema/docs/frontend contract sync
  - use `$goat-ci-surface-router` to choose the minimum correct validation matrix
  - use `$goat-desktop-release-evidence` when desktop workflows, tools, or proof docs change
  - use `$goat-workbench-authz-proof` when workbench scopes, source visibility, or `/api/system/features` may widen
  - use `$goat-observability-contract-proof` when metrics, alerts, dashboards, or observability runbooks change
  - use `$goat-governance-sync` when proof is already landed and roadmap/status/ops docs may need the owning update
- Skills are the reusable workflow layer; `AGENTS.md` and [`docs/standards/ENGINEERING_STANDARDS.md`](docs/standards/ENGINEERING_STANDARDS.md) remain the enforcement point for permanent repository policy.
- Add or update tests for happy path, failure path, and at least one boundary case when you touch core behavior.
- Do not treat a red local CI-equivalent gate as follow-up work.
- Do not run manual visual verification unless the user asks.

## Quick pointers

- API work: `__tests__/contracts/test_api_blackbox_contract.py`, `docs/api/openapi.json`, `docs/api/api.llm.yaml`
- CLI helpers: `python -m tools.<module>`
- Keep `.cursor/rules/` aligned with these standards
- Directory ownership lives in [`.github/CODEOWNERS`](.github/CODEOWNERS)

## Lead Agent Model

The current thread is the Lead Agent unless explicitly reassigned. The Lead Agent coordinates subagents, consolidates findings, and performs the final repo edits.

### Current Subagent Bindings

- Frontend Owner -> `Galileo`
- Backend Owner -> `Rawls`
- Docs / Assets Owner -> `Helmholtz`

### Lead-only operating rules

- Use subagents as analysts, reviewers, and auditors by default.
- Subagents are read-only unless write access is explicitly delegated for a narrow task.
- Subagents must not create commits, make unilateral implementation decisions, or open new worktrees.
- If a new worktree is needed, the user will create or manage it directly.
- The Lead Agent is the sole writing agent by default and owns final code changes, patch integration, and PR-ready cleanup.

### Lead responsibilities

1. Restate the main goal and decompose it into bounded investigations.
2. Assign each subagent a clear scope with strict file and domain boundaries.
3. Require structured findings instead of code edits.
4. Merge duplicate findings, rank them by severity, and resolve conflicts.
5. Produce a concise implementation plan.
6. Apply the final code changes.
7. Run or recommend the relevant checks.
8. Summarize changes, validation, residual risks, and follow-up items.

### Default subagent scopes

- `Galileo`: frontend ownership, UI/state flow, request shaping, accessibility, frontend regressions
- `Rawls`: backend ownership, API/contract tracing, persistence semantics, router/service layering
- `Helmholtz`: docs, assets, config/governance drift, artifact sync

### Required subagent output

Each subagent should return:

1. Finding
2. Why it is a problem
3. Minimal fix proposal
4. Likely affected files
5. Risks if left unchanged
6. Suggested tests or validations
7. Confidence or uncertainty

## Collaboration Rules

1. **`.github/CODEOWNERS` is the source of truth** for default directory ownership.
- `AGENTS.md` defines operating rules and escalation, not the canonical path table.

2. **Treat shared-boundary files as explicit assignments.**
- Files such as `frontend/src/api/types.ts`, `docs/api/openapi.json`, `docs/api/api.llm.yaml`, `backend/application/ports.py`, and cross-layer tests must have a named owner for that task.

3. **Do not overlap edits** unless the Lead Agent explicitly assigns a shared boundary.

4. **Escalate contract drift immediately.**
- If frontend payloads, backend schemas, persistence behavior, and docs disagree, stop local optimization and report to the Lead Agent.

5. **Keep outputs structured.** Each assigned subagent should report:
- Scope worked on
- Files reviewed or likely affected
- Tests run or required
- Risks or follow-ups

6. **Prefer small, reviewable patches.**
- If a task spans layers, split into frontend, backend, and docs/assets sub-patches when practical.

7. **Use a single sync strategy.**
- `main` is responsible for rebasing onto `origin/main`.
- Owner branches should rebase onto `main`.
- Do not default to `git merge origin/main` inside owner threads.

8. **Gate merges through GitHub reviews and CI.**
- Required checks should block merges to `main`.
- Code owner review should be enabled for owned paths.
- The Lead Agent gives the final merge recommendation and release gate decision.

## Recommended Routing

- UI bug, hook bug, or settings issue -> **Frontend Owner**
- API validation, rename semantics, persistence bug, or contract semantics -> **Backend Owner**
- Docs, standards, release notes, prompts, or agent rules -> **Docs / Assets Owner**
- CI, ownership conflicts, shared-boundary arbitration, regression audit, or final merge readiness -> **Lead Agent**
