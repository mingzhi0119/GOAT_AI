# Code Sandbox Runtime Follow-ons Plan

Status: draft

This is a non-canonical working artifact.

## Slices

- Goal: land the feature spec, decision package, and governance pilot allow-list
  updates before runtime-control changes widen the sandbox implementation.
  - Main files: `docs/governance/specs/code-sandbox-runtime-follow-ons/`;
    `docs/architecture/CODE_SANDBOX_RUNTIME_FOLLOW_ON_DECISION_PACKAGE.md`;
    `docs/decisions/README.md`;
    `__tests__/governance/test_feature_spec_governance.py`
  - Risks: runtime-control behavior can land ahead of the governing decision and
    leave the repo without a durable blocker record
  - Validation: governance structure and decision-entrypoint tests
  - Assumptions or decisions: running retry, allowlisted egress, and Rust
    supervision stay explicitly out of scope for this slice

- Goal: add a process-local supervisor seam plus fail-closed startup recovery for
  durable sandbox executions.
  - Main files: `backend/services/code_sandbox_supervisor.py`;
    `backend/services/code_sandbox_execution_service.py`;
    `backend/application/code_sandbox.py`; `backend/platform/dependencies.py`;
    `backend/main.py`; `backend/services/code_sandbox_runtime.py`;
    `backend/services/code_sandbox_execution_store.py`
  - Risks: cancellation could acknowledge before the durable record is terminal,
    or restart recovery could leave stale `running` rows behind
  - Validation: targeted application/runtime/contract tests plus Ruff
  - Assumptions or decisions: cooperative cancellation through the current
    Python runtime is good enough until a Rust supervisor is proven

- Goal: improve workspace/runtime ergonomics without changing the public route
  surface.
  - Main files: `backend/services/code_sandbox_provider.py`;
    `backend/models/code_sandbox.py`; `backend/routers/code_sandbox.py`;
    `frontend/src/api/runtimeSchemas.ts`
  - Risks: docs or frontend parsing could still advertise unimplemented network
    modes, or workspace scripts could keep guessing paths
  - Validation: provider tests, contract sync, frontend contract/runtime checks
  - Assumptions or decisions: `.goat/workspace_manifest.json` and
    `GOAT_SANDBOX_*` environment variables are additive runtime hints rather
    than a new public API

- Goal: sync the narrowed remaining sandbox blockers into roadmap, status,
  operations, and Codex logs once the runtime slice is proven.
  - Main files: `docs/api/API_REFERENCE.md`; `docs/operations/OPERATIONS.md`;
    `docs/operations/INCIDENT_TRIAGE.md`; `docs/governance/ROADMAP.md`;
    `docs/governance/PROJECT_STATUS.md`;
    `docs/governance/codex-logs/2026-04.md`
  - Risks: roadmap/status can overstate Phase 18 as fully closed when the repo
    still lacks allowlisted egress and Rust supervision proof
  - Validation: contract sync, frontend gates, and governance/ops doc tests
  - Assumptions or decisions: only the runtime-control slice is landed; the
    remaining sandbox follow-ons stay open

## Integration notes

- Cross-layer boundaries: the API route surface stays stable; runtime behavior
  becomes more predictable through internal control seams and contract-truth
  narrowing, not through new endpoints.
- Contract refresh requirements: regenerate OpenAPI, LLM YAML, and frontend
  generated types because the sandbox request/response enum contract narrows and
  the cancel route documentation changes.
- Doc/status sync requirements: `ROADMAP.md` should keep only the unfinished
  sandbox items after this slice closes, and `PROJECT_STATUS.md` should record
  the landed running-cancel plus restart-recovery baseline without implying that
  allowlisted egress or Rust supervision are done.
