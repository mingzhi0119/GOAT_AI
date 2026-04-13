# Runtime Platform Shared Foundations Plan

Status: draft

This is a non-canonical working artifact.

## Slices

- Goal: land the Task 6 spec and decision package before moving more runtime
  logic into shared seams.
  - Main files: `docs/governance/specs/runtime-platform-shared-foundations/`;
    `docs/architecture/RUNTIME_PLATFORM_SHARED_FOUNDATIONS_DECISION_PACKAGE.md`;
    `docs/decisions/README.md`;
    `__tests__/governance/test_feature_spec_governance.py`
  - Risks: implementation can outpace the governance pilot and make the landed
    architecture harder to audit later
  - Validation: governance structure and decision-entrypoint tests
  - Assumptions or decisions: public endpoint shapes stay stable

- Goal: extract a shared source catalog plus caller-visible source facts under
  the existing registry wrappers.
  - Main files: `backend/services/workbench_source_catalog.py`;
    `backend/services/workbench_source_registry.py`;
    `backend/application/workbench_shared.py`
  - Risks: source concealment can regress if the shared helper starts doing
    authz instead of staying pure
  - Validation: source-catalog and source-registry tests plus Ruff
  - Assumptions or decisions: authz and audit remain in
    `workbench_source_registry.py`

- Goal: extract shared workbench capability assembly out of
  `system_telemetry_service`.
  - Main files: `backend/services/workbench_capability_surface.py`;
    `backend/services/system_telemetry_service.py`
  - Risks: read/write/export semantics can collapse into a single “enabled”
    bit, or hidden sources can leak through capability truth
  - Validation: capability-surface, telemetry, authz, and black-box tests
  - Assumptions or decisions: `/api/system/features` models remain unchanged

- Goal: extract a source-executor registry under the current LangGraph runtime.
  - Main files: `backend/services/workbench_research_source_executors.py`;
    `backend/services/workbench_research_runtime.py`
  - Risks: durable event wording/order or LangGraph failure isolation can drift
    while moving logic out of the graph function
  - Validation: source-executor and workbench-execution tests plus black-box
    contract proof
  - Assumptions or decisions: the graph stays the composition root and the
    legacy fallback remains intact

- Goal: sync roadmap/status/API-reference/domain truth once the shared seams are
  proven.
  - Main files: `docs/governance/ROADMAP.md`;
    `docs/governance/PROJECT_STATUS.md`; `docs/architecture/DOMAIN.md`;
    `docs/api/API_REFERENCE.md`; `docs/governance/codex-logs/2026-04.md`
  - Risks: roadmap can overstate future runtime work as complete, or status can
    claim frontend widening that has not happened
  - Validation: governance and structure tests
  - Assumptions or decisions: only the shared foundations slice moves out of
    the roadmap; later runtime follow-ons remain open

## Integration notes

- Cross-layer boundaries: source catalog is pure inventory; registry remains the
  caller-scoped authz/audit wrapper; telemetry remains the HTTP adapter over
  shared capability assembly; LangGraph remains the orchestration root over
  source executors.
- Contract refresh requirements: generated API artifacts stay unchanged unless a
  public schema changes; still run contract-sync proof because caller-scoped
  capability behavior is a governed API surface.
- Doc/status sync requirements: remove only the finished shared-foundations
  subsection from `ROADMAP.md` and leave 17B/17C/17E follow-ons open.
