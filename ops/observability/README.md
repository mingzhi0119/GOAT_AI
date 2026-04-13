# Observability Assets

This directory keeps production-facing observability assets versioned in-repo so dashboards, alerts, and scrape config review alongside the code they describe.

## Contents

- `prometheus/goat-api-scrape.yml`: example scrape job for `GET /api/system/metrics`
- `alerts/goat-api-alerts.yml`: starter Prometheus alert rules for health, latency, and persistence failures
- `grafana/goat-api-dashboard.json`: starter Grafana dashboard for request volume, latency, retrieval quality, and feature-gate denials

## Update rules

- Keep metric names aligned with `backend/platform/prometheus_metrics.py` and `docs/operations/OPERATIONS.md`.
- `backend/platform/prometheus_metrics.py::EXPORTED_METRIC_FAMILIES` and `EXPORTED_METRIC_LABELS` are the canonical metric contract; alerts, dashboards, and runbooks are mechanically verified against both the exported families and the governed label/query shape in CI.
- CI now checks both directions: observability assets cannot reference non-exported metric families, and every exported metric family must appear in at least one approved alert, dashboard, or runbook surface.
- When adding or renaming an operator-facing metric, update the relevant dashboard and alert rules in the same change.
- Treat these files as release assets, not ad hoc examples.
