---
name: goat-desktop-release-evidence
description: Audit and validate GOAT AI desktop proof chains across packaged PR validation, signed release evidence, and recurring installed-desktop drills. Use when desktop workflows, tools, or docs change and MSI/NSIS evidence boundaries or retention need to stay mechanically governed.
---

# GOAT Desktop Release Evidence

Use this skill when the task touches desktop packaging, release evidence, or installed-desktop drills.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [references/desktop-boundaries.md](references/desktop-boundaries.md)
- [references/evidence-checklist.md](references/evidence-checklist.md)
- [references/retention-and-summary.md](references/retention-and-summary.md)
- [references/dry-run-examples.md](references/dry-run-examples.md)

## Dry-Run Examples

- See [references/dry-run-examples.md](references/dry-run-examples.md) for packaged-vs-installed-vs-drill prompt patterns before you conclude a desktop slice regressed.

## Workflow

1. Separate the three governed desktop proof paths before reasoning about failures:
   - packaged PR validation
   - release provenance and installed evidence
   - recurring installed-desktop drill
2. Verify workflow boundaries in docs and tests before concluding a capability is landed.
3. Treat MSI and NSIS as dual installed-artifact paths; failure-state evidence still needs to remain diagnosable.
4. Use the desktop tests and runbooks as proof, not just workflow text.
5. When Linux desktop parity is required from Windows, compose with [wsl-linux-rust-desktop](../wsl-linux-rust-desktop/SKILL.md).

## Guardrails

- Do not treat packaged CI-binary smoke as proof of installed release artifacts.
- Do not mix release evidence and scheduled drill ownership.
- Do not sign off a desktop governance change unless retention, summary shape, and workflow/docs/tests remain aligned.

## Validation

- Run the narrowest relevant tests under `__tests__/desktop/`.
- For workflow-shape or retention changes, include [test_desktop_release_governance.py](../../../__tests__/desktop/test_desktop_release_governance.py).
- For tool changes, include the matching packaged or installed smoke tests.
