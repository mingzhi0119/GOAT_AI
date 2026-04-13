# Workbench Multi-step Research Plan

Status: draft

This is a non-canonical working artifact.

## Slices

- Goal: record the decision package, feature spec, and task checklist before
  runtime changes land.
  - Main files: `docs/governance/specs/workbench-multi-step-research/`;
    `docs/architecture/WORKBENCH_LANGGRAPH_RESEARCH_DECISION_PACKAGE.md`
  - Risks: docs can drift from the actual runtime if they are not updated in
    the same slice as the implementation
  - Validation: governance structure and log tests
  - Assumptions or decisions: LangGraph stays an internal implementation detail
    behind `/api/workbench/*`

- Goal: add a bounded LangGraph-backed research runtime for `browse` and
  `deep_research` with a private rollback switch.
  - Main files: `backend/services/workbench_execution_service.py`;
    `backend/services/workbench_research_runtime.py`;
    `goat_ai/config/settings.py`; `requirements.txt`; `requirements-ci.txt`
  - Risks: event ordering or failure semantics could regress the current
    durable workbench contract
  - Validation: targeted backend service/runtime tests plus Ruff
  - Assumptions or decisions: legacy retrieval remains available when the new
    runtime is disabled or unavailable

- Goal: prove the new behavior through boundary tests and sync the governance
  truth once the slice is closed.
  - Main files: `__tests__/backend/services/test_workbench_execution_service.py`;
    `__tests__/backend/platform/test_dotenv_config.py`;
    `docs/governance/ROADMAP.md`; `docs/governance/PROJECT_STATUS.md`;
    `docs/governance/codex-logs/2026-04.md`
  - Risks: roadmap/status could overstate the slice if they move ahead of test
    proof
  - Validation: targeted pytest suites and governance tests
  - Assumptions or decisions: only task-1 facts move into status; later task
    foundations stay open in roadmap

## Integration notes

- Cross-layer boundaries: no frontend/runtime contract widening in this slice;
  workbench source visibility remains caller-scoped through the existing
  application/authz layer.
- Contract refresh requirements: no OpenAPI shape refresh required unless the
  public payload shape changes.
- Doc/status sync requirements: if task 1 closes, remove its active-priority
  roadmap entry and record the landed fact in `PROJECT_STATUS.md`.
