# Observability Assets

This directory keeps production-facing observability assets versioned in-repo so dashboards, alerts, and scrape config review alongside the code they describe.

## Contents

- `prometheus/goat-api-scrape.yml`: example scrape job for `GET /api/system/metrics`
- `alerts/goat-api-alerts.yml`: starter Prometheus alert rules for health, latency, and persistence failures
- `grafana/goat-api-dashboard.json`: starter Grafana dashboard for request volume, latency, retrieval quality, and feature-gate denials

## Update rules

- Keep metric names aligned with `backend/prometheus_metrics.py` and `docs/operations/OPERATIONS.md`.
- When adding or renaming an operator-facing metric, update the relevant dashboard and alert rules in the same change.
- Treat these files as release assets, not ad hoc examples.
