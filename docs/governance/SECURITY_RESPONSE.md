# GOAT AI Security Response Policy

Last updated: 2026-04-11

This document defines the P2 baseline for vulnerability response, dependency refresh,
and credential rotation. It is the operator-facing follow-through for the controls
summarized in [SECURITY.md](SECURITY.md).

## 1. Vulnerability triage expectations

- Treat a known actively exploited issue, remote code execution path, auth bypass, or
  secret exposure as `critical`.
- Treat an internet-reachable denial-of-service, privilege boundary weakness, or high
  confidence dependency vulnerability in a shipped path as `high`.
- Treat lower-confidence dependency advisories or non-default-path weaknesses as
  `medium` or `low` until proven otherwise.

## 2. Response targets

- `critical`
  - acknowledge the issue the same business day
  - mitigate or disable the exposed path within 24 hours
  - land a permanent fix or explicit compensating control within 72 hours
- `high`
  - acknowledge within 1 business day
  - land a fix, safe pin, or documented exception within 7 calendar days
- `medium`
  - triage in the next scheduled security review
  - fix or defer with rationale inside 30 calendar days
- `low`
  - fold into the normal dependency refresh cadence unless exploitability changes

## 3. Dependency refresh cadence

- Review Python, Node, and Rust dependency audit output at least weekly.
- Refresh routine dependencies at least monthly, even when there is no open advisory,
  so the repo does not accumulate large risky jumps.
- Do not let audit ignore lists drift silently; every exception must stay explicit,
  time-bounded, and reviewed in-repo.
- Release blockers:
  - any unresolved `critical` advisory in a shipped runtime path
  - any unresolved `high` advisory in a path that is enabled in CI, desktop packaging,
    or production deploys without a written compensating control

## 4. Credential rotation policy

- Shared API credentials and deploy credentials must rotate at least every 90 days.
- Rotate immediately when:
  - a secret may have been exposed
  - a maintainer with access leaves the project or changes responsibility
  - a CI secret, deployment host, or signing workstation is suspected compromised
- Rotation must prefer overlap:
  - add the replacement credential first
  - verify staging and production health with the replacement
  - revoke the previous credential only after validation succeeds
- Record the rotation date, affected credential scope, and operator in the release or
  incident notes.

## 5. Evidence and review

- Weekly review should include:
  - `security-review-snapshot.json` from [`.github/workflows/quality-trends.yml`](../../.github/workflows/quality-trends.yml)
  - current ignore lists and expiration dates
  - pending dependency refresh PRs or backlog items
- Monthly review should include:
  - last successful credential rotation date per credential class
  - release artifact provenance/SBOM workflow health
  - trend snapshots from [QUALITY_TRENDS.md](QUALITY_TRENDS.md)

## 6. Repository variables for recurring evidence

Configure these repository variables so the recurring security-review snapshot can
record credential-rotation evidence without exposing raw secrets:

- `GOAT_LAST_SHARED_API_KEY_ROTATION_DATE`
- `GOAT_LAST_DEPLOY_CREDENTIAL_ROTATION_DATE`
- `GOAT_LAST_DESKTOP_SIGNING_KEY_ROTATION_DATE`

Values must use `YYYY-MM-DD`.

## Related docs

- [SECURITY.md](SECURITY.md)
- [RELEASE_GOVERNANCE.md](../operations/RELEASE_GOVERNANCE.md)
- [QUALITY_TRENDS.md](QUALITY_TRENDS.md)
