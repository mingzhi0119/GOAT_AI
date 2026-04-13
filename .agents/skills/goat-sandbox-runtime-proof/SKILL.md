---
name: goat-sandbox-runtime-proof
description: Prove GOAT AI code-sandbox runtime behavior across supervisor seams, cancellation/retry semantics, egress policy, durable logs, and `/api/code-sandbox/*` contract truth. Use when sandbox runtime code, supervisor wiring, network-policy semantics, or sandbox ops docs change and the repo needs mechanical proof that safety boundaries still hold.
---

# GOAT Sandbox Runtime Proof

Use this skill when the change touches code-sandbox runtime behavior, supervisor
control, egress policy, or the governed sandbox contract/docs surface.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/sandbox-truth-sources.md](references/sandbox-truth-sources.md)
- [references/sandbox-checklist.md](references/sandbox-checklist.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for
  read-only supervisor, egress, and contract-proof prompts before editing the
  sandbox runtime.

## Workflow

1. Separate sandbox proof into four surfaces before diagnosing a regression:
   - policy/authz and caller-facing contract
   - runtime control plane (queue, running cancel, retry posture, recovery)
   - provider/supervisor behavior
   - operator docs and incident guidance
2. Start from the runtime truth sources, then trace outward to
   `/api/code-sandbox/*`, docs, and tests.
3. Treat running cancellation, restart recovery, network-policy semantics, and
   durable log replay as distinct proof surfaces.
4. When Linux parity is required from Windows, compose with
   [wsl-linux-ops-checks](../wsl-linux-ops-checks/SKILL.md) or
   [wsl-linux-build](../wsl-linux-build/SKILL.md) instead of substituting
   PowerShell-only proof.
5. When sandbox behavior changes the public contract or docs surface, compose
   with [goat-api-contract-proof](../goat-api-contract-proof/SKILL.md) and
   [goat-governance-sync](../goat-governance-sync/SKILL.md).

## Guardrails

- Do not treat queued-only and running-state control as the same proof surface.
- Do not widen `network_policy` semantics from `disabled` to allowlisted modes
  without real provider enforcement proof.
- Do not claim Rust supervisor parity from the current Python-backed seam.
- Do not mark sandbox docs or status as closed from intent alone; require the
  matching tests and contract proof.

## Validation

- Run the relevant sandbox runtime tests in `__tests__/backend/`.
- Include `__tests__/contracts/test_api_blackbox_contract.py` and
  `__tests__/contracts/test_api_authz.py` when caller-facing sandbox behavior or
  denial semantics move.
- Run `python -m tools.contracts.check_api_contract_sync` if
  `/api/code-sandbox/*` models, docs, or generated artifacts change.
- Re-run governance or ops-asset tests when sandbox docs or governance truth
  move with the code.
