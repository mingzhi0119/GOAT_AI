# Dry-Run Examples

## Example 1

User asks:
- "I changed `.github/workflows/desktop-provenance.yml` and the installed smoke tool; what proof do I need before calling release evidence healthy?"

First moves:
- read [desktop-boundaries.md](desktop-boundaries.md), [evidence-checklist.md](evidence-checklist.md), and [retention-and-summary.md](retention-and-summary.md)
- separate packaged PR validation from installed release evidence and the scheduled drill
- confirm MSI and NSIS still behave as dual installed-artifact proof paths

Expected output:
- which desktop proof chain is in scope
- the exact retention, summary, and workflow invariants that must still hold
- the narrowest tests needed before calling release evidence healthy

Validate with:
- run [test_desktop_release_governance.py](../../../../__tests__/desktop/test_desktop_release_governance.py) and the narrow installed smoke tests that cover the changed tool path

## Example 2

User asks:
- "A packaged-shell smoke failure showed up in PR CI; does that mean release governance regressed too?"

First moves:
- check whether the failure is on the packaged path or the installed release/drill path
- avoid treating PR packaged binaries as proof for release installers
- confirm whether retention, summary shape, and workflow ownership changed together or only the packaged gate moved

Expected output:
- a clear packaged-vs-release-vs-drill scope decision
- which desktop proof chains remain healthy even if one path regressed
- the minimum follow-up tests or evidence needed for the affected chain only

Validate with:
- report which desktop proof chain actually regressed and which ones remain mechanically proven

## Example 3

User asks:
- "I changed a desktop workflow plus release docs; which desktop proof chain is in scope, and which governance docs actually own the wording update?"

First moves:
- separate packaged PR validation, release installed evidence, and recurring drill ownership before reasoning about docs
- compose with `goat-ci-surface-router` to keep the required validation matrix honest
- compose with `goat-governance-sync` before editing any runbook or roadmap text

Expected output:
- the in-scope desktop proof chain for the diff
- whether `RELEASE_GOVERNANCE.md`, `OPERATIONS.md`, `INCIDENT_TRIAGE.md`, or none of them should move
- the narrowest test pair that proves both workflow truth and doc ownership

Validate with:
- run `python -m pytest __tests__/desktop/test_desktop_release_governance.py __tests__/ops/test_ops_asset_contracts.py -q`

## Example 4

User asks:
- "We changed Linux packaged-desktop proof and macOS blocker reporting in the same slice; what is actually landed?"

First moves:
- separate Linux packaged evidence, Windows installed evidence, and macOS blocker-report scaffolding before reasoning about shipped status
- compose with `wsl-linux-rust-desktop` for Linux parity from Windows
- keep external signing/notarization blockers separate from repo-landed workflow proof

Expected output:
- which platform proof path moved and whether it is packaged, installed, or blocker-only
- which status wording can land today versus what must stay as external blocker text
- the exact workflow/tests that prove the distinction

Validate with:
- run `python -m pytest __tests__/desktop/test_desktop_release_governance.py __tests__/ops/test_ops_asset_contracts.py -q` and the matching WSL Linux desktop validation when the Linux path changed
