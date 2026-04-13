# Dry-Run Examples

## Example 1

User asks:
- "I added a label to a Prometheus metric; what observability proof do I need?"

First moves:
- read [observability-surfaces.md](observability-surfaces.md), [metric-label-policy.md](metric-label-policy.md), and [approved-surfaces.md](approved-surfaces.md)
- start from the exporter contract, then inspect alerts, dashboards, and runbook references
- check whether selectors or `sum by (...)` clauses now depend on the new label shape

Expected output:
- which exported family or label surface changed
- which approved assets or runbooks would need to move with it
- the minimum observability proof path that would clear the change

Validate with:
- run [test_observability_asset_contract.py](../../../../__tests__/ops/test_observability_asset_contract.py) and the relevant backend observability tests

## Example 2

User asks:
- "I changed an alert query and a Grafana panel selector; what has to remain mechanically aligned?"

First moves:
- verify both directions: exported families and labels stay referenced by approved assets, and assets only query exported labels
- keep `.github/workflows/ci.yml` in scope when the change affects what `backend-heavy` must prove
- treat query-shape drift as a real regression, not a docs-only cleanup

Expected output:
- whether the drift is in the exporter, the asset, the runbook, or the CI proof path
- the approved surfaces affected by the query change
- the narrowest backend-heavy or asset-contract proof needed before editing

Validate with:
- report whether the exporter, assets, runbooks, and CI proof path still agree on the changed selector surface

## Example 3

User asks:
- "I changed OTel or observability proof paths on a Windows host; what Linux-parity check should I actually run for `backend-heavy`?"

First moves:
- compose with `goat-ci-surface-router` first so the answer stays scoped to the real `backend-heavy` proof path
- keep both OTel enabled-path tests and the observability asset contract in scope when the diff touches exporter or workflow truth
- prefer the WSL Python CI helper over ad hoc package installs if Ubuntu-side dependencies are required

Expected output:
- whether Linux parity is actually required for the current diff
- the narrowest WSL-backed OTel plus observability proof chain
- any bootstrap prerequisite that must happen before the proof command is trustworthy

Validate with:
- run `powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "bash ./.agents/skills/wsl-linux-build/scripts/run_python_ci.sh -- python -m pytest __tests__/backend/platform/test_otel_tracing.py __tests__/backend/platform/test_backend_main_factory.py __tests__/ops/test_observability_asset_contract.py -q"`
