# Dry-Run Examples

## Example 1

User asks:
- "I touched `backend/services/system_telemetry_service.py` and `__tests__/ops/test_observability_asset_contract.py`; what is the minimum local matrix?"

First moves:
- read [ci-routing.md](ci-routing.md) and [local-check-matrix.md](local-check-matrix.md)
- map the touched files to the real CI gates instead of guessing from package names
- call out which checks are required because the change touches caller-scoped API or observability proof

Expected output:
- the minimum local validation matrix in fast-to-heavy order
- which suggested checks map to which CI jobs or proof gates
- which steps require WSL or platform-specific execution

Validate with:
- list the minimum local checks and the workflow or job each one stands in for

## Example 2

User asks:
- "I only changed `desktop-provenance.yml`; do I need the packaged Windows PR gate too?"

First moves:
- separate packaged validation, release provenance, and scheduled drill surfaces
- keep the repo's fast-to-heavy gate ordering intact
- recommend desktop-specific validation only for the path the change actually touched

Expected output:
- whether the packaged PR gate is in scope for the current diff
- the required desktop or backend-heavy checks, and which ones are optional
- a short explanation for every omitted gate so the no-run decision is auditable

Validate with:
- explain why each suggested check is required, optional, or out of scope for the current diff
