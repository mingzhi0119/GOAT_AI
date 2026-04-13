# Desktop Distribution Maturity Plan

Status: draft

This is a non-canonical working artifact.

## Slices

- Goal: land the feature-scoped spec, decision package, and task checklist
  before workflow and runbook changes move.
  - Main files: `docs/governance/specs/desktop-distribution-maturity/`;
    `docs/architecture/DESKTOP_DISTRIBUTION_MATURITY_DECISION_PACKAGE.md`
  - Risks: the repo could gain workflow changes without a durable statement of
    what is actually supported versus explicitly blocked
  - Validation: governance structure tests
  - Assumptions or decisions: macOS public release remains blocked until
    signing/notarization proof exists

- Goal: add Linux packaged-desktop workflow coverage, macOS blocker-report
  scaffolding, and readiness/runbook updates.
  - Main files: `.github/workflows/ci.yml`;
    `.github/workflows/desktop-provenance.yml`;
    `docs/operations/DESKTOP_DISTRIBUTION_READINESS.md`;
    `docs/operations/RELEASE_GOVERNANCE.md`;
    `docs/operations/OPERATIONS.md`
  - Risks: workflow docs can overstate support, or Linux packaging can drift
    from the repo's actual desktop build path
  - Validation: desktop governance tests and WSL Linux build parity commands
  - Assumptions or decisions: Linux packaging can be proven inside the repo;
    public macOS release cannot

- Goal: sync the landed facts and remaining blockers into roadmap/status/log
  truth once proof exists.
  - Main files: `docs/governance/ROADMAP.md`;
    `docs/governance/PROJECT_STATUS.md`;
    `docs/governance/codex-logs/2026-04.md`
  - Risks: roadmap/status can keep stale desktop maturity language if they are
    not updated in the same slice
  - Validation: governance path/log tests
  - Assumptions or decisions: Linux packaged CI/release scaffolding is a
    landed fact; public macOS distribution remains a blocker

## Integration notes

- Cross-layer boundaries: this slice is workflow/runbook/governance-only and
  should not widen frontend product promises.
- Contract refresh requirements: no OpenAPI change is expected.
- Doc/status sync requirements: if the Linux packaged path and readiness docs
  land, `ROADMAP.md` should narrow the remaining desktop blockers instead of
  leaving the broader pre-task wording in place.
