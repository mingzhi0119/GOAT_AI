# Project Memory And Connectors Foundation Decision Package

Status: accepted for implementation

## Context

Task 2 needs to make `project_memory` and connectors real enough that
`/api/workbench/sources` and `/api/system/features` stop advertising pure
placeholders, but it must do so without leaking hidden connector inventory or
back-dooring write-capable connector behavior into the public contract.

The repo already has:

- durable workbench workspace outputs that can be listed by `project_id`
- caller-scoped output authz for tenant and owner visibility
- a bounded browse / deep-research runtime behind `/api/workbench/*`
- a governed capability-discovery surface in `/api/system/features`

The repo does not yet have:

- a real `project_memory` retrieval source
- connector binding visibility semantics
- a read-only connector execution path
- truthful landed documentation for this foundation

## Decision

### 1. Project memory ships first as a read-only retrieval source

`project_memory` is implemented as a read-only source backed by
`WorkbenchTaskRepository.list_workspace_outputs_for_project(project_id)` plus
existing workspace-output authz filtering.

- No new storage model or write route is introduced.
- The source is discoverable through `/api/workbench/sources`.
- The runtime requires an explicit `project_id` when the source is requested.

### 2. Connectors ship first as operator-provisioned read-only bindings

Connector foundations are limited to static, operator-configured bindings loaded
from `GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON`.

- Each binding declares `source_id`, `display_name`, documents, and optional
  task-kind / capability / visibility metadata.
- Visibility can be constrained by tenant id, principal id, and legacy owner id.
- Bindings remain read-only and in-process; they do not call remote systems or
  persist credentials in this slice.

### 3. Hidden connector bindings are concealed, not denied

Connector visibility is treated as inventory concealment rather than as a public
permission error.

- `/api/workbench/sources` omits hidden bindings entirely.
- `resolve_requested_sources()` treats hidden bindings as
  `unknown_or_unavailable`.
- `/api/system/features` computes connector readiness only from the caller's
  visible sources.

### 4. Capability discovery stays split by read vs write semantics

- `workbench.project_memory` remains a read-scoped capability view and becomes
  runtime-ready only when the caller can see a runnable `project_memory` source.
- `workbench.connectors` remains a write-scoped capability view because using
  connector-backed retrieval inside a task still requires `workbench:write`.
- `/api/workbench/sources` stays read-scoped inventory and may show visible
  connector bindings even when `/api/system/features.workbench.connectors` is
  permission-denied for that caller.

### 5. Write-capable connector work is deferred

This slice does not introduce:

- connector mutation routes
- remote OAuth / credential exchanges
- connector-driven background sync
- export or write paths that bypass workbench authz

Those remain roadmap work and must prove separate authz, storage, rollback, and
operator runbook boundaries.

## Consequences

### Benefits

- lands real read-only project-memory and connector foundations without widening
  the public write surface
- reuses existing durable output ownership semantics instead of inventing a new
  project-memory store
- makes capability discovery truthful for the current caller

### Costs

- connector bindings are static seed data, not live adapters
- the runtime carries one more bounded source-dispatch seam until later shared
  runtime extraction
- project-memory retrieval depends on existing workspace-output quality rather
  than a dedicated memory index

## Rollout and rollback

- Rollout is additive-first: source inventory and runtime become available
  behind the existing agent-workbench gate.
- Operator rollback is safe by clearing
  `GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON` and/or disabling the LangGraph-backed
  research runtime.
- Existing `web` and `knowledge` behavior remains unchanged for callers that do
  not request the new sources.

## Proof requirements

- source-registry tests for visible, hidden, and scope-missing cases
- runtime tests for project-memory and connector citations
- caller-scoped black-box tests for `/api/workbench/sources` and
  `/api/system/features`
- contract sync for OpenAPI, API reference, and generated frontend types
