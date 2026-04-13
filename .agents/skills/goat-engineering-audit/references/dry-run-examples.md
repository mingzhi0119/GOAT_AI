# Dry-Run Examples

## Example 1

User asks:
- "Audit whether the current `main` branch is ready for a formal 9/10 engineering review."

First moves:
- read [truth-sources.md](truth-sources.md), [severity-rubric.md](severity-rubric.md), and [readiness-report-template.md](readiness-report-template.md)
- read the workflows, implementation files, and tests named in the request before scoring readiness
- separate in-repo proof from residual risk and external blockers

Validate with:
- rerun only the narrow test suites needed to confirm or clear the findings you report

## Example 2

User asks:
- "Check whether the desktop, authz, and observability governance slices are still closed or have regressed."

First moves:
- read the matching specialized skill references before concluding a slice regressed
- look for structural proof gaps in workflows, tests, or retained evidence rather than style-only differences
- confirm any claimed regression against current code and tests instead of roadmap history alone

Validate with:
- cite the exact workflows, files, and tests that prove the slice is still closed or has reopened
