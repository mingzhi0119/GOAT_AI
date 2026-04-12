# GOAT AI Roadmap

> Last updated: 2026-04-12
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This file tracks **unfinished work only**.

Completed phases, landed slices, and historical closeout notes live in:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [DOMAIN.md](../architecture/DOMAIN.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)

---

## Open Work

### Audit remediation backlog

These items come from the April 2026 lifecycle audit and should take priority over
new capability expansion. The goal is to close industrial-score gaps before
widening product promises.

No open P0 audit items remain after the 2026-04-11 remediation pass.

The 2026-04-11 P1 pass also closed the deploy/ops asset-governance slice
(direct tests now cover deploy/service/health/watchdog/phase0 contracts) and
closed the contract-tooling startup-side-effect slice (API contract tooling no
longer needs runtime DB/telemetry initialization just to inspect OpenAPI).

The same 2026-04-11 remediation sequence also closed the remaining non-desktop
P1 audit slices:

- immutable artifact promotion now builds once in CI, promotes the same retained
  bundle through staging and production, records per-environment promotion
  evidence, and exercises artifact rollback via
  `python -m tools.release.exercise_release_rollback_drill`
- frontend browser-level protected-flow coverage, lint, bundle-budget checks,
  and Playwright regression gates are now part of the standard CI path
- backend provider drift is closed; the repo is now explicit that the active LLM
  runtime is Ollama-only until a future provider decision lands end to end
- request correlation and durable packaged-desktop diagnostics are surfaced
  consistently enough to close the cross-surface observability P1 slice
- the single-writer contract is now exposed via `/api/system/runtime-target`, and
  merge-blocking latency smoke runs in CI through
  `python -m tools.quality.run_pr_latency_gate`

No open P1 audit items remain after the 2026-04-11 desktop release-maturity
closure. The final desktop slice now has:

- merge-blocking Windows packaged-desktop validation in CI
- a signed Windows desktop release path in
  `.github/workflows/desktop-provenance.yml`
- packaged-artifact provenance for Windows installers plus the existing Linux
  sidecar digest/SBOM record
- explicit packaged-app failure handling in the Tauri shell so startup timeout
  and sidecar exit paths do not silently reveal a broken UI

No open P2 audit items remain after the 2026-04-12 closeout. That pass:

- extracted remaining composer-panel and attachment-strip responsibilities out of
  the largest frontend hotspot so `ChatWindow` no longer owns the full popover
  state machine inline
- tightened bundle-budget thresholds after the async chunk split reduced the main
  entry cost to a governed baseline
- expanded automated accessibility coverage for the plus-menu and upload-manager
  focus contracts instead of relying on manual review alone
- promoted repository-layout truth and industrial-score guardrails into
  merge-blocking governance tests so docs drift and stale paths are less likely
  to re-enter the repo unnoticed

Any remaining work is now capability roadmap scope, not audit-remediation debt.

### Active priorities

1. **Multi-step research behavior on top of landed web retrieval**
   - `/api/workbench/sources` now exposes runtime-ready experimental DDGS-backed `web`
   - browse/deep-research still remain bounded single-pass evidence briefs
   - the next step is iterative planning, fetch, synthesis, and stronger safety boundaries

2. **Project memory and connectors**
   - both are already advertised as future capability slots
   - they should not grow UI promises until the runtime, tenancy, and connector boundaries are real

3. **Desktop distribution maturity**
   - signed Windows release and packaged CI validation are landed
   - macOS/Linux public packaging, updater readiness, and deeper native runtime operations are still open
   - current governance order is: clear `backend-fast` first, then inspect `backend-heavy`, and only then move to `desktop-package-windows` / `desktop-supply-chain`
   - pre-ready restart/backoff is shipped, and the current residual risk is keeping the merge-blocking packaged-shell fault smoke in `desktop-package-windows` green for missing-sidecar, early-exit, and pre-ready-timeout paths

### Runtime platform

#### Phase 17 shared runtime foundations

- Goal: finish the shared task/runtime primitives that Browse, Deep Research, Canvas, project memory, and connectors should all build on.
- Remaining work:
  - clearer task cancellation and retry semantics
  - source registry extensions for real web and future connector-backed retrieval
- Sequencing rule:
  - finish shared runtime foundations before widening frontend promises

#### Phase 17B: plan-mode follow-ons

- Goal: move beyond the current minimal `task_kind = plan` runner.
- Remaining work:
  - safe cancellation
  - retry semantics
  - richer execution beyond a minimal inline markdown result

#### Phase 17C: browse and deep-research runtime

