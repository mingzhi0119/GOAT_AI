# GOAT AI Release Governance

This document defines the minimum artifact-first release process for staging and production.

## Goals

- Build the release payload once in CI and promote the same immutable bundle through staging and production.
- Keep release evidence reviewable without needing host-side forensics.
- Preserve an explicit rollback target for each environment promotion.

## Release flow

1. Run the normal CI gates on the target ref.
2. Trigger `.github/workflows/release-governance.yml` with the release ref.
3. Build one `release-bundle.tar.gz` plus one `release-manifest.json` for that ref.
4. Deploy the same bundle and manifest to `staging`.
5. Run `tools/ops/post_deploy_check.py` against staging.
6. Emit `staging-promotion-evidence.json` with environment, digest, resolved SHA, and rollback target.
7. Promote the same retained bundle to `production` only through the `production` environment gate.
8. Emit `production-promotion-evidence.json` after the production contract check passes.

## Required GitHub environment setup

- `staging`
  - secrets: `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`, `STAGING_APP_DIR`, `STAGING_BASE_URL`
  - optional secrets: `STAGING_API_KEY`, `STAGING_OWNER_ID`
- `production`
  - secrets: `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`, `PRODUCTION_APP_DIR`, `PRODUCTION_BASE_URL`
  - optional secrets: `PRODUCTION_API_KEY`, `PRODUCTION_OWNER_ID`

## Approval policy

- `staging` may be operator-triggered without a second approver.
- `production` should use GitHub Environment protection rules so the production job pauses for explicit approval.
- Do not bypass the environment approval by manually copying source or rebuilding the frontend on the host.

## Release artifact expectations

Each workflow run retains:

- the requested release ref
- the resolved commit SHA
- the actor and UTC timestamp
- one immutable `release-bundle.tar.gz`
- the bundle SHA-256 digest
- per-environment promotion evidence JSON

The deploy scripts preserve the latest deployed `release-manifest.json` under the project root and keep the prior one as `release-manifest.previous.json` so operators can identify the immediate rollback target without additional host inspection.

## Manual artifact deployment

The workflow is the default release path, but the same deploy scripts support manual artifact promotion when required:

- canonical checked-in deploy assets live under `ops/deploy/`

Linux:

```bash
PROJECT_DIR=/srv/goat-ai \
RELEASE_BUNDLE=/tmp/release-bundle.tar.gz \
RELEASE_MANIFEST=/tmp/release-manifest.json \
EXPECTED_GIT_SHA=<resolved-sha> \
bash ops/deploy/deploy.sh
```

Windows PowerShell:

```powershell
.\ops\deploy\deploy.ps1 -ProjectDir C:\GOAT_AI -ReleaseBundle C:\temp\release-bundle.tar.gz -ReleaseManifest C:\temp\release-manifest.json -ExpectedGitSha <resolved-sha>
```

## Desktop release flow

Desktop release governance now uses a separate provenance workflow at
[`.github/workflows/desktop-provenance.yml`](../../.github/workflows/desktop-provenance.yml).

That workflow covers:

- the Linux desktop sidecar path by generating:
  - the built desktop sidecar artifact
  - a Linux desktop sidecar provenance record
  - an SPDX SBOM
  - GitHub artifact attestations when the repository plan or repo variables permit it
- the signed Windows desktop release path by generating:
  - real packaged `.msi` and NSIS installers
  - an installer provenance manifest with digests and signature status
  - GitHub artifact attestations for the shipped installers when supported

The signed Windows desktop release path is the default public-distribution path.
Manual or local unsigned desktop builds remain internal/test-only artifacts.

Desktop release steps:

1. Trigger `.github/workflows/desktop-provenance.yml` from a release tag or manual dispatch.
2. Build the Linux desktop sidecar and write its provenance record with `python -m tools.desktop.write_linux_sidecar_provenance`.
3. Build real Windows packaged installers from the same requested ref.
4. Sign the Windows installers when `distribution_channel=public` (the tag path always requires this).
5. Run `python -m tools.desktop.installed_windows_desktop_fault_smoke` against both the signed MSI and NSIS installers, continuing to the second installer even if the first one fails, and retain the installed-app evidence bundle.
6. Write `desktop-windows-provenance.json` with artifact digests and signature status.
7. Upload the installers plus provenance assets and installed-smoke evidence, then emit installer attestations when supported.

The installed Windows evidence bundle should retain `desktop-installed-smoke/*/summary.json`
even when install, startup, or uninstall fails. That summary is the audit entrypoint
for installer kind, installer digest, install root, resolved SHA, distribution channel,
healthy launch status, partial scenario results, uninstall outcome, and any retained
`primary_failure_phase` / `primary_failure_error` fields when uninstall failure is
not the first fault.

The installed evidence order is fixed: install, healthy launch, health/ready proof,
controlled shutdown, pre-ready fault scenarios, then uninstall. The healthy launch
step runs with isolated appdata, a reserved localhost backend port, preserved shell
logs, and `GOAT_READY_SKIP_OLLAMA_PROBE=1` so release evidence proves the installed
desktop can reach the backend-ready baseline without making local Ollama availability
part of the gate.

Signed Windows installer provenance and Linux sidecar provenance are necessary release evidence, but they are not sufficient proof that pre-ready desktop startup still fails closed. Desktop-related changes must also keep the merge-blocking `desktop-package-windows` packaged-shell fault smoke green for missing-sidecar, early-exit-before-ready, and health-timeout paths.

The workflow boundaries stay distinct:

- `desktop-package-windows`: merge-blocking packaged-binary smoke for CI-built desktop executables
- `.github/workflows/desktop-provenance.yml`: signed installer provenance plus installed Windows startup evidence, including healthy/fault evidence for release artifacts
- `.github/workflows/fault-injection.yml`: recurring installed Windows drill to catch regression drift between releases; it replays the same installed-desktop proof without owning release signing

For PR packaged diagnostics, `desktop-package-windows` should retain a
`desktop-windows-fault-smoke` artifact containing at least the packaged-build
log, packaged-shell smoke log, top-level `summary.json`, and per-scenario result
files. That artifact proves packaged CI-binary startup evidence only; it is not
release-installed MSI/NSIS evidence.

Required desktop signing secrets:

- `GOAT_DESKTOP_SIGNING_CERT_BASE64`
  - base64-encoded PFX for the Windows desktop signing certificate
- `GOAT_DESKTOP_SIGNING_CERT_PASSWORD`
  - password for the PFX
- optional `GOAT_DESKTOP_SIGNING_TIMESTAMP_URL`
  - overrides the default RFC3161 timestamp server used by `signtool`

If public desktop signing secrets are missing, the public tagged workflow must
fail closed rather than silently shipping unsigned installers.

If artifact attestations are not available for the repository plan, keep the digest
manifests and SBOM outputs as the minimum provenance record and enable attestations
later via the `ENABLE_GITHUB_ATTESTATIONS` repository variable when support is ready.
