# Approved Observability Surfaces

Approved surfaces are the operator-facing files that CI treats as governed observability assets:

- [ops/observability/alerts/goat-api-alerts.yml](../../../../ops/observability/alerts/goat-api-alerts.yml)
- [ops/observability/grafana/goat-api-dashboard.json](../../../../ops/observability/grafana/goat-api-dashboard.json)
- [docs/operations/OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [docs/operations/INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)

When one of these files changes, verify it still matches the exporter and the proof tests rather than assuming the prose is self-validating.
