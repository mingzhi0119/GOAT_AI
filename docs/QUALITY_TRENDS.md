# GOAT AI Quality Trends

Last updated: 2026-04-11

This document defines the first P2 baseline for recurring engineering-quality trend
capture.

## Current baseline

- Workflow: [`.github/workflows/quality-trends.yml`](../.github/workflows/quality-trends.yml)
- Snapshot generator: [`tools/quality_snapshot.py`](../tools/quality_snapshot.py)
- Artifact output: `quality-snapshot`

The scheduled workflow currently captures:

- backend coverage from `coverage.py` JSON output
- frontend coverage from `frontend/coverage/lcov.info`
- a clean frontend production build in the same recurring run
- git SHA, ref, workflow run id, and run attempt metadata

## How to use it

1. Run the workflow manually or let the weekly schedule produce a fresh snapshot.
2. Download the `quality-snapshot` artifact from the workflow run.
3. Compare the new `quality-snapshot.json` with previous snapshots.
4. Escalate any sustained regression in coverage or repeated workflow instability.

## What this baseline does not cover yet

- defect escape rate
- long-term dependency vulnerability backlog history
- automatic performance-trend aggregation from the nightly smoke workflow
- release-over-release scorecard rollups

Those remain active P2 follow-ons in [ROADMAP.md](ROADMAP.md).

## Related docs

- [ROADMAP.md](ROADMAP.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [SECURITY_RESPONSE.md](SECURITY_RESPONSE.md)
