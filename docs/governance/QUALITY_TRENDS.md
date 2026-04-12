# GOAT AI Quality Trends

Last updated: 2026-04-11

This document defines the shipped recurring engineering-quality evidence baseline.

## Current baseline

- Workflow: [`.github/workflows/quality-trends.yml`](../../.github/workflows/quality-trends.yml)
- Snapshot generator: [`tools/quality/quality_snapshot.py`](../../tools/quality/quality_snapshot.py)
- Artifact output: `quality-snapshot`
- Related security snapshot generator: [`tools/quality/security_review_snapshot.py`](../../tools/quality/security_review_snapshot.py)
- Related performance summary generator: [`tools/quality/load_chat_smoke.py`](../../tools/quality/load_chat_smoke.py)

The scheduled workflow currently captures:

- backend coverage from `coverage.py` JSON output
- frontend coverage from `frontend/coverage/lcov.info`
- recurring security-review evidence:
  - Python / Node / Rust dependency-audit state
  - desktop Cargo-audit exception review metadata
  - configured credential-rotation evidence inputs
- a clean frontend production build in the same recurring run
- optional deployed-environment performance smoke summary when `PERFORMANCE_BASE_URL` is configured
- git SHA, ref, workflow run id, and run attempt metadata

## How to use it

1. Run the workflow manually or let the weekly schedule produce a fresh snapshot.
2. Download the `quality-snapshot` artifact from the workflow run.
3. Compare the new `quality-snapshot.json` with previous snapshots.
4. Review `security-review-snapshot.json` for backlog growth or missing rotation evidence.
5. When present, compare `performance-summary.json` with previous runs for latency drift.
6. Escalate any sustained regression in coverage, security backlog, or recurring workflow instability.

## Remaining limits

- defect escape rate still relies on release/incident review rather than a first-class issue-tracker integration
- performance trend evidence depends on a configured deployed target (`PERFORMANCE_BASE_URL`) for weekly capture
- release-over-release scorecard rollups remain a human review activity over the stored artifacts rather than a rendered dashboard in-repo

## Related docs

- [ROADMAP.md](ROADMAP.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [SECURITY_RESPONSE.md](SECURITY_RESPONSE.md)
