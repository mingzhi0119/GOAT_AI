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

### Active priorities

1. **Multi-step research behavior on top of landed web retrieval**
   - `/api/workbench/sources` now exposes runtime-ready experimental DDGS-backed `web`
   - browse/deep-research still remain bounded single-pass evidence briefs
   - the next step is iterative planning, fetch, synthesis, and stronger safety boundaries
   - evaluate a LangGraph-backed orchestration path for deeper multi-step research only if it can sit behind the existing `/api/workbench/*` contract instead of forcing a frontend-visible runtime rewrite

2. **Project memory and connectors**
   - both are already advertised as future capability slots
   - the open work is still runtime foundations, tenancy rules, and connector boundaries that make those slots real
   - if LangGraph is adopted, treat it as an internal execution/runtime option for long-running workbench tasks rather than as the public product contract

3. **Desktop distribution maturity**
   - macOS/Linux public packaging, updater readiness, and deeper native runtime operations are still open

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
- Remaining work:
  - decide whether future workbench, connector, or other newly shipped frontend surfaces should adopt the same runtime parser pattern when a real consumer lands, while keeping the current OpenAPI generation chain as the only contract source
  - decide whether the current frontend `dependency-cruiser` rules should widen after the present structure stabilizes, without expanding the tool to Python imports
  - decide whether feature-spec usage should grow beyond the current single real example, while keeping `AGENTS.md`, repo-local skills, roadmap, and status docs as the canonical governance layer

### Atomicity and composition follow-ons

- Goal: reduce the current brownfield orchestration hotspots so the repository more consistently follows the intended "small focused functions plus composed flows" structure without changing public behavior.
- Remaining work:
  - split `backend/services/workbench_execution_service.py` into smaller task-kind and source-kind executors so `execute_workbench_task()` stays as a dispatcher while retrieval, plan, and canvas flows move behind narrower seams
  - extract the current retrieval-heavy `_execute_retrieval_task()` path into separate helpers for source resolution, knowledge execution, web execution, event emission, and result finalization instead of keeping the full state machine in one function
  - break `backend/application/workbench.py` into narrower workbench application modules such as task lifecycle, source listing, and workspace-output/export use cases so create/retry/cancel/read/export flows do not continue to accumulate in one file
  - isolate the knowledge-augmented chat path in `backend/services/chat_service.py` behind a dedicated flow module so knowledge lookup, safeguard handling, knowledge-instruction composition, and stream handoff no longer live in one orchestration function
  - split `frontend/src/hooks/useChatSession.ts` into smaller controller hooks for session title derivation, history synchronization, and send-message orchestration so the current brownfield chat-session hook remains a composition root instead of a growing stateful hotspot
- Sequencing rule:
  - start with `backend/services/workbench_execution_service.py`, then `backend/application/workbench.py`, then `backend/services/chat_service.py`, and finally `frontend/src/hooks/useChatSession.ts` unless a user-facing bug forces a different order

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
  - a concrete orchestration spike for whether LangGraph improves plan -> retrieve -> synthesize -> follow-up loops, checkpointing, and human-review pauses without weakening the current authz/event/audit model
  - remote connector adapters behind the shared source registry

#### Phase 17E: project memory and connectors

- Goal: add project-scoped memory and external source plumbing once runtime foundations are ready.
- Remaining work:
  - explicit project scope and tenancy rules
  - connector registry and capability metadata
  - memory write/read boundaries that do not bypass authz/resource rules
  - read-only retrieval contracts before any write-capable connector path is enabled
  - keep any future LangGraph-style runtime integration behind the existing workbench/task boundary until project memory and connector authz semantics are mechanically proven

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

- Planning for future workbench, connector, project-memory, and other frontier surfaces should follow the canonical policy in [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md), especially the admission-gate and capability-gate rules.
- Shared runtime foundations still need to land before project-memory, connector, or broader frontend promises widen.
- Shared runtime foundations now build on the shipped object-store boundary plus the hosted/server Postgres runtime metadata posture in [POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md](../architecture/POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md), while local and desktop continue to default to SQLite.

---

## Decision pending

### `/api/knowledge/answers` semantic alignment

The product still needs a decision on whether `/api/knowledge/answers` should keep returning a raw retrieved snippet summary or move to the same LLM-synthesis behavior used by chat with `knowledge_document_ids`.

- Current state: chat synthesizes retrieved context; `/api/knowledge/answers` returns a snippet-style response
- Decision needed: keep the divergence and document it, or unify the answer semantics
- Impact: user expectations, API documentation, and the long-term retrieval UX
