# GOAT AI Roadmap

> Last updated: 2026-04-13
> Current release tag: **v1.3.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This file tracks **unfinished work only**.

Completed phases, landed slices, and historical closeout notes live in:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [DOMAIN.md](../architecture/DOMAIN.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)

---

## Open Work

### Active priorities

1. **Code sandbox follow-ons**
   - running-state cancellation and restart recovery are landed, but
     running-state retry semantics, allowlisted egress, richer workspace UX,
     and Rust supervisor parity remain open
2. **Desktop public release blockers**
   - Linux packaged build/provenance and readiness docs are landed, but public macOS signing/notarization and updater enablement remain open

### Repository-native Skills and Agent Automation

- Goal: keep hardening the repo-local Codex skill layer so audit, proof, CI-routing, and governance-sync workflows stay repeatable without reverting to thread-by-thread memory.
- Non-goals:
  - do not replace [`AGENTS.md`](../../AGENTS.md) or the engineering standards as the permanent policy layer
  - do not create a plugin marketplace or generic IDE macro bundle
  - do not collapse all governance work into one broad "catch-all skill"
- Remaining work:
  - extend forward-tested coverage beyond the current audit, ci-routing plus WSL composition, desktop evidence, sandbox runtime proof, frontend-exposed contract, caller-scoped workbench/runtime proof, observability, and governance-sync task set; keep tightening references when new scenarios expose ambiguity or stale truth sources
  - add deterministic `scripts/` or `assets/` only where repeated usage shows a real need beyond the current shared prompt/output patterns and governance tests
  - extend the governance coverage around `.agents/skills/` as the inventory grows so future additions cannot drift in metadata, links, or directory shape
  - decide when the skill layer is stable enough to promote from roadmap follow-on work into shipped-status documentation
- Relationship to existing skills:
  - `wsl-linux-build`, `wsl-linux-ops-checks`, and `wsl-linux-rust-desktop` remain the execution-layer helpers for Linux-targeted validation from Windows
  - the new `goat-*` skills sit above them as governance/proof workflows and may compose with them when Linux parity is required

### Governance tooling follow-ons

- Goal: extend the now-landed governance tooling pilot only where additional scope still has clear payback.
- Remaining work:
  - decide whether future workbench, connector, or other newly shipped frontend surfaces should adopt the same runtime parser pattern when a real consumer lands, while keeping the current OpenAPI generation chain as the only contract source
  - decide whether the current frontend `dependency-cruiser` rules should widen after the present structure stabilizes, without expanding the tool to Python imports
  - decide whether feature-spec usage should grow beyond the current single real example, while keeping `AGENTS.md`, repo-local skills, roadmap, and status docs as the canonical governance layer

### Runtime platform

#### Phase 17B: plan-mode follow-ons

- Goal: move beyond the current minimal `task_kind = plan` runner.
- Remaining work:
  - running-state interruption beyond the current queued-only control plane
  - richer execution beyond a minimal inline markdown result

#### Phase 17C: browse and deep-research runtime

- Goal: continue hardening the landed browse/deep-research runtime around safety boundaries, richer sources, and the now-landed shared runtime control plane.
- Remaining work:
  - staged safety boundaries for public web vs private retrieval
  - remote connector adapters behind the shared source registry

#### Phase 17E: project memory and connectors

- Goal: add project-scoped memory and external source plumbing once runtime foundations are ready.
- Remaining work:
  - write-capable connector authorization and resource boundaries
  - live remote connector adapters plus durable credential handling beyond the current operator-provisioned static bindings
  - project-memory mutation or editing flows, if they are introduced later, without bypassing authz/resource rules
  - keep future connector widening behind the existing workbench/task boundary until the stronger authz and rollback semantics are mechanically proven

### Code sandbox follow-ons

#### Phase 18: sandbox beyond the MVP

- Goal: extend the landed Docker-first sandbox without weakening the current operator/safety posture.
- Remaining work:
  - running-state retry semantics beyond the now-landed cancellation control seam
  - multi-file workspace ergonomics beyond inline text seeding plus the landed
    workspace manifest/runtime metadata hints
  - allowlisted egress modes instead of the current disabled-only contract
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

Desktop shell scaffolding and packaged backend sidecar are already landed and archived. Signed Windows public packaging is shipped, Linux packaged-desktop CI/release scaffolding plus readiness docs are now landed, and the remaining work is the narrower public-release and deeper-native-runtime follow-on set below.

#### Phase 19C: platform installers, signing, and updates

- Goal: finish the remaining public-release blockers after the shipped Windows
  path and the now-landed Linux packaged proof/readiness scaffolding.
- Remaining work:
  - public macOS signing, notarization, and release-secret wiring
  - updater readiness after signing is stable
- Exit criteria:
  - supported public installers are produced in CI/release workflows
  - updater strategy is documented and wired only after signed release flow is stable

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

These items should remain roadmap-only in the frontend until the corresponding backend/runtime slice exists. The shipped UI now treats `/api/system/features` as the capability truth for currently exposed workbench affordances, so future placeholders should stay hidden or diagnostic-only until the backend path is mechanically proven.

- Cloud model API integration for non-local inference backends
- Real Search / Browse mode
- Deep Research
- Project-scoped knowledge / memory
- Connected apps / external sources

---

## Dependencies and constraints

- Planning for future workbench, connector, project-memory, and other frontier surfaces should follow the canonical policy in [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md), especially the admission-gate and capability-gate rules.
- Future project-memory, connector, and frontend widening should build on the landed shared source catalog, capability assembly, and source-executor seams before promising broader runtime behavior.
- Shared runtime foundations now build on the shipped object-store boundary plus the hosted/server Postgres runtime metadata posture in [POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md](../architecture/POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md), while local and desktop continue to default to SQLite.

---
