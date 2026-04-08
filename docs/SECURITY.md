# GOAT AI Security Notes

This document records the current threat model and the guardrails that matter for Phase 13.5.

## Authentication and trust model

- The production deployment uses a shared API key model, not per-user authentication.
- Do not treat the key as user identity or as a substitute for row-level authorization.
- Any future authorization work should be explicit and service-layer driven.

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

- `pip-audit` runs in CI against `requirements.txt` to surface known dependency vulnerabilities.
- `ruff check` runs in CI to catch style and correctness regressions early.
- Formatting checks should stay lightweight enough to avoid forcing a repository-wide rewrite for legacy files.

## Related docs

- [OPERATIONS.md](OPERATIONS.md)
- [ROADMAP.md](ROADMAP.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
