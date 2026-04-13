# Runtime Platform Shared Foundations Decision Package

Status: accepted for implementation

## Context

Tasks 1 and 2 landed real browse/deep-research execution, project-memory reads,
and read-only connectors, but the underlying runtime truth still lived in three
different places:

- `workbench_source_registry.py` owned both catalog construction and authz/audit
- `system_telemetry_service.py` re-derived capability truth from visible
  sources with its own local predicates
- `workbench_research_runtime.py` hard-coded per-source execution branches
  inside the LangGraph step function

That shape worked, but it left Phase 17 shared foundations incomplete: new
sources or future runtime widening would have to keep touching multiple local
implementations before the frontend could safely trust the caller-scoped
runtime story.

## Decision

### 1. Extract a pure source catalog under the existing registry wrappers

`WorkbenchSourceDescriptor` and source-catalog construction move into a shared
module that is pure inventory and runtime-readiness assembly.

- The catalog still defines `web`, `knowledge`, `project_memory`, and operator
  connector bindings.
- `list_workbench_sources()` and `resolve_requested_sources()` remain the
  public compatibility wrappers that own authz, concealment, and audit events.
- Hidden sources stay hidden because the shared catalog does not perform authz.

### 2. Extract capability assembly from `/api/system/features`

The workbench capability matrix now assembles from shared caller-visible source
facts instead of service-local predicates.

- `workbench.browse` and `workbench.deep_research` depend on runnable visible
  sources for those task kinds.
- `workbench.project_memory` stays read-scoped and only becomes runnable when
  the caller can see a runnable `project_memory` source.
- `workbench.connectors` stays write-scoped even when read-scoped callers can
  list visible connector bindings through `/api/workbench/sources`.

### 3. Extract a narrow source-executor registry under LangGraph

The LangGraph runtime remains the orchestration root, but per-source execution
now resolves through a dedicated source-executor seam.

- The graph still owns plan creation, follow-up scheduling, synthesis, and
  durable task events.
- Source execution for `knowledge`, `web`, `project_memory`, and
  `connector:*` moves behind one executor registry and context bundle.
- The private legacy single-pass fallback remains available and unchanged as a
  rollback seam.

### 4. Do not widen frontend promises in this slice

This decision only completes the backend/shared-control-plane foundation.

- No new endpoints are added.
- No new feature keys are added.
- No frontend capability flags are widened solely because the internals are
  cleaner.

## Consequences

### Benefits

- shared source truth and shared capability truth now derive from the same
  caller-visible facts
- new source families have a clearer place to land without editing multiple
  unrelated services first
- LangGraph orchestration is easier to evolve without mixing source-specific
  retrieval code into the graph body

### Costs

- the runtime still carries workbench-specific model names because the public
  contract is intentionally unchanged in this slice
- the legacy fallback path remains separate from the LangGraph executor registry
- future remote connector or broader runtime-generic work still needs a later
  migration

## Rollout and rollback

- Rollout is additive-first and internal-only: wrappers and response models stay
  in place while the shared modules take over assembly.
- Rollback is safe because the shared modules sit under existing wrappers and
  the legacy single-pass retrieval path still exists for browse/deep-research.
- If a regression appears, the repo can keep the shared source catalog while
  reverting only the source-executor extraction without changing public API
  semantics.

## Proof requirements

- focused tests for the source catalog, capability surface, and source-executor
  registry
- existing source-registry, telemetry, workbench application, and execution
  tests
- caller-scoped black-box and authz tests for `/api/workbench/sources` and
  `/api/system/features`
- contract-sync proof even though generated artifacts remain unchanged
