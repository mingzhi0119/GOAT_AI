---
name: goat-api-contract-proof
description: Validate and maintain GOAT AI API contract surfaces. Use when backend schemas, OpenAPI artifacts, API docs, frontend generated types, or black-box contract tests may need to stay in sync as one governed surface.
---

# GOAT API Contract Proof

Use this skill for HTTP/API contract work in this repository.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/contract-surfaces.md](references/contract-surfaces.md)
- [references/change-checklist.md](references/change-checklist.md)
- [references/blackbox-tests.md](references/blackbox-tests.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for read-only contract-impact prompts before changing generated artifacts.

## Workflow

1. Decide whether the change affects an HTTP contract, not just internal implementation.
2. Inspect the backend schema or route source and the existing API reference before touching generated artifacts.
3. Keep these surfaces aligned when the contract changes:
   - backend response/request models
   - [docs/api/openapi.json](../../../docs/api/openapi.json)
   - [docs/api/api.llm.yaml](../../../docs/api/api.llm.yaml)
   - [frontend/src/api/generated/openapi.ts](../../../frontend/src/api/generated/openapi.ts)
   - [frontend/src/api/types.ts](../../../frontend/src/api/types.ts) when frontend-facing adapters change
4. Prove sync with the repo's contract commands and black-box tests before treating the work as complete.

## Guardrails

- Do not refresh generated contract files unless the underlying contract actually changed.
- Do not stop at OpenAPI regeneration if docs or frontend generated types are now stale.
- Treat authz-facing capability payloads as part of the API contract, not as internal-only details.

## Validation

- Run `python -m tools.contracts.check_api_contract_sync`.
- Run the relevant contract tests from `__tests__/contracts/`.
- For frontend-exposed contract changes, also run `cd frontend && npm run contract:check`.
