# Dry-Run Examples

## Example 1

User asks:
- "We changed running cancellation and supervisor wiring; what proof do we need before saying sandbox control is still safe?"

First moves:
- read [sandbox-truth-sources.md](sandbox-truth-sources.md) and
  [sandbox-checklist.md](sandbox-checklist.md)
- separate application routing, execution-service state changes, and
  supervisor/provider behavior
- confirm whether the change touches queued-only control, running cancellation,
  or restart recovery

Expected output:
- which sandbox control surface moved
- the exact backend and contract tests that prove the behavior
- whether any sandbox docs or API truth also need to move

Validate with:
- run the matching sandbox backend tests and the relevant
  `__tests__/contracts/` proof

## Example 2

User asks:
- "The code mentions allowlisted egress now; is that a real landed capability or still future work?"

First moves:
- inspect the provider enforcement path, the public `network_policy` contract,
  and the operator docs together
- avoid treating config names or TODOs as proof of enforcement
- confirm whether the current runtime actually enforces allowlisted egress

Expected output:
- whether allowlisted egress is landed, partial, or still roadmap-only
- the exact files or tests that prove that classification
- which docs should stay blocked if enforcement is not yet real

Validate with:
- include `python -m tools.contracts.check_api_contract_sync` if the public
  contract moved, plus the relevant sandbox/backend proof tests

## Example 3

User asks:
- "We edited sandbox runtime code plus ops docs; which proof skill should we compose before updating roadmap or status text?"

First moves:
- confirm the runtime and contract proof is already landed
- compose with `goat-api-contract-proof` if `/api/code-sandbox/*` truth moved
- compose with `goat-governance-sync` only after the proof surface is green

Expected output:
- whether the change is runtime-only, contract-bearing, or governance-bearing
- the exact validation matrix before doc edits are safe
- which docs should move and which ones should stay untouched

Validate with:
- rerun the relevant sandbox tests and the narrow governance/ops-asset tests for
  any touched doc surface
