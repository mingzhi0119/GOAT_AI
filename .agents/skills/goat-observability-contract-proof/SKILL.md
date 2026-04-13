---
name: goat-observability-contract-proof
description: Validate GOAT AI observability contracts across metrics, labels, approved alert/dashboard selectors, and ops runbooks. Use when metric export or operator-facing observability assets change and both family-level and label/query-shape proof must remain aligned.
---

# GOAT Observability Contract Proof

Use this skill when the change touches metrics, observability assets, or runbook references to those assets.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/observability-surfaces.md](references/observability-surfaces.md)
- [references/metric-label-policy.md](references/metric-label-policy.md)
- [references/approved-surfaces.md](references/approved-surfaces.md)

## Workflow

1. Start from the exporter contract, then inspect alerts, dashboards, and runbooks.
2. Treat family names and label/query shape as governed surfaces.
3. Verify both directions:
   - assets only reference exported families and labels
   - exported families remain represented by approved operational surfaces
4. Keep the CI proof path aligned with the actual observability tests in `backend-heavy`.

## Guardrails

- Do not treat dashboard or alert text as informal examples.
- Do not add or rename labels without checking selector and grouping drift.
- Do not stop at family-level proof when operator queries depend on labels.

## Validation

- Run [__tests__/ops/test_observability_asset_contract.py](../../../__tests__/ops/test_observability_asset_contract.py).
- Include the relevant backend observability tests when exporter behavior or OTel-enabled paths change.
- If the change alters the validation matrix, compose with [goat-ci-surface-router](../../goat-ci-surface-router/SKILL.md).

