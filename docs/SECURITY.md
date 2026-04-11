# GOAT AI Security Notes

This document records the current threat model and the guardrails that matter for Phase 13.5.

## Authentication and trust model

- The production deployment uses a shared API key model, not per-user authentication.
- Do not treat the key as user identity or as a substitute for row-level authorization.
- Any future authorization work should be explicit and service-layer driven.
- Phase 16C introduces credential-backed authorization and tenancy boundaries, not end-user identity.
- Resource-level access decisions should be made by `backend.services.authorizer` helpers (invoked from application use cases and services), using stable principal, tenant, and scope metadata.
- Sessions, artifacts, knowledge documents, and media uploads now carry explicit tenancy metadata so resource checks do not depend on a raw owner header alone.

## Upload and media handling

- Treat file extensions and browser-reported MIME types as hints only.
- Validate uploads against the backend allowlist and size limits before processing.
- Reject oversized inputs early; do not decompress or parse unbounded archives.
- Image and video uploads should remain explicitly gated by model capability; unsupported models must fail closed.

## CSV and spreadsheet injection

- Treat CSV/XLSX content as data, not executable spreadsheet logic.
- When exporting or rendering spreadsheet-like content, sanitize leading formula characters such as `=`, `+`, `-`, and `@`.
- Do not auto-open or execute macros, scripts, or embedded links from uploaded files.

## Logging and data minimization

- Do not log raw uploads, secrets, or full prompts at INFO level or higher.
- Prefer compact summaries, request IDs, and stable error codes over full content dumps.
- Keep diagnostic logs narrowly scoped so they can be shared safely during incident review.

## Dependency and CI hygiene

- `pip-audit` runs in CI against `requirements-ci.txt` (runtime `requirements.txt` plus lint/test tooling) to surface known dependency vulnerabilities.
- `npm audit --audit-level=high` runs in CI against `frontend/package-lock.json`, including desktop build-tool dependencies in `devDependencies`.
- `cargo audit --deny warnings --file frontend/src-tauri/Cargo.lock` runs in CI for the desktop Rust shell and bundled runtime dependencies.
- `ruff check` runs in CI to catch style and correctness regressions early.
- Formatting checks should stay lightweight enough to avoid forcing a repository-wide rewrite for legacy files.
- Dependency audit exceptions must be explicit, time-bounded, and tracked in-repo. Silent local bypasses or ad hoc CI edits are not acceptable release practice.
- Current desktop Rust audit waivers live in [DESKTOP_CARGO_AUDIT_EXCEPTIONS.md](DESKTOP_CARGO_AUDIT_EXCEPTIONS.md) and must be reviewed together with any workflow ignore changes.

## Frontend and desktop supply chain

- Frontend and desktop dependency audits are release gates, not advisory checks. PRs and pushes to `main` must keep the `frontend` and `desktop-supply-chain` jobs green.
- Desktop artifacts produced from local developer machines or unsigned ad hoc builds are internal/test-only artifacts. They must not be presented as public production releases.
- Publicly distributed desktop installers must come from target-platform CI or an equivalent auditable release pipeline, then move through the later signing flow tracked in `ROADMAP.md`.
- Until signed-release automation lands, any externally shared desktop package must be labeled internal/test-only and accompanied by the exact build provenance used to create it.

## Related docs

- [OPERATIONS.md](OPERATIONS.md)
- [ROADMAP.md](ROADMAP.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