- Goal: replace the currently partial retrieval runtime with real web execution and stronger multi-step research behavior.
- Remaining work:
  - staged safety boundaries for public web vs private retrieval
  - iterative multi-step research behavior instead of one bounded retrieval pass
  - remote connector adapters behind the shared source registry

#### Phase 17E: project memory and connectors

- Goal: add project-scoped memory and external source plumbing once runtime foundations are ready.
- Remaining work:
  - explicit project scope and tenancy rules
  - connector registry and capability metadata
  - memory write/read boundaries that do not bypass authz/resource rules
  - read-only retrieval contracts before any write-capable connector path is enabled

### Code sandbox follow-ons

#### Phase 18: sandbox beyond the MVP

- Goal: extend the landed Docker-first sandbox without weakening the current operator/safety posture.
- Remaining work:
  - cancel / retry semantics for async runs
  - multi-file workspace ergonomics beyond inline text seeding
  - allowlisted egress modes instead of all-or-nothing disablement
  - alternate providers behind the same sandbox boundary
  - richer terminal / PTY UX beyond replayable chunked logs

#### Phase 18B: Rust sandbox supervisor

- Goal: move the most systems-heavy sandbox supervision responsibilities into a Rust runtime component while preserving the HTTP/API contract.
- Planned scope:
  - child-process lifecycle management
  - timeout and cancellation enforcement
  - stdout/stderr event streaming and bounded buffering
  - workspace and egress policy enforcement at the supervisor boundary
- Non-goals:
  - no rewrite of chat, knowledge, authz, or higher-level domain logic into Rust
  - no public API expansion solely because the runtime implementation changed
- Exit criteria:
  - the Rust supervisor can back the existing execution contract without changing API semantics
  - parity tests cover success, failure, timeout, cancellation, and log replay
  - rollout remains feature-gated until proven

### Desktop distribution and native runtime

Desktop shell scaffolding and packaged backend sidecar are already landed and archived. Remaining work starts at distribution maturity.

#### Phase 19C: platform installers, signing, and updates

- Goal: ship real installable desktop artifacts instead of developer-only bundles.
- Remaining work:
  - macOS signing
  - Linux packaged validation and release shape
  - updater readiness after signing is stable
  - explicit prerequisite/bootstrap story for end users and developers
- Exit criteria:
  - supported public installers are produced in CI/release workflows
  - updater strategy is documented and wired only after signed release flow is stable
  - prerequisite installation paths are explicit enough for new users

#### Phase 19D: desktop-native UX and local-runtime operations

- Goal: make the packaged app behave like a real desktop product rather than a wrapped website.
- Remaining work:
  - desktop-native readiness status
  - durable log sinks and log viewing
  - app-data discoverability for outputs
  - desktop settings for endpoint/runtime diagnostics
  - clear packaged-build behavior for risky capability gates such as code sandbox

#### Phase 19E: Rust desktop runtime bridge

- Goal: harden packaged-app startup and local-runtime operations by moving process supervision deeper into the native Rust layer in the Tauri shell.
- Planned scope:
  - native sidecar boot coordination
  - readiness handshake before window reveal
  - native log sink wiring
  - restart/backoff and clearer first-run failure reporting
  - desktop-safe local data and path handling
- Current governance focus:
  - the runtime behavior is landed, but merge-blocking packaged-shell fault smoke still needs to remain green on desktop-related changes because Rust unit tests and local builds alone are not enough evidence for pre-ready retry behavior
- Non-goals:
  - no SPA rewrite into Rust
  - no backend business-logic rewrite solely for desktop packaging

### UI surfaces waiting on backend/runtime

These items should remain roadmap-only in the frontend until the corresponding backend/runtime slice exists.

- Cloud model API integration for non-local inference backends
- Real Search / Browse mode
- Deep Research
- Project-scoped knowledge / memory
- Connected apps / external sources

---

## Dependencies and constraints

- Capability gates must continue to separate runtime unavailability from policy denial.
- Storage evolution must preserve the current SQLite-first / single-writer operational contract unless a separate decision log changes that assumption.
- Search, research, canvas, connector UI, and future cloud model selection should not expose fake capabilities before the backend/runtime can actually support them.
- Shared runtime foundations should land before feature-specific frontend promises widen.

---

## Decision pending

### `/api/knowledge/answers` semantic alignment

The product still needs a decision on whether `/api/knowledge/answers` should keep returning a raw retrieved snippet summary or move to the same LLM-synthesis behavior used by chat with `knowledge_document_ids`.

- Current state: chat synthesizes retrieved context; `/api/knowledge/answers` returns a snippet-style response
- Decision needed: keep the divergence and document it, or unify the answer semantics
- Impact: user expectations, API documentation, and the long-term retrieval UX
