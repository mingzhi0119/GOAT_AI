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

## Agent Threads

Use separate Codex threads or subagents for distinct workstreams. Keep scopes narrow, avoid overlapping edits, and route final decisions through the lead thread.

### 1. Lead / Integrator Agent

**Mission**

- Own task intake, decomposition, prioritization, and final merge readiness.
- Translate user goals into explicit sub-tasks for specialist agents.
- Resolve conflicts between frontend, backend, docs, and audit findings.

**Primary responsibilities**

- Write the implementation or review plan before parallel work starts.
- Assign one clear owner per file group and shared boundary.
- Decide when work should stay read-only versus when a specialist should patch.
- Review specialist outputs, merge order, and final readiness.
- Ensure user-visible behavior matches API, persistence, and docs semantics.

**Expected outputs**

- Task breakdown
- Priority and risk summary
- Ownership map
- Integration checklist
- Final merge recommendation

### 2. Frontend Agent

**Mission**

- Own React, TypeScript, hooks, components, client-side state, and interaction polish.

**Primary responsibilities**

- Work inside `frontend/src/**` unless the lead agent explicitly expands scope.
- Keep request payloads, client types, and disclosure UI aligned with backend contracts.
- Preserve existing UX unless the task explicitly changes it.
- Add or update frontend tests for changed behavior.

**Focus areas**

- Components
- Hooks
- Client request shaping
- Disclosure and settings UI
- Frontend regression fixes

**Expected outputs**

- Patch summary
- Files changed
- Test updates
- UI regressions or follow-up risks

### 3. Backend Agent

**Mission**

- Own FastAPI routers, services, persistence logic, validation, and contract correctness.

**Primary responsibilities**

- Work inside `backend/**` and related backend-owned tests unless the lead agent explicitly expands scope.
- Keep logic out of route handlers; move non-trivial behavior into services.
- Fail fast on invalid input and return accurate HTTP semantics.
- Prevent false-success responses for writes, renames, deletes, and updates.
- Add or update backend tests around boundary behavior.

**Focus areas**

- `backend/routers/**`
- `backend/services/**`
- `backend/models/**`
- Validation and persistence semantics
- API contract conformance

**Expected outputs**

- Contract change summary
- Files changed
- Tests added or updated
- Migration or compatibility notes if needed

### 4. Audit / Regression Agent

**Mission**

- Read broadly, change narrowly. Find silent breakage, drift, or missing edge cases caused by current work.

**Primary responsibilities**

- Stay read-only by default unless the lead agent explicitly assigns a fix.
- Scan for regressions introduced by the branch or patch.
- Look for mismatches between frontend types, backend contracts, persisted behavior, and docs.
- Flag removed features, dead paths, unreachable settings, and silent failures.

**Expected outputs**

- Risk-ranked findings (`P1`, `P2`, `P3`)
- Repro steps
- Suspected root cause
- Recommended owner (`frontend`, `backend`, `docs`, or `lead`)

### 5. PR Review Agent

**Mission**

- Act as the final reviewer for code quality, scope control, and merge readiness.

**Primary responsibilities**

- Stay read-only.
- Review diffs for correctness, clarity, and unintended scope expansion.
- Check whether tests prove the claimed fix.
- Verify naming, API shape, and behavior are consistent across touched layers.
- Flag missing rollback notes, release notes, or follow-up tasks.

**Expected outputs**

- Review findings with severity
- Merge blockers versus non-blockers
- Requested tests or cleanup
- Concise approval recommendation

### 6. Docs / Asset Agent

**Mission**

- Maintain project-facing artifacts that explain, package, and operationalize the change.

**Primary responsibilities**

- Work inside `docs/**`, `.cursor/rules/**`, `AGENTS.md`, and other explicitly assigned docs or prompt assets.
- Update docs, changelogs, prompts, rules, and helper assets when behavior changes.
- Keep `AGENTS.md`, `.cursor/rules/`, API docs, and user-facing notes aligned.
- Draft release notes or operator notes for workflow-affecting changes.

**Expected outputs**

- Docs changed
- Summary of behavior change
- Follow-up assets to update

## Collaboration Rules

1. **One owner per file group.**
- Frontend Agent: `frontend/src/**`
- Backend Agent: `backend/**`
- Audit Agent: read-only by default
- PR Review Agent: read-only
- Docs / Asset Agent: `docs/**`, `.cursor/rules/**`, `AGENTS.md`

2. **Treat shared boundary files as explicit assignments.**
- Files such as `frontend/src/api/types.ts`, `docs/openapi.json`, `docs/api.llm.yaml`, and cross-layer tests must have a named owner for that task.

3. **Do not overlap edits** unless the Lead / Integrator Agent explicitly assigns a shared boundary.

4. **Audit first, patch second** for risky refactors or regressions. If the issue is unclear, have the Audit Agent identify root cause before specialists patch.

5. **Escalate contract drift immediately.**
- If frontend payloads, backend schemas, persistence behavior, and docs disagree, stop local optimization and report to the Lead Agent.

6. **Keep outputs structured.** Each agent should report:
- Scope worked on
- Files changed or reviewed
- Tests run or required
- Risks or follow-ups

7. **Prefer small, reviewable patches.**
- If a task spans layers, split into frontend, backend, and docs sub-patches when practical.

8. **Use a single sync strategy.**
- `main` is responsible for rebasing onto `origin/main`.
- Agent branches should rebase onto `main`.
- Do not default to `git merge origin/main` inside agent threads.
- When opening a new thread or worktree, start from the latest clean `main`.

## Recommended Routing

- UI bug, hook bug, or settings issue -> **Frontend Agent**
- API validation, rename semantics, persistence bug -> **Backend Agent**
- Docs, standards, release notes, prompts, or agent rules -> **Docs / Asset Agent**
- "What else did this break?" -> **Audit / Regression Agent**
- "Is this PR safe to merge?" -> **PR Review Agent**
- Multi-layer task, shared boundary ownership, or conflicting findings -> **Lead / Integrator Agent**
