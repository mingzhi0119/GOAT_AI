# Project Memory And Connectors Foundation Spec

Status: draft

This is a non-canonical working artifact.

- `ROADMAP.md` owns planned work.
- `PROJECT_STATUS.md` owns landed facts.
- `AGENTS.md` and repo-local skills own the standing governance model.

## Summary

Land the first real runtime foundation for read-only `project_memory` and
connector-backed retrieval without widening public write capabilities. The
smallest successful slice is a caller-scoped source registry plus bounded
runtime execution path that can read project-scoped durable workspace outputs
and operator-provisioned connector bindings while concealing caller-invisible
sources.

## Scope

- In scope:
  - read-only `project_memory` source discovery and execution behind the
    existing `/api/workbench/*` boundary
  - read-only connector binding discovery backed by operator-provisioned JSON
    metadata, with tenant / principal / owner visibility
  - truthful `/api/workbench/sources` and `/api/system/features` runtime
    exposure for the current caller
  - runtime and contract proof that hidden connector bindings are concealed
    rather than advertised as denied
  - governance sync for roadmap, project status, API reference, domain terms,
    decision package, and Codex logs
- Out of scope:
  - write-capable connector flows or new connector write endpoints
  - external credential exchange, mutation-side authorization, or sync jobs
  - frontend promise widening beyond generated contract sync
  - shared runtime extraction that belongs to later follow-on work

## Constraints

- Contract and source-of-truth boundaries:
  - keep `/api/workbench/*` and `/api/system/features` endpoint shapes stable
  - do not add public write-capable connector or project routes in this slice
  - keep `connector_ids` as a deprecated alias rather than inventing a second
    request shape
  - keep invisible connector bindings concealed from callers who fail
    tenant / principal / owner visibility checks
- Platform or environment constraints:
  - backend validation must run on Python 3.14 with `requirements-ci.txt`
  - frontend validation is required because generated OpenAPI artifacts change
  - Linux-targeted packaging remains out of scope for this task
- Existing governance surfaces that must stay authoritative:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`
  - `docs/architecture/PROJECT_MEMORY_CONNECTORS_FOUNDATION_DECISION_PACKAGE.md`

## Acceptance

- Required behavior:
  - `/api/workbench/sources` lists a real read-only `project_memory` source for
    eligible callers and lists only the connector bindings visible to that
    caller
  - hidden connector bindings resolve as unknown / unavailable instead of a
    permission-denied leak
  - browse and deep-research tasks can execute against `project_memory` and
    visible read-only connectors without adding write capabilities
  - `/api/system/features` distinguishes read-scoped project-memory readiness
    from write-scoped connector task capability
- Required validations:
  - touched backend files pass `ruff check` and `ruff format --check`
  - source-registry, telemetry, execution, authz, and black-box contract tests
    cover happy path, concealment, and missing-project boundaries
  - generated OpenAPI artifacts and frontend types stay in sync
- Residual risks to keep visible:
  - connector bindings remain operator-provisioned static metadata rather than
    remote live adapters
  - write-capable connector authorization and durable credential handling remain
    future work
