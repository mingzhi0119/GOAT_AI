# Desktop Distribution Maturity Decision Package

Last updated: 2026-04-13

## Purpose

Record the rollout, blocker, and rollback posture for raising desktop
distribution maturity beyond the shipped Windows-only public path without
pretending that unsupported public macOS release automation already exists.

## Context

The repository already ships a Tauri desktop shell, a packaged Python sidecar,
and signed Windows release proof with installed smoke evidence. The remaining
gap is distribution maturity across non-Windows targets: Linux packaging needs
to be exercised and retained as part of CI/release proof, while macOS still
depends on signing/notarization inputs that are not mechanically available
inside the repository.

At the same time, desktop operators need a clearer prerequisite and diagnostic
story so packaged-shell failures are debuggable before a user resorts to source
builds or unsupported guesswork.

## Fixed constraints

- do not widen public API or frontend capability promises for this slice
- keep Windows public distribution proof intact and non-regressive
- run Linux-targeted packaging validation from Windows through the repo-local
  WSL helper chain
- do not claim public macOS distribution support until signing/notarization
  proof exists
- keep updater enablement gated until the signed public release flow is stable

## Decision

Adopt a two-track maturity posture:

1. **Linux:** promote Linux packaged-desktop proof into CI/release workflows by
   building the packaged desktop, retaining `.AppImage` and `.deb` artifacts,
   and writing packaged provenance beside them.
2. **macOS:** add a packaged workflow scaffold that can build and emit a
   structured blocker report, but keep public release blocked until signing,
   notarization, and runner-secret requirements are satisfied.

Document prerequisite installation, updater gating, and startup/runtime
diagnostics in a dedicated readiness runbook so operators and developers have a
single truth source for packaged-desktop expectations.

## Options considered

- Keep desktop proof Windows-only:
  - lowest short-term cost, but it leaves Linux packaging and macOS readiness
    ambiguous and keeps the roadmap item artificially broad
- Pretend Linux and macOS are both public-release ready now:
  - rejected because the repo cannot prove public macOS signing/notarization
    and should not turn a hoped-for path into status truth
- Delay all desktop maturity work until every platform can be public:
  - rejected because Linux packaged proof, readiness docs, and blocker reports
    provide useful operational value immediately

## Compatibility strategy

- Read compatibility:
  - existing desktop workflows and docs stay readable; new Linux/macOS workflow
    jobs are additive
- Write compatibility:
  - no public API or installer contract shape changes are required
- Downgrade behavior:
  - if Linux packaged artifacts regress, the repo can still rely on the
    existing Windows public path while the Linux additions are repaired
- Additive-first posture:
  - Linux packaged proof and macOS blocker reporting extend evidence coverage
    without removing the existing Windows release path

## Migration or rollout sequence

1. land the decision package and feature-scoped spec artifacts
2. extend CI and provenance workflows for Linux packaged builds and macOS
   blocker-report scaffolding
3. add readiness/runbook documentation for prerequisites, updater gating, and
   diagnostics
4. prove Linux packaging through the WSL helper path from this Windows checkout
5. update roadmap/status/log truth to reflect what is landed versus still
   externally blocked

## Rollback strategy

- workflow rollback can remove the new Linux/macOS jobs without affecting the
  existing Windows public packaging path
- readiness docs are additive and can be narrowed if a platform path regresses
- public macOS distribution remains blocked by default, so there is no public
  rollback burden for that channel in this slice

## Validation and proof

- Tests:
  - `__tests__/desktop/test_desktop_release_governance.py`
  - `__tests__/desktop/test_linux_sidecar_provenance.py`
  - `__tests__/ops/test_ops_asset_contracts.py`
  - `__tests__/governance/test_feature_spec_governance.py`
- Workflow or runbook links:
  - `.github/workflows/ci.yml`
  - `.github/workflows/desktop-provenance.yml`
  - `docs/operations/DESKTOP_DISTRIBUTION_READINESS.md`
  - `docs/operations/RELEASE_GOVERNANCE.md`
  - `docs/operations/OPERATIONS.md`
- Local execution proof:
  - WSL helper run for Linux package dependencies, sidecar build,
    `npm run desktop:build`, packaged provenance generation, and
    `cargo test --manifest-path frontend/src-tauri/Cargo.toml`

## Open questions

- what GitHub environment/secrets model should own public macOS signing and
  notarization when the external credentials become available
- whether updater activation should ship first on Windows-only signed releases
  or wait for a broader multi-platform signed posture

## Related artifacts

- Roadmap item:
  - `docs/governance/ROADMAP.md`
- Status or operations docs:
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/operations/DESKTOP_DISTRIBUTION_READINESS.md`
  - `docs/governance/codex-logs/2026-04.md`
- Related PRs or follow-ups:
  - task 4 sandbox/runtime follow-ons
  - future public macOS signing/notarization automation
