# GOAT AI Roadmap

> Last updated: 2026-04-11
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This file tracks **unfinished work only**.

Completed phases, landed slices, and historical closeout notes live in:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [OPERATIONS.md](OPERATIONS.md)
- [DOMAIN.md](DOMAIN.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)

---

## Open Work

### Audit remediation backlog

These items come from the April 2026 lifecycle audit and should take priority over
new capability expansion. The goal is to close industrial-score gaps before
widening product promises.

No open P0 audit items remain after the 2026-04-11 remediation pass. Active
follow-on work now starts at P1 and focuses on broader contract, release,
desktop, and observability maturity.

The 2026-04-11 P1 pass also closed the deploy/ops asset-governance slice
(direct tests now cover deploy/service/health/watchdog/phase0 contracts) and
closed the contract-tooling startup-side-effect slice (API contract tooling no
longer needs runtime DB/telemetry initialization just to inspect OpenAPI).

#### P1: immutable artifact promotion and richer release evidence

- Problem:
  - release correctness now verifies exact refs / SHAs, but deploys still build from mutable hosts instead of promoting immutable artifacts
  - release evidence still stops short of a full artifact-first provenance trail across staging and production
- Solution:
  - build release artifacts once in CI, attest/sign them, and promote the same immutable payload through staging and production
  - extend release evidence so operators can answer "which artifact digest reached which environment, and when?" without host forensics
  - add rollback drills for artifact promotion, not only source-ref deployment
- Exit criteria:
  - staging and production promote the same immutable artifact, not independent host builds
  - release evidence captures artifact digest, environment promotion, and rollback target
  - rollback drills validate artifact-first recovery

#### P1: frontend browser-level coverage and broader UI quality gates

- Problem:
  - frontend contract generation/checking is now automated, but browser-level end-to-end coverage is still missing
  - complex protected flows are now covered in jsdom/App integration tests, not in a real browser runner
  - lint and accessibility/performance checks are still not part of the standard frontend gate
- Solution:
  - add browser-level integration coverage for chat, history, uploads, auth-enabled flows, and feature-gated UI
  - add lint and accessibility/performance checks to the frontend gate
  - keep protected code-sandbox async log flows inside the same browser regression suite so auth/header regressions do not slip past unit tests
- Exit criteria:
  - protected-path browser tests exist for the highest-risk flows
  - lint and basic accessibility checks are part of the standard frontend gate

#### P1: desktop release maturity, installer validation, and native recovery

- Problem:
  - desktop CI validates sidecar build and Rust tests, but not a full packaged installer/bundle path
  - signing, installer verification, and cross-platform packaged validation are still incomplete
  - desktop runtime supervision is still thin: one-shot health wait, limited child-exit handling, and weak durable logging
- Solution:
  - add CI validation for real packaged desktop artifacts, not only the sidecar
  - extend provenance from Linux sidecar evidence to shipped installers/bundles
  - land signing/notarization workflows for supported release targets
  - harden the Rust bridge for child-exit handling, restart/backoff, and durable packaged-app log sinks
  - add desktop release-path tests, packaged smoke tests, and clearer operator/user recovery guidance
- Exit criteria:
  - supported desktop artifacts are built, validated, and provenance-recorded in CI
  - signed release artifacts are the default public distribution path
  - packaged-app failures are diagnosable without manual stdout/stderr scraping

#### P1: backend provider drift and runtime seam hardening

- Problem:
  - some provider/config paths, such as the OpenAI client seam, remain partially landed and undocumented
  - critical runtime seams still rely on process-local assumptions
- Solution:
  - either wire unfinished provider paths all the way through settings/docs/tests or remove them until needed
  - clarify which runtime seams remain intentionally single-process and add stronger guards/tests around those assumptions
- Exit criteria:
  - provider/config surfaces are either fully supported or removed from the active code path
  - the repo is explicit about which seams are single-instance by design

#### P1: observability and request correlation across backend, frontend, and desktop

- Problem:
  - backend observability is much stronger than frontend and desktop observability
  - request IDs, stable error codes, and packaged-app diagnostics are not surfaced consistently to users or operators
- Solution:
  - expose request correlation and stable error codes in frontend-visible error states
  - add desktop log sink and failure-reporting paths that survive packaged runtime failures
  - keep dashboards, alerts, runbooks, and emitted metrics aligned whenever operator-facing telemetry changes
- Exit criteria:
  - user-visible failures can be correlated to backend logs without guesswork
  - desktop incidents have durable local diagnostic artifacts
  - observability assets remain version-aligned with emitted metrics and recovery runbooks

#### P1: performance governance and single-instance boundary clarity

- Problem:
  - performance smoke exists, but not as a standard PR-blocking gate
  - some heavy paths remain synchronous and local-file-backed
  - rate limiting, background jobs, and some telemetry remain process-local
- Solution:
  - define which performance budgets should block PRs versus only scheduled monitoring
  - harden heavy ingestion/retrieval paths with clearer limits, async/offline boundaries, or better isolation
  - document and enforce the current single-writer/single-instance boundary until a deliberate storage/runtime decision changes it
- Exit criteria:
  - the highest-risk latency regressions are caught before merge
  - heavy ingestion/runtime paths no longer rely on accidental best-effort behavior
  - operational boundaries are explicit enough that scaling expectations stay honest

#### P2: frontend modularity, accessibility, and bundle discipline

- Problem:
  - top-level orchestration hotspots are growing in `App`, `useChatSession`, and `ChatWindow`
  - bundle size warnings and continuous polling still create avoidable UX/perf drag
  - accessibility coverage is partial rather than systematic
- Solution:
  - continue extracting feature-specific controllers from the largest frontend hotspots
  - add bundle-budget monitoring and reduce long-lived polling where event- or visibility-driven refresh is enough
  - expand accessibility review and automated checks beyond the currently tested components
- Exit criteria:
  - major frontend hotspots are smaller and easier to reason about
  - bundle growth and polling cost are visible and governed
  - accessibility regressions are less likely to escape by accident

#### P2: documentation truth maintenance and semantic drift prevention

- Problem:
  - some docs, examples, and status narratives lag real implementation state
  - roadmap/status/doc files need stronger rules to keep feature claims honest
- Solution:
  - keep `README.md`, `.env.example`, `PROJECT_STATUS.md`, and operations docs aligned in the same change whenever runtime semantics change
  - add targeted checks for high-risk doc drift such as env vars, release-manifest schema, and feature-status claims
  - remove or archive stale guidance once a new source of truth exists
- Exit criteria:
  - operators and contributors can trust the primary docs without cross-referencing legacy files
  - high-risk semantic drift is caught by CI instead of review luck

### Active priorities

1. **Real web retrieval for workbench**
   - `/api/workbench/sources` already exposes `web`
   - the source remains declarative but runtime-unready
   - browse/deep-research should not remain permanently partial behind a fake-ready public source

2. **Project memory and connectors**
   - both are already advertised as future capability slots
   - they should not grow UI promises until the runtime, tenancy, and connector boundaries are real

3. **Desktop distribution maturity**
   - Windows packaging is landed
   - signed release, cross-platform packaged validation, updater readiness, and stronger native runtime operations are still open

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
  - actual public-web execution behind the `web` source
  - staged safety boundaries for public web vs private retrieval
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
  - Windows/macOS signing
  - Linux packaged validation and release shape
  - updater readiness after signing is stable
  - explicit prerequisite/bootstrap story for end users and developers
- Exit criteria:
  - signed installers are produced in CI/release workflows
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
