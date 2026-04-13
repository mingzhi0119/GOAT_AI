# Workbench Multi-step Research Spec

Status: draft

This is a non-canonical working artifact.

- `ROADMAP.md` owns planned work.
- `PROJECT_STATUS.md` owns landed facts.
- `AGENTS.md` and repo-local skills own the standing governance model.

## Summary

Replace the current single-pass browse/deep-research execution path with a
controlled multi-step research loop that stays behind the existing
`/api/workbench/*` contract. The smallest successful outcome is a durable
plan -> retrieve -> synthesize runtime with bounded follow-up steps, source
failure isolation, and visible event-timeline proof.

## Scope

- In scope:
  - internal LangGraph-backed orchestration for `task_kind = browse` and
    `task_kind = deep_research`
  - bounded step planning, retrieval iteration, synthesis, and follow-up
    scheduling behind the existing durable workbench task/runtime layer
  - private rollback control via settings, with legacy single-pass retrieval
    preserved as a fallback
  - timeline and boundary tests for happy path, intermediate-source failure
    isolation, step ceilings, and no-runnable-source behavior
  - governance sync for roadmap/status/log truth after the slice lands
- Out of scope:
  - new public endpoints or request/response shapes
  - connector or project-memory widening
  - human-in-the-loop UI or frontend-visible runtime rewrites
  - sandbox/runtime composition work that belongs to later tasks

## Constraints

- Contract and source-of-truth boundaries:
  - keep `/api/workbench/*` request and response shapes unchanged
  - preserve the durable workbench task/event/output persistence model
  - keep source visibility and authz behavior owned by the existing source
    registry and application layer
- Platform or environment constraints:
  - backend validation must run on Python 3.14 with `requirements-ci.txt`
  - Linux-targeted validation remains out of scope for this slice
- Existing governance surfaces that must stay authoritative:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`
  - `docs/architecture/WORKBENCH_LANGGRAPH_RESEARCH_DECISION_PACKAGE.md`

## Acceptance

- Required behavior:
  - `browse` and `deep_research` execute through a bounded multi-step runtime
    rather than a single retrieval pass
  - the runtime records plan, per-step retrieval, follow-up scheduling, and
    synthesis events in the durable task timeline
  - single-source provider failures can be isolated without dropping the whole
    task when another runnable source still succeeds
  - the runtime can fall back to the shipped legacy retrieval path when the
    operator disables the LangGraph path
- Required validations:
  - touched backend files pass `ruff check` and `ruff format --check`
  - targeted backend tests prove happy path, failure isolation, step ceilings,
    and no-runnable-source boundaries
  - governance tests keep roadmap/status/log structure aligned
- Residual risks to keep visible:
  - the LangGraph Python stack currently emits an upstream Python 3.14 warning
    from `langchain-core`
  - task 1 does not yet widen the shared runtime foundation to connectors or
    project memory; that remains follow-on work
