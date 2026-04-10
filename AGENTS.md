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
- Directory ownership lives in [`.github/CODEOWNERS`](.github/CODEOWNERS)

## Agent Threads

Use four long-lived Codex owner threads for parallel work. Each owner thread should keep a dedicated branch and worktree. Keep scopes narrow, avoid overlapping edits, and route final decisions through the lead thread.

### 1. Lead / Platform Owner

**Mission**

- Own task intake, decomposition, repository governance, and final merge readiness.
- Translate user goals into explicit sub-tasks for the frontend, backend, and docs/assets owner threads.
- Arbitrate shared-boundary work, release gating, and project direction when owners disagree.

**Primary responsibilities**

- Write the implementation or review plan before parallel work starts.
- Assign one clear owner per shared-boundary task.
- Review specialist outputs, merge order, and final readiness.
- Own CI and governance changes under `.github/**` unless a boundary is explicitly shared.
- Give the final merge recommendation after required owner reviews and checks pass.
- Run read-only audit or PR-review passes directly, or assign them as temporary tasks instead of keeping separate long-lived owner threads.

### 2. Frontend Owner

**Mission**

- Own React, TypeScript, hooks, components, client request shaping, and frontend tests.

**Primary responsibilities**

- Work inside the paths assigned to the frontend lane in `.github/CODEOWNERS`.
- Keep request payloads, client types, and disclosure UI aligned with backend contracts.
- Preserve existing UX unless the task explicitly changes it.
- Add or update frontend tests for changed behavior.

### 3. Backend Owner

**Mission**

- Own FastAPI routers, services, persistence logic, validation, contract correctness, and backend tests.

**Primary responsibilities**

- Work inside the paths assigned to the backend lane in `.github/CODEOWNERS`.
- Keep logic out of route handlers; move non-trivial behavior into services.
- Fail fast on invalid input and return accurate HTTP semantics.
- Prevent false-success responses for writes, renames, deletes, and updates.
- Add or update backend tests around boundary behavior.

### 4. Docs / Assets Owner

**Mission**

- Maintain project-facing artifacts that explain, package, and operationalize the change.

**Primary responsibilities**

- Work inside the docs/assets lane in `.github/CODEOWNERS`.
- Update docs, changelogs, prompts, rules, and helper assets when behavior changes.
- Keep `AGENTS.md`, `.cursor/rules/`, API docs, and user-facing notes aligned.
- Draft release notes or operator notes for workflow-affecting changes.

## Collaboration Rules

1. **`.github/CODEOWNERS` is the source of truth** for default directory ownership.
- `AGENTS.md` defines operating rules and escalation, not the canonical path table.

2. **Treat shared-boundary files as explicit assignments.**
- Files such as `frontend/src/api/types.ts`, `docs/openapi.json`, `docs/api.llm.yaml`, `backend/application/ports.py`, and cross-layer tests must have a named owner for that task.

3. **Do not overlap edits** unless the Lead / Platform Owner explicitly assigns a shared boundary.

4. **Escalate contract drift immediately.**
- If frontend payloads, backend schemas, persistence behavior, and docs disagree, stop local optimization and report to the Lead / Platform Owner.

5. **Keep outputs structured.** Each owner thread should report:
- Scope worked on
- Files changed or reviewed
- Tests run or required
- Risks or follow-ups

6. **Prefer small, reviewable patches.**
- If a task spans layers, split into frontend, backend, and docs/assets sub-patches when practical.

7. **Use a single sync strategy.**
- `main` is responsible for rebasing onto `origin/main`.
- Owner branches should rebase onto `main`.
- Do not default to `git merge origin/main` inside owner threads.
- When opening a new thread or worktree, start from the latest clean `main`.

8. **Gate merges through GitHub reviews and CI.**
- Required checks should block merges to `main`.
- Code owner review should be enabled for owned paths.
- The Lead / Platform Owner gives the final merge recommendation and release gate decision.

## Recommended Routing

- UI bug, hook bug, or settings issue -> **Frontend Owner**
- API validation, rename semantics, persistence bug, or contract semantics -> **Backend Owner**
- Docs, standards, release notes, prompts, or agent rules -> **Docs / Assets Owner**
- CI, ownership conflicts, shared-boundary arbitration, or final merge readiness -> **Lead / Platform Owner**
