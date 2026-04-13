# Workbench LangGraph Research Decision Package

Last updated: 2026-04-13

## Purpose

Record the compatibility, rollout, and rollback posture for replacing the
single-pass workbench browse/deep-research runtime with a bounded
LangGraph-backed research loop.

## Context

The shipped workbench baseline already has durable tasks, event timelines,
runtime-ready `web` retrieval, knowledge retrieval, and caller-scoped source
visibility. The remaining gap is behavioral: `browse` and `deep_research`
still execute as one bounded retrieval pass. The roadmap explicitly calls for a
plan -> retrieve -> synthesize -> follow-up loop, but that widening must stay
behind the existing `/api/workbench/*` contract and must not weaken the
current authz/audit/event model.

## Fixed constraints

- do not add or rename public `/api/workbench/*` endpoints for this slice
- preserve durable task rows, task-event timelines, and caller-scoped source
  visibility
- keep project memory and connectors out of scope until their authz/runtime
  semantics are mechanically proven
- provide an operator rollback switch to the legacy retrieval runtime
- keep failure handling bounded and observable rather than silently widening to
  long-horizon autonomous behavior

## Decision

Adopt LangGraph as the primary internal runtime for `task_kind = browse` and
`task_kind = deep_research`, with the graph controlling four phases:

1. source resolution
2. bounded step planning
3. iterative retrieval plus follow-up scheduling
4. final synthesis

The graph remains internal to the backend service layer. The public product
contract stays the durable workbench task model already exposed by
`/api/workbench/*`.

The shipped implementation also keeps a private `GOAT_WORKBENCH_LANGGRAPH_ENABLED`
switch so operators can roll back to the legacy single-pass retrieval path
without changing callers or persisted task rows.

## Options considered

- Keep the current single-pass runtime:
  - lowest code risk, but it fails the roadmap goal and keeps deep research as
    a renamed evidence brief
- Add a custom hand-rolled loop without LangGraph:
  - feasible, but it leaves the repo without the chosen runtime seam for later
    task/runtime widening
- Expose a new public research runtime contract:
  - rejected because it would widen frontend/API semantics before the runtime
    and authz model are proven

## Compatibility strategy

- Read compatibility:
  - existing task polling, task events, source listing, and result payloads
    remain readable without schema changes
- Write compatibility:
  - task creation keeps the same request shape and source-resolution rules
- Downgrade behavior:
  - disabling the LangGraph path returns execution to the shipped legacy
    single-pass retrieval behavior
- Additive-first posture:
  - new event types are additive timeline detail, not contract breaks

## Migration or rollout sequence

1. land the decision package and feature-scoped working artifacts
2. add the LangGraph dependency and private runtime settings
3. land the multi-step research runtime behind the current workbench executor
4. prove behavior through service/runtime tests and governance sync
5. only after task-1 proof lands, update roadmap/status truth

## Rollback strategy

- the rollback lever is `GOAT_WORKBENCH_LANGGRAPH_ENABLED=false`
- rollback does not require storage or schema changes
- any tasks created before rollback remain readable because task/result/event
  payload shapes do not change
- timeline detail from already-executed LangGraph tasks remains durable history
  and is not rewritten

## Validation and proof

- Tests:
  - `__tests__/backend/services/test_workbench_execution_service.py`
  - `__tests__/backend/services/test_workbench_runtime.py`
  - `__tests__/backend/platform/test_dotenv_config.py`
  - governance sync tests for logs/path truth
- Contracts or generated artifacts:
  - no OpenAPI shape change required for this slice
- Workflow or runbook links:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`

## Open questions

- whether the future shared runtime foundation should keep using LangGraph
  directly or wrap it behind a narrower internal control-plane seam
- whether the upstream `langchain-core` Python 3.14 warning disappears in a
  later LangGraph stack release without repo-local suppression

## Related artifacts

- Roadmap item:
  - `docs/governance/ROADMAP.md`
- Status or operations docs:
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/codex-logs/2026-04.md`
- Related PRs or follow-ups:
  - task 2 project memory/connectors
  - task 6 shared runtime foundations
