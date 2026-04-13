# Dry-Run Examples

## Example 1

User asks:
- "I added a label to a Prometheus metric; what observability proof do I need?"

First moves:
- read [observability-surfaces.md](observability-surfaces.md), [metric-label-policy.md](metric-label-policy.md), and [approved-surfaces.md](approved-surfaces.md)
- start from the exporter contract, then inspect alerts, dashboards, and runbook references
- check whether selectors or `sum by (...)` clauses now depend on the new label shape

Validate with:
- run [test_observability_asset_contract.py](../../../../__tests__/ops/test_observability_asset_contract.py) and the relevant backend observability tests

## Example 2

User asks:
- "I changed an alert query and a Grafana panel selector; what has to remain mechanically aligned?"

First moves:
- verify both directions: exported families and labels stay referenced by approved assets, and assets only query exported labels
- keep `.github/workflows/ci.yml` in scope when the change affects what `backend-heavy` must prove
- treat query-shape drift as a real regression, not a docs-only cleanup

Validate with:
- report whether the exporter, assets, runbooks, and CI proof path still agree on the changed selector surface
