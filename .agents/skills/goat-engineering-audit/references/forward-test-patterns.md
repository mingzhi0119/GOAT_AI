# Forward-Tested Patterns

These patterns come from live repo tasks exercised against the current skill set. The checks listed below passed during the 2026-04-12 forward-test pass.

## Tasks exercised

- `goat-engineering-audit`: repo-native skill rollout readiness and governance coverage across [ROADMAP.md](../../../../docs/governance/ROADMAP.md), [AGENTS.md](../../../../AGENTS.md), [README.md](../../README.md), and [test_repo_local_skills.py](../../../../__tests__/governance/test_repo_local_skills.py)
- `goat-api-contract-proof`: caller-scoped `/api/system/features` contract review across [system_telemetry_service.py](../../../../backend/services/system_telemetry_service.py), [system.py](../../../../backend/models/system.py), [openapi.json](../../../../docs/api/openapi.json), and frontend contract artifacts
- `goat-ci-surface-router`: changed-file routing for telemetry/authz/observability and desktop workflow diffs
- `goat-desktop-release-evidence`: installed MSI/NSIS release proof review in [desktop-provenance.yml](../../../../.github/workflows/desktop-provenance.yml) plus desktop governance tests
- `goat-workbench-authz-proof`: caller-scoped workbench capability and gate-reason review across [feature_gates.py](../../../../goat_ai/config/feature_gates.py), [feature_gate_reasons.py](../../../../goat_ai/config/feature_gate_reasons.py), and `/api/system/features`
- `goat-observability-contract-proof`: label/query-shape review across [prometheus_metrics.py](../../../../backend/platform/prometheus_metrics.py), [approved-surfaces.md](../../goat-observability-contract-proof/references/approved-surfaces.md), and the observability asset contract
- `goat-governance-sync`: roadmap follow-on update after the live forward-test pass

## Checks exercised

- `python -m tools.contracts.check_api_contract_sync`
- `python -m pytest __tests__/contracts/test_api_authz.py __tests__/contracts/test_api_blackbox_contract.py __tests__/backend/services/test_system_telemetry_service.py -q`
- `python -m pytest __tests__/desktop/test_desktop_release_governance.py -q`
- `python -m pytest __tests__/ops/test_observability_asset_contract.py -q`
- `python -m pytest __tests__/governance/test_repo_local_skills.py __tests__/governance/test_structure_path_truth.py -q`

## Repeated prompt pattern

Use this when you want a read-only forward-test before any edit:

`Read-only review of <scope>. Start from the repo truth sources for this skill. Tell me what surfaces move together, what proof to run, whether the current behavior is a real regression or just out of scope, and do not edit files yet.`

## Repeated output pattern

Across the live tasks above, the most reusable output shape was:

1. `Scope`: what is in scope and what is intentionally out of scope
2. `Read-first truth`: the files or workflows that define current repo reality
3. `Coupled surfaces`: which files, generated artifacts, docs, workflows, or tests move together
4. `Minimum validation`: the narrowest checks that prove or clear the question
5. `Decision`: whether this is a real regression, a no-op, or a follow-on change
6. `Residual risk`: external blockers or proof gaps that still remain after the read-only pass

## Script decision

No shared script landed in this pass. The live forward-tests showed repeated friction in prompt framing and output structure, not in deterministic command synthesis. Keep strengthening shared examples and governance tests until a command sequence is rewritten often enough to justify a script.
