# Project Memory And Connectors Foundation Plan

Status: draft

This is a non-canonical working artifact.

## Slices

- Goal: land the required feature spec, decision package, and governance pilot
  allow-list before runtime changes expand the workbench surface.
  - Main files: `docs/governance/specs/project-memory-connectors-foundation/`;
    `docs/architecture/PROJECT_MEMORY_CONNECTORS_FOUNDATION_DECISION_PACKAGE.md`;
    `docs/decisions/README.md`;
    `__tests__/governance/test_feature_spec_governance.py`
  - Risks: the slice can violate the admission gate if implementation lands
    ahead of the spec or decision package
  - Validation: governance structure and decision-entrypoint tests
  - Assumptions or decisions: write-capable connectors remain explicitly out of
    scope

- Goal: add a read-only project-memory and connector source inventory with
  caller-scoped concealment and truthful runtime metadata.
  - Main files: `backend/services/workbench_source_registry.py`;
    `backend/services/authorizer.py`;
    `backend/services/system_telemetry_service.py`;
    `goat_ai/config/settings.py`; `goat_ai/shared/workbench_connector_bindings.py`
  - Risks: visible inventory can drift from runtime reality or leak hidden
    connector bindings
  - Validation: source-registry, telemetry, dotenv-config, and authz contract
    tests plus Ruff
  - Assumptions or decisions: connector bindings come from operator config and
    remain read-only

- Goal: wire the new sources into the bounded workbench runtime without
  changing the existing route surface.
  - Main files: `backend/application/workbench.py`;
    `backend/services/workbench_execution_service.py`;
    `backend/services/workbench_research_runtime.py`;
    `backend/services/workbench_readonly_retrieval.py`
  - Risks: source inventory may say "ready" while the runtime still skips the
    source, or project memory may run without an explicit project scope
  - Validation: targeted runtime and application tests plus black-box contract
    proof
  - Assumptions or decisions: `project_memory` requires an explicit `project_id`

- Goal: sync API/governance truth after the read-only foundation is proven.
  - Main files: `docs/api/API_REFERENCE.md`; `docs/api/openapi.json`;
    `docs/api/api.llm.yaml`; `frontend/src/api/generated/openapi.ts`;
    `docs/governance/ROADMAP.md`; `docs/governance/PROJECT_STATUS.md`;
    `docs/architecture/DOMAIN.md`; `docs/governance/codex-logs/2026-04.md`
  - Risks: roadmap/status can overstate future write-capable work as already
    finished
  - Validation: contract sync, frontend gates, and governance tests
  - Assumptions or decisions: only the read-only foundation moves into landed
    status; write-capable connector work stays on the roadmap

## Integration notes

- Cross-layer boundaries: inventory is read-scoped; task creation remains
  `workbench:write`-gated; `/api/system/features.workbench.project_memory`
  remains a read-scoped capability view while `connectors` remains write-scoped.
- Contract refresh requirements: regenerate OpenAPI, LLM YAML, and frontend
  generated types if source enums or source inventory semantics change.
- Doc/status sync requirements: once the slice closes, remove only the finished
  read-only foundation work from active roadmap sections and leave write-capable
  connector follow-ons open.
