# Dry-Run Examples

## Example 1

User asks:
- "I changed `/api/system/features`; what contract surfaces have to move together?"

First moves:
- read [contract-surfaces.md](contract-surfaces.md), [change-checklist.md](change-checklist.md), and [blackbox-tests.md](blackbox-tests.md)
- inspect the backend schema and route source before touching generated artifacts
- decide whether [openapi.json](../../../../docs/api/openapi.json), [api.llm.yaml](../../../../docs/api/api.llm.yaml), [frontend generated types](../../../../frontend/src/api/generated/openapi.ts), and [frontend adapter types](../../../../frontend/src/api/types.ts) should move together

Validate with:
- run `python -m tools.contracts.check_api_contract_sync`
- run the relevant black-box and contract governance tests

## Example 2

User asks:
- "I refactored a backend route; do I actually need to regenerate OpenAPI?"

First moves:
- compare the request/response schema and authz-facing payload with the committed contract artifacts
- treat caller-scoped capability payloads as public contract, not internal-only implementation
- leave generated artifacts untouched if the external contract is unchanged

Validate with:
- prove either that no generated artifact changed or that all governed artifacts were refreshed together
