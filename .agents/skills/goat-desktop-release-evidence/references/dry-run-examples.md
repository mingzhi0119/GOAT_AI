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
