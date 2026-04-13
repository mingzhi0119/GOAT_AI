# Desktop Distribution Maturity Spec

Status: draft

This is a non-canonical working artifact.

- `ROADMAP.md` owns planned work.
- `PROJECT_STATUS.md` owns landed facts.
- `AGENTS.md` and repo-local skills own the standing governance model.

## Summary

Harden desktop distribution maturity without overstating unsupported public
channels. The smallest successful slice is Linux packaged-desktop CI/release
scaffolding plus explicit prerequisite and diagnostics guidance, while macOS
public distribution stays blocked behind an explicit blocker-report path instead
of an implied promise.

## Scope

- In scope:
  - Linux packaged-desktop build/provenance workflow coverage alongside the
    existing Windows path
  - macOS packaged-desktop workflow scaffolding that emits a blocker report and
    refuses to represent the current repo as a ready public release path
  - runbook/readiness documentation for prerequisites, updater gating, and
    runtime diagnostics
  - governance sync for roadmap/status/log truth once the slice lands
- Out of scope:
  - shipping real macOS signing or notarization credentials
  - changing public app capabilities or frontend product promises
  - rewriting the desktop runtime bridge or local-native UX beyond the current
    distribution/readiness slice
  - retrofitting new Windows packaging semantics unrelated to this task

## Constraints

- Contract and source-of-truth boundaries:
  - do not widen public API contracts for desktop distribution work
  - do not claim public macOS support until signing/notarization proof exists
  - keep workflow/runbook truth aligned with `ROADMAP.md`,
    `PROJECT_STATUS.md`, and `CODEX_LOGS.md`
- Platform or environment constraints:
  - Linux-targeted build and packaging validation from this Windows host must
    run through the repo-local WSL skills, not plain PowerShell bash commands
  - desktop governance proof must stay aligned with the existing workflow
    tests and operations docs
- Existing governance surfaces that must stay authoritative:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`
  - `docs/architecture/DESKTOP_DISTRIBUTION_MATURITY_DECISION_PACKAGE.md`

## Acceptance

- Required behavior:
  - Linux packaged-desktop workflows produce retained bundle artifacts and
    packaged provenance instead of only sidecar proof
  - macOS packaged workflow scaffolding emits an explicit blocker report and
    does not silently masquerade as a supported public distribution path
  - release/readiness docs clearly explain prerequisites, updater gating, and
    startup/runtime diagnostic inputs
- Required validations:
  - desktop governance tests cover the workflow and runbook truth
  - Linux packaged build validation runs successfully through the WSL helper
    path with sidecar build, Tauri package build, provenance generation, and
    Rust tests
- Residual risks to keep visible:
  - public macOS signing/notarization still depends on external credentials,
    runner setup, and approval wiring outside repo-only proof
  - updater enablement remains intentionally disabled until a signed public
    release path is mechanically proven
