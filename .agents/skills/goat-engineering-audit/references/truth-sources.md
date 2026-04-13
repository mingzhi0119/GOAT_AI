# Audit Truth Sources

Start with these files before judging implementation status:

- [ROADMAP.md](../../../../docs/governance/ROADMAP.md)
- [PROJECT_STATUS.md](../../../../docs/governance/PROJECT_STATUS.md)
- [ENGINEERING_STANDARDS.md](../../../../docs/standards/ENGINEERING_STANDARDS.md)
- [OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)
- [RELEASE_GOVERNANCE.md](../../../../docs/operations/RELEASE_GOVERNANCE.md)
- [API_REFERENCE.md](../../../../docs/api/API_REFERENCE.md)
- [ci.yml](../../../../.github/workflows/ci.yml)

Read the implementation and tests only after the relevant truth source is clear.

## Common audit surfaces

- Desktop evidence: workflows under [`.github/workflows`](../../../../.github/workflows), `tools/desktop/*`, `__tests__/desktop/*`
- API and authz: `backend/application/*`, `backend/services/*`, `__tests__/contracts/*`
- Observability: `backend/platform/prometheus_metrics.py`, `ops/observability/*`, `__tests__/ops/*`
- Governance drift: `AGENTS.md`, `docs/governance/*`, `docs/operations/*`, `__tests__/governance/*`
