# Runtime Platform Shared Foundations Spec

Status: draft

This is a non-canonical working artifact.

- `ROADMAP.md` owns planned work.
- `PROJECT_STATUS.md` owns landed facts.
- `AGENTS.md` and repo-local skills own the standing governance model.

## Summary

Close the remaining Phase 17 shared-foundations gap by lifting workbench source
inventory, caller-scoped capability assembly, and LangGraph source execution
out of service-local duplicate logic and into shared runtime seams. The
smallest successful slice keeps `/api/workbench/*` and `/api/system/features`
stable while making source truth, capability truth, and retrieval execution
compose from the same control-plane facts.

## Scope

- In scope:
  - extract a shared workbench source catalog and caller-visible source facts
    under the existing source-registry wrappers
  - extract shared workbench capability assembly under the existing
    `/api/system/features` response model
  - extract a narrow source-executor registry under the current LangGraph
    research runtime so orchestration and per-source execution no longer live in
    one function
  - add focused tests for the new shared module boundaries plus existing authz
    and black-box regression proof
  - sync roadmap, project status, domain terms, decision-entrypoint examples,
    API reference notes, and Codex logs
- Out of scope:
  - new endpoints, new capability keys, or broader frontend promise widening
  - replacing the legacy retrieval fallback with a new public contract
  - write-capable connectors, project-memory mutation, or remote live adapters
  - turning workbench runtime records into a generic cross-product runtime model

## Constraints

- Contract and source-of-truth boundaries:
  - keep `/api/workbench/sources` and `/api/system/features` response shapes
    stable
  - keep caller-scoped concealment semantics intact: hidden sources remain
    unknown/unavailable rather than newly denied
  - preserve the existing read/write/export capability split in
    `/api/system/features.workbench.*`
- Platform or environment constraints:
  - backend validation must run on Python 3.14 with `requirements-ci.txt`
  - no frontend contract regeneration is needed unless public schemas change
  - Linux packaging is out of scope for this task
- Existing governance surfaces that must stay authoritative:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`
  - `docs/architecture/RUNTIME_PLATFORM_SHARED_FOUNDATIONS_DECISION_PACKAGE.md`

## Acceptance

- Required behavior:
  - source inventory and capability discovery consume the same caller-visible
    source facts instead of separate service-local predicates
  - the LangGraph runtime delegates source execution through a dedicated
    source-executor seam while preserving the same durable event names and
    fallback behavior
  - hidden sources remain concealed and do not leak through
    `/api/system/features`
- Required validations:
  - touched backend files pass `ruff check` and `ruff format --check`
  - focused source-catalog, capability-surface, and source-executor tests pass
  - existing source-registry, telemetry, workbench application, execution,
    authz, and black-box contract tests stay green
  - API contract sync remains green even though generated artifacts do not need
    refresh
- Residual risks to keep visible:
  - the legacy single-pass fallback remains a compatibility seam rather than a
    fully shared runtime path
  - future remote connectors and broader frontend promises still need separate
    proof before widening
