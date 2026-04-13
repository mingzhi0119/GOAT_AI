# Code Sandbox Runtime Follow-on Decision Package

Last updated: 2026-04-13

## Purpose

Record the compatibility, rollout, and blocker posture for the next code
sandbox runtime-control slice after the Docker-first MVP.

## Context

The shipped sandbox baseline already has durable execution rows, replayable log
chunks, provider-backed execution, and queued-execution recovery. The remaining
gap is control-plane predictability: running executions could not be cancelled,
abandoned `running` rows could survive a process restart, workspace scripts had
to infer their execution context, and the public contract still mentioned
network modes the runtime could not actually enforce.

A lightweight decision record is insufficient because this slice changes
operator-visible failure handling, contract truth, and rollout posture for the
current async runtime while also needing an explicit blocker statement for the
future Rust supervisor and allowlisted egress work.

## Fixed constraints

- do not add or rename public `/api/code-sandbox/*` endpoints for this slice
- keep retry terminal-only until side-effect and idempotency semantics are
  proven for running executions
- keep `network_policy=disabled` as the only public request contract until an
  enforced allowlisted egress boundary exists
- fail abandoned `running` executions closed on restart rather than pretending
  they can be resumed safely

## Decision

Adopt a Python-backed in-process supervisor seam as the immediate runtime bridge
for Phase 18 follow-on control:

1. providers receive a cooperative `cancel_requested()` callback
2. the cancel route now accepts visible `queued` and `running` executions
3. startup recovery replays `queued` work and marks abandoned `running`
   executions terminal with a restart-recovery event
4. sandbox workspaces receive a `.goat/workspace_manifest.json` file plus
   `GOAT_SANDBOX_*` environment variables for runtime introspection
5. the public request contract narrows to the only shipped network mode:
   `disabled`

This is a bridge decision, not the final supervision architecture. Real
allowlisted egress and the Rust supervisor remain explicitly blocked until they
have their own mechanical proof.

## Options considered

- Keep the queued-only control plane:
  - lowest change risk, but it leaves running executions stuck on restart and
    keeps cancellation semantics weaker than the roadmap requires
- Add a Python-backed supervisor seam now:
  - chosen because it improves cancellation and restart behavior without
    widening the API contract or pretending the Rust path already exists
- Jump straight to a Rust supervisor plus allowlisted egress:
  - rejected for this slice because the repo does not yet have the parity proof,
    packaging story, or enforcement evidence to land that safely in one step

## Compatibility strategy

- Read compatibility:
  - execution payload shape stays the same; new event types are additive
- Write compatibility:
  - `POST /api/code-sandbox/exec` request shape stays stable, but
    `network_policy` now truthfully accepts only `disabled`
  - `POST /cancel` keeps the same path and payload shape while widening
    behavior from queued-only to queued-or-running
- Downgrade behavior:
  - the current runtime can fall back to queued-only operational posture by
    removing the new supervisor/recovery path in a rollback commit; no storage
    migration is required
- Additive-first posture:
  - workspace manifest/env hints are additive runtime metadata, not a new HTTP
    contract surface

## Migration or rollout sequence

1. land the decision package and feature-scoped working artifacts
2. add the supervisor seam, provider cancellation callback, and running-cancel
   application flow
3. add restart recovery for abandoned `running` executions
4. land workspace manifest/runtime metadata hints and narrow generated contract
   truth to `network_policy=disabled`
5. sync API/runbook/roadmap/status/log docs after validation passes

## Rollback strategy

- rollback is code-only; no migration or data rewrite is required
- existing durable execution rows remain readable because the response shape and
  event persistence model stay intact
- if the new running-cancel path causes issues, operators can still rely on the
  existing restart-fail-closed posture to avoid stranded `running` rows
- rollback does not unlock new network modes; the disabled-only request contract
  remains the safe truth until allowlisted egress is proven

## Validation and proof

- Tests:
  - `__tests__/backend/application/test_application_code_sandbox.py`
  - `__tests__/backend/services/test_code_sandbox_execution_service.py`
  - `__tests__/backend/services/test_code_sandbox_provider.py`
  - `__tests__/backend/services/test_code_sandbox_runtime.py`
  - `__tests__/contracts/test_api_authz.py`
  - `__tests__/contracts/test_api_blackbox_contract.py`
  - governance and ops doc tests touched by the new spec/runbook surfaces
- Contracts or generated artifacts:
  - `docs/api/openapi.json`
  - `docs/api/api.llm.yaml`
  - `frontend/src/api/generated/openapi.ts`
  - `frontend/src/api/runtimeSchemas.ts`
- Workflow or runbook links:
  - `docs/api/API_REFERENCE.md`
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/INCIDENT_TRIAGE.md`
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`

## Open questions

- how to enforce a real allowlisted egress boundary mechanically without
  claiming support before supervisor-level proof exists
- when to replace the Python in-process seam with a Rust supervisor that proves
  success, failure, timeout, cancellation, and log replay parity
- whether future running-state retry semantics can be made safe without
  widening side effects or confusing lineage

## Related artifacts

- Roadmap item:
  - `docs/governance/ROADMAP.md`
- Status or operations docs:
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/INCIDENT_TRIAGE.md`
  - `docs/governance/codex-logs/2026-04.md`
- Related PRs or follow-ups:
  - Phase 18 allowlisted egress follow-on
  - Phase 18B Rust sandbox supervisor
