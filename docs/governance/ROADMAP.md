# GOAT AI Roadmap

> Last updated: 2026-04-13
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

The 2026-04-12 P2 closeout completed the original lifecycle-audit backlog. That pass:

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

The same-day engineering-score follow-on pass also closed the last open `P2`
gaps:

- backend runtime persistence and stream hotspots are now split into smaller
  modules instead of concentrating state transitions, storage mapping, and
  orchestration in a few oversized files
- workbench now has dedicated `workbench:read`, `workbench:write`, and
  `workbench:export` scopes, with route/authz semantics proven through contract
  and application tests
- OTel enabled-path behavior and observability assets are now mechanically
  verified in `backend-heavy`
- top-bar settings/actions now use real keyboard/focus semantics, and chat
  composer state has been extracted out of the largest frontend hotspot
- Windows desktop evidence now covers installed MSI/NSIS startup behavior in the
  release workflow plus a recurring installed-desktop drill

No open `P2` engineering-score items remain after the 2026-04-12 closeout.

The same 2026-04-12 governance-maintenance pass also closed the prior `P3`
watchpoints:

- `desktop-package-windows` now has path-truth gating, merge-blocking packaged-shell fault smoke, retained failure logs/summaries, and governance tests that pin the packaged-desktop PR workflow shape
- `.github/workflows/desktop-provenance.yml` and
  `.github/workflows/fault-injection.yml` now retain structured installed
  Windows evidence for both MSI and NSIS across install -> healthy launch ->
  pre-ready fault scenarios -> uninstall, with release-vs-drill ownership
  boundaries documented in ops runbooks
- workbench/authz and observability widening risk is now mechanically guarded
  through caller-scoped `/api/system/features` contract tests, workbench
  compatibility/visibility tests, and bidirectional metric-asset contracts

No open `P3` governance-maintenance watchpoints remain inside the repository.
Remaining audit-adjacent risk now sits in external GitHub/release conditions
such as branch-protection wiring, hosted Windows runner execution, and signing
secret availability.

### Active priorities

1. **Multi-step research behavior on top of landed web retrieval**
   - `/api/workbench/sources` now exposes runtime-ready experimental DDGS-backed `web`
   - browse/deep-research still remain bounded single-pass evidence briefs
   - the next step is iterative planning, fetch, synthesis, and stronger safety boundaries

2. **Project memory and connectors**
   - both are already advertised as future capability slots
   - they should not grow UI promises until the runtime, tenancy, and connector boundaries are real
   - any widening work should satisfy the admission gate in `docs/standards/ENGINEERING_STANDARDS.md` before implementation starts

3. **Desktop distribution maturity**
   - signed Windows release and packaged CI validation are landed
   - macOS/Linux public packaging, updater readiness, and deeper native runtime operations are still open
   - current governance order is: clear `backend-fast` first, then inspect `backend-heavy`, and only then move to `desktop-package-windows` / `desktop-supply-chain`
   - pre-ready restart/backoff is shipped, and the PR packaged-binary smoke plus release/scheduled installed-desktop evidence are now fixed governance mechanisms rather than ad hoc watchpoints

### Repository-native Skills and Agent Automation

- Goal: keep hardening the repo-local Codex skill layer so audit, proof, CI-routing, and governance-sync workflows stay repeatable without reverting to thread-by-thread memory.
- Non-goals:
  - do not replace [`AGENTS.md`](../../AGENTS.md) or the engineering standards as the permanent policy layer
  - do not create a plugin marketplace or generic IDE macro bundle
  - do not collapse all governance work into one broad "catch-all skill"
- Remaining work:
  - extend forward-tested coverage beyond the current audit, ci-routing plus WSL composition, desktop plus governance-runbook linkage, frontend-exposed contract, authz, observability, and governance-sync task set; keep tightening references when new scenarios expose ambiguity or stale truth sources
  - add deterministic `scripts/` or `assets/` only where repeated usage shows a real need beyond the current shared prompt/output patterns and governance tests
  - extend the governance coverage around `.agents/skills/` as the inventory grows so future additions cannot drift in metadata, links, or directory shape
  - decide when the skill layer is stable enough to promote from roadmap follow-on work into shipped-status documentation
- Relationship to existing skills:
  - `wsl-linux-build`, `wsl-linux-ops-checks`, and `wsl-linux-rust-desktop` remain the execution-layer helpers for Linux-targeted validation from Windows
  - the new `goat-*` skills sit above them as governance/proof workflows and may compose with them when Linux parity is required

### Governance tooling follow-ons

- Goal: extend the now-landed governance tooling pilot only where additional scope still has clear payback.
- Already landed and tracked in [PROJECT_STATUS.md](PROJECT_STATUS.md):
  - repo-native decision-record templates and PR guidance
  - frontend-only `dependency-cruiser`
  - shared runtime parsing across the current shipped frontend JSON adapters plus current chat/upload/code-sandbox SSE boundaries
  - lightweight non-canonical `spec/plan/tasks` pilot under `docs/governance/specs/`
- Remaining work:
  - decide whether future workbench, connector, or other newly shipped frontend surfaces should adopt the same runtime parser pattern when a real consumer lands, while keeping the current OpenAPI generation chain as the only contract source
  - decide whether the current frontend `dependency-cruiser` rules should widen after the present structure stabilizes, without expanding the tool to Python imports
  - decide whether feature-spec usage should grow beyond the current single real example, while keeping `AGENTS.md`, repo-local skills, roadmap, and status docs as the canonical governance layer
  - keep applying the admission gate for future workbench, connector, and project-memory widening so those surfaces do not outrun tenancy, authz, contract-proof, and rollback planning
- Non-goals:
  - do not introduce OpenAPI Generator alongside the current `docs/api/openapi.json -> openapi-typescript -> contract:check` path unless the repo explicitly chooses to replace that pipeline end to end
  - do not add a second constitution/process system that competes with the current standards, skills, roadmap, and status documents

### Runtime platform

#### Phase 17 shared runtime foundations

- Goal: finish the shared task/runtime primitives that Browse, Deep Research, Canvas, project memory, and connectors should all build on.
- Remaining work:
  - source registry extensions for real web and future connector-backed retrieval
  - broader runtime composition for project memory/connectors on top of the now-landed queued-only cancel/retry control plane
- Sequencing rule:
  - finish shared runtime foundations before widening frontend promises

#### Phase 17B: plan-mode follow-ons

- Goal: move beyond the current minimal `task_kind = plan` runner.
- Remaining work:
  - running-state interruption beyond the current queued-only control plane
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
  - running-state cancellation / retry behavior beyond the current queued-only control plane
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
  - the runtime behavior and its evidence gates are landed; remaining work in this phase is product/runtime breadth rather than keeping packaged-binary and installed-evidence guardrails alive by convention
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
