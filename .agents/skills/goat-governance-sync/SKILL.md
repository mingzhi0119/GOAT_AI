---
name: goat-governance-sync
description: Keep GOAT AI governance documents aligned with shipped repository reality. Use when implementation and tests prove a slice has landed or shifted, and the roadmap, project status, ops runbooks, or release governance docs may need coordinated updates without confusing unfinished work, shipped status, and external blockers.
---

# GOAT Governance Sync

Use this skill when the repository's documented governance state needs to catch up to proved implementation reality.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/doc-ownership-map.md](references/doc-ownership-map.md)
- [references/status-vs-roadmap-rules.md](references/status-vs-roadmap-rules.md)
- [references/governance-edit-checklist.md](references/governance-edit-checklist.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for read-only document-ownership triage before rewriting roadmap, status, or ops text.

## Workflow

1. Confirm the implementation and proof are already landed; do not write governance status from intent alone.
2. Decide which document owns the update:
   - unfinished work
   - shipped status
   - operational procedure
   - release governance
3. Keep repo-internal proof separate from external GitHub, runner, approval, or secret-based blockers.
4. Update only the docs that correspond to the proven change; do not broadcast the same statement everywhere.

## Guardrails

- Do not put shipped status into `ROADMAP.md` except as unfinished follow-on or remaining risk.
- Do not mark a slice as fully closed if its blocker still depends on unproven external conditions.
- Do not let runbooks drift from workflow or test truth.

## Validation

- Re-read the touched governance docs after editing them.
- Run the relevant governance or ops asset tests when doc truth is part of a governed surface.
- When the update depends on a proof path, compose with the matching repo-native proof skill first.
