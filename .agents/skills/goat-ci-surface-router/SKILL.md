---
name: goat-ci-surface-router
description: Route GOAT AI changes to the minimum required validation matrix. Use when deciding which local checks, CI-equivalent gates, and proof suites are required for a given change set based on touched files and workflow truth.
---

# GOAT CI Surface Router

Use this skill when the question is "what do we need to run for this change?"

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/ci-routing.md](references/ci-routing.md)
- [references/local-check-matrix.md](references/local-check-matrix.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for changed-file prompts that map to the minimum required validation matrix.

## Workflow

1. Identify touched files first.
2. Map those files to the repo's actual CI surfaces rather than guessing from subsystem names.
3. Keep the repo's documented gate ordering intact:
   - clear changed-file fast gates first
   - then move to heavier backend or frontend proof
   - then run desktop-specific or Linux-parity validation when the surface actually changed
4. When Linux parity is required from Windows, compose with the existing `wsl-*` skills instead of substituting PowerShell-only proof.

## Guardrails

- Do not send non-desktop-only changes through Windows desktop packaging gates.
- Do not skip black-box contract or observability proof when the change touches governed surfaces.
- Do not claim Linux parity from native Windows results for Linux-targeted checks.

## Output

- State the minimum required local validation matrix.
- Call out optional wider confidence checks separately.
- Name the workflow or gate each suggested check corresponds to.
