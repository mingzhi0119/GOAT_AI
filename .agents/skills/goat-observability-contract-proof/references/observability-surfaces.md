# Observability Surfaces

Exporter and assets:

- [backend/platform/prometheus_metrics.py](../../../../backend/platform/prometheus_metrics.py)
- [ops/observability/alerts/goat-api-alerts.yml](../../../../ops/observability/alerts/goat-api-alerts.yml)
- [ops/observability/grafana/goat-api-dashboard.json](../../../../ops/observability/grafana/goat-api-dashboard.json)
- [ops/observability/README.md](../../../../ops/observability/README.md)

Operator-facing docs:

- [OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)

Primary proof tests:

- [__tests__/ops/test_observability_asset_contract.py](../../../../__tests__/ops/test_observability_asset_contract.py)
- [__tests__/backend/platform/test_otel_tracing.py](../../../../__tests__/backend/platform/test_otel_tracing.py)
- [__tests__/backend/platform/test_backend_main_factory.py](../../../../__tests__/backend/platform/test_backend_main_factory.py)
