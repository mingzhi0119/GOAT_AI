# GOAT AI Incident Triage

Use this runbook when staging or production health regresses and you need a fast first-pass diagnosis.

## Correlation first

1. Capture the failing request path and timestamp.
2. Pull the `X-Request-ID` from the client response when available.
3. Search structured logs for the same `request_id` before changing runtime state.

## Merge-blocking CI is red

1. Clear `backend-fast` first. Its changed-files `ruff format --check` and repo-wide `ruff check` can block the rest of backend CI before contract, audit, and `pytest` results are even visible.
2. After `backend-fast` is green, inspect `backend-heavy` for `python -m tools.contracts.check_api_contract_sync`, OTel enabled-path tests, the observability asset contract, `pytest`, `pip-audit`, `python -m tools.quality.run_rag_eval`, `lint-imports`, and the PR latency gate.
3. Only after backend is green should triage move to `desktop-package-windows` and `desktop-supply-chain`.
4. Treat `desktop-package-windows` as the source of truth for packaged pre-ready startup resilience because it now carries the packaged-shell fault smoke for missing-sidecar, early-exit, and health-timeout paths.
5. Expect `desktop-package-windows` for desktop build inputs, not just `frontend/src-tauri/**`: frontend build inputs such as `frontend/src/**`, `frontend/public/**`, `frontend/index.html`, Vite/Tailwind/PostCSS/TS config, desktop scripts, desktop tools, and desktop governance tests/workflows are in scope for that PR gate.
6. Do not expect `desktop-package-windows` for non-desktop-only backend or documentation changes when the packaged Windows build surface is untouched.
7. Treat `.github/workflows/desktop-provenance.yml` as the source of truth for installed Windows release evidence and `.github/workflows/fault-injection.yml` as the recurring installed-desktop drill; do not mix those failures into the PR packaged gate.

## What to look at first

### Readiness is failing

- Check `GET /api/ready` and `GET /api/health`.
- Inspect `var/logs/fastapi.log`.
- Scrape `sqlite_log_write_failures_total` and `ollama_errors_total`.
- If only readiness is red and health is green, assume a dependency or migration issue before assuming process crash.

### Chat latency or stream failures are rising

- Run `python -m tools.quality.load_chat_smoke --base-url <base-url> --model <model> --runs 10 --show-system-inference`.
- Check `http_request_duration_seconds`, `chat_stream_completed_total`, and `ollama_errors_total`.
- Compare first-token p95 against the SLO in `OPERATIONS.md`.

### Retrieval quality looks degraded

- Check `knowledge_retrieval_requests_total{outcome="hit|miss"}`.
- Check `knowledge_query_rewrite_applied_total`.
- Re-run `python -m tools.quality.run_rag_eval` before changing retrieval defaults.

### Feature-gated runtime looks unavailable

- Check `feature_gate_denials_total{feature,gate_kind,reason}`.
- Verify whether the failure is policy (`403`) or runtime (`503`) before debugging the wrong layer.

## Escalation hints

- Repeated SQLite write failures: stop new persistence work and prepare backup / restore checks.
- Repeated readiness failures after deploy: use `ROLLBACK.md` rather than iterating hotfixes blindly on the host.
- Observability asset drift or OTel enabled-path failures: fix `backend-heavy` first so alerts, dashboards, runbooks, and `traceparent` propagation are back in sync before debugging higher-level symptoms.
- Repeated desktop startup failures: capture sidecar logs, Tauri shell logs, the packaged app version, the logged restart attempt counts, the recorded failure stage, the installer kind (`msi` vs `nsis`), the install root, the uninstall result, and whether the failure came from `desktop-package-windows`, release installed evidence, or the scheduled installed drill before retrying. Call out the exact fault-smoke scenario when known: `missing_sidecar`, `exit_before_ready`, or `hang_before_ready`.

## Required follow-up

- Document the trigger, request id, user-visible impact, and mitigation in the incident ticket or release note.
- If the issue exposed a missing alert, dashboard panel, or runbook gap, patch the corresponding observability asset in the same follow-up change.
