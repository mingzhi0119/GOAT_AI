---
name: goat-workbench-authz-proof
description: Prove caller-scoped workbench and authz behavior in GOAT AI. Use when workbench scopes, source visibility, runtime readiness, deny reasons, or `/api/system/features` capability discovery may widen, drift, or need explicit proof.
---

# GOAT Workbench Authz Proof

Use this skill when the change touches workbench authorization, source visibility, or caller-scoped capability surfaces.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/authz-truth-sources.md](references/authz-truth-sources.md)
- [references/caller-scoped-checklist.md](references/caller-scoped-checklist.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for read-only caller-scoped authz review patterns before changing scopes or capability payloads.

## Workflow

1. Read the current scope and capability model before interpreting a failing test as either a bug or intended narrowing.
2. Trace the change across:
   - policy/scopes
   - source visibility
   - runtime readiness
   - caller-scoped API payloads
3. Treat `/api/system/features` as a governed capability discovery surface, not a convenience summary.
4. Verify that read, write, and export semantics stay distinct where the repo already models them separately.
5. Use black-box contract tests as the proof surface for future-widening prevention.

## Guardrails

- Do not infer authz semantics from frontend behavior alone.
- Do not collapse source visibility, runtime readiness, and permission denial into one bucket.
- Do not widen UI promises if the caller-scoped backend contract is still denied or not implemented.

## Validation

- Run the relevant black-box contract tests in `__tests__/contracts/`.
- Add service-level tests when the logic depends on source registry or system feature assembly.
- If the change also affects public API shape, compose with [goat-api-contract-proof](../goat-api-contract-proof/SKILL.md).
