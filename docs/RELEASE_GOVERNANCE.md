# GOAT AI Release Governance

This document defines the minimum P1 release process for staging and production.

## Goals

- Keep releases reproducible and reviewable.
- Make staging deployment a standard workflow instead of a one-off terminal ritual.
- Require an explicit production approval step after staging has been exercised.

## Release flow

1. Run the normal CI gates on the target ref.
2. Trigger `.github/workflows/release-governance.yml` with the release ref.
3. Generate and retain a release manifest artifact for that ref.
4. Deploy the same ref to the `staging` environment.
5. Run `scripts/post_deploy_check.py` against staging.
6. Promote to `production` only through the `production` environment gate and after staging validation is green.

## Required GitHub environment setup

- `staging`
  - secrets: `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`, `STAGING_APP_DIR`
  - optional secrets: `STAGING_BASE_URL`, `STAGING_API_KEY`
- `production`
  - secrets: `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`, `PRODUCTION_APP_DIR`
  - optional secrets: `PRODUCTION_BASE_URL`, `PRODUCTION_API_KEY`

## Approval policy

- `staging` may be operator-triggered without a second approver.
- `production` should use GitHub Environment protection rules so the production job pauses for explicit approval.
- Do not bypass the environment approval by rerunning deploy commands manually on the host.

## Release manifest expectations

Each release workflow run should retain:

- requested release ref
- resolved commit SHA
- actor
- UTC timestamp
- staging / production job outcome

This is enough to answer "what exactly was deployed?" during rollback or incident review.

## Supply-chain provenance follow-on

P2 adds a separate provenance baseline workflow at
[`.github/workflows/desktop-provenance.yml`](../.github/workflows/desktop-provenance.yml).

That workflow currently covers the Linux desktop sidecar path by generating:

- the built desktop sidecar artifact
- a SHA-256 digest manifest
- an SPDX SBOM
- GitHub artifact attestations when the repository plan or repo variables permit it

If artifact attestations are not available for the repository plan, keep the digest
manifest and SBOM outputs as the minimum provenance record and enable attestations
later via the `ENABLE_GITHUB_ATTESTATIONS` repository variable when support is ready.

Signed public installers remain a later roadmap item; this provenance workflow is the
baseline that should exist before release-signing automation is considered complete.
