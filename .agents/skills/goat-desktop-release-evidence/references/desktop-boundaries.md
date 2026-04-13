# Desktop Proof Boundaries

Start from these workflow and doc truth sources:

- [ci.yml](../../../../.github/workflows/ci.yml)
- [desktop-provenance.yml](../../../../.github/workflows/desktop-provenance.yml)
- [fault-injection.yml](../../../../.github/workflows/fault-injection.yml)
- [RELEASE_GOVERNANCE.md](../../../../docs/operations/RELEASE_GOVERNANCE.md)
- [OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)

## Ownership split

- `desktop-package-windows`: packaged PR gate for CI-built binaries
- `desktop-provenance.yml`: signed release evidence and installed-artifact proof
- `fault-injection.yml`: recurring installed-desktop drill outside release ownership

Keep these three paths distinct in code, docs, and findings.
