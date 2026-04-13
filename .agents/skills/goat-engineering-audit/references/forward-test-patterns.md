# Forward-Tested Patterns

These patterns come from live repo tasks exercised against the current skill set. The checks listed below passed during the 2026-04-12 forward-test pass.

## Tasks exercised

- `goat-engineering-audit`: repo-native skill rollout readiness and governance coverage across [ROADMAP.md](../../../../docs/governance/ROADMAP.md), [AGENTS.md](../../../../AGENTS.md), [README.md](../../README.md), and [test_repo_local_skills.py](../../../../__tests__/governance/test_repo_local_skills.py)
- `goat-api-contract-proof`: caller-scoped `/api/system/features` contract review across [system_telemetry_service.py](../../../../backend/services/system_telemetry_service.py), [system.py](../../../../backend/models/system.py), [openapi.json](../../../../docs/api/openapi.json), and frontend contract artifacts
- `goat-ci-surface-router`: changed-file routing for telemetry/authz/observability and desktop workflow diffs
- `goat-desktop-release-evidence`: installed MSI/NSIS release proof review in [desktop-provenance.yml](../../../../.github/workflows/desktop-provenance.yml) plus desktop governance tests
- `goat-workbench-authz-proof`: caller-scoped workbench capability and gate-reason review across [feature_gates.py](../../../../goat_ai/config/feature_gates.py), [feature_gate_reasons.py](../../../../goat_ai/config/feature_gate_reasons.py), and `/api/system/features`
- `goat-observability-contract-proof`: label/query-shape review across [prometheus_metrics.py](../../../../backend/platform/prometheus_metrics.py), [approved-surfaces.md](../../goat-observability-contract-proof/references/approved-surfaces.md), and the observability asset contract
- `goat-observability-contract-proof` + `goat-ci-surface-router` + `wsl-linux-build`: Linux-parity backend-heavy review across OTel enabled-path tests, observability asset proof, and WSL Python bootstrap behavior
- `goat-governance-sync`: roadmap follow-on update after the live forward-test pass

## Checks exercised

- `python -m tools.contracts.check_api_contract_sync`
- `python -m pytest __tests__/contracts/test_api_authz.py __tests__/contracts/test_api_blackbox_contract.py __tests__/backend/services/test_system_telemetry_service.py -q`
- `python -m pytest __tests__/desktop/test_desktop_release_governance.py -q`
- `python -m pytest __tests__/ops/test_observability_asset_contract.py -q`
- `python -m pytest __tests__/governance/test_repo_local_skills.py __tests__/governance/test_structure_path_truth.py -q`
- `powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "uname -a && bash -n ./ops/verification/phase0_check.sh && bash -n ./ops/verification/healthcheck.sh && bash -n ./ops/verification/watchdog.sh"`
- `python -m pytest __tests__/desktop/test_desktop_release_governance.py __tests__/ops/test_ops_asset_contracts.py -q`
- `cd frontend && npm run contract:check`
- `python -m pytest __tests__/contracts/test_frontend_contract_governance.py __tests__/contracts/test_generate_llm_api_yaml.py -q`
- `powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "bash ./.agents/skills/wsl-linux-build/scripts/run_python_ci.sh -- python -m pytest __tests__/backend/platform/test_otel_tracing.py __tests__/backend/platform/test_backend_main_factory.py __tests__/ops/test_observability_asset_contract.py -q"`

## Composed skill chains

- Linux parity from a Windows host:
  - `$goat-ci-surface-router` decides the diff really needs Linux parity
  - `$wsl-linux-ops-checks` or `$wsl-linux-build` executes the narrow WSL command
- Release workflow to runbook ownership:
  - `$goat-desktop-release-evidence` decides which desktop proof chain changed
  - `$goat-governance-sync` decides whether `RELEASE_GOVERNANCE.md`, `OPERATIONS.md`, or `INCIDENT_TRIAGE.md` owns the wording update
- Frontend-exposed contract change:
  - `$goat-api-contract-proof` keeps backend, docs, and frontend contract artifacts aligned
  - frontend contract checks prove the generated and hand-maintained frontend surfaces still match the backend contract
- Windows-hosted observability proof:
  - `$goat-observability-contract-proof` identifies the backend-heavy OTel and asset-contract path
  - `$goat-ci-surface-router` narrows the required Linux-parity checks
  - `$wsl-linux-build` runs [run_python_ci.sh](../../wsl-linux-build/scripts/run_python_ci.sh) so WSL can use a repo-specific virtualenv instead of the externally managed system Python

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

One minimal script landed in this pass: [run_python_ci.sh](../../wsl-linux-build/scripts/run_python_ci.sh). The Linux-parity observability forward-test exposed a real recurring friction point on WSL: the system Python is externally managed, but `backend-heavy` OTel and observability checks still need repo dependencies such as `ddgs`. The new helper creates a dedicated WSL virtualenv, installs `requirements-ci.txt` when needed, and then runs the requested Python command without asking future callers to rediscover the PEP 668 workaround.
