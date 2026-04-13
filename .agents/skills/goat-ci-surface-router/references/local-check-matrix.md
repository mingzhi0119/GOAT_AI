# Local Check Matrix

Use the narrowest matrix that still matches the touched governed surface.

## Common mappings

- Python backend/shared/tests touched:
  - `python -m ruff check <touched files>`
  - `python -m ruff format --check <touched files>` for formatting-sensitive Python
  - relevant pytest slice
- API contract surfaces touched:
  - `python -m tools.contracts.check_api_contract_sync`
  - relevant `__tests__/contracts/*`
  - `cd frontend && npm run contract:check` when generated frontend types are in play
- Frontend build, packaging, or generated types touched:
  - `cd frontend && npm ci && npm test -- --run`
  - `cd frontend && npm run build`
- Observability surfaces touched:
  - `__tests__/ops/test_observability_asset_contract.py`
- Desktop governance or tooling touched:
  - `__tests__/desktop/test_desktop_release_governance.py`
  - other desktop tests that match the changed tool or workflow

Use workflow truth, not subsystem instinct, to widen beyond this baseline.
