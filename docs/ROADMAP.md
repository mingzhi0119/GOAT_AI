# GOAT AI Roadmap

> Last updated: 2026-04-11
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This roadmap only tracks **unfinished work**. Completed phases and archived closeout notes live in [PROJECT_STATUS.md](PROJECT_STATUS.md), [OPERATIONS.md](OPERATIONS.md), [DOMAIN.md](DOMAIN.md), and [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md).

---

## Open Work

### Engineering quality uplift plan (`7/10 -> 9/10`)

This track is about preventing score regressions while raising the repo from "solid and reviewable" to "industrial-grade and continuously provable." Product work must not bypass these gates.

#### P0: stop score leaks and restore release confidence

Ship these before taking on net-new product promises that widen the runtime surface.

- [x] Fix any red CI-equivalent local gate before merge, especially frontend build failures.
- [x] Add and enforce coverage reporting plus fail-under thresholds for backend and frontend.
- [x] Close direct-test gaps for core decision-heavy modules:
  - `backend/services/knowledge_service.py`
  - `backend/services/workbench_execution_service.py`
  - history/workbench application paths
  - frontend persistence/layout/error-boundary and menu hooks/components
- [x] Eliminate visible encoding/garbled-text defects in user-facing or operator-facing paths.
- [x] Tighten credential handling:
  - stop relying on plain string equality for secrets
  - move toward hashed or otherwise non-reversible credential storage
  - require constant-time comparison where raw comparisons still exist
- [x] Add supply-chain gates for desktop/frontend dependencies:
  - CI-blocking `npm audit --audit-level=high`
  - CI-blocking `cargo audit` for `frontend/src-tauri/Cargo.lock`
  - a documented desktop artifact trust model that keeps unsigned packages internal/test-only until signing is in place
- [x] Reduce the highest-risk large-file hotspots by extracting focused submodules instead of adding more logic inline.
- [x] Add direct automated tests for delivery-critical scripts and desktop wrappers.
- Keep Rust migration work scoped to stable, systems-oriented boundaries during P0; do not begin broad business-logic rewrites before the quality gates above are green.

P0 exit criteria:

- `lint + format + test + build + contract + security` are all green for touched layers
- coverage is reported in CI and enforced by threshold
- core release flows no longer rely on "tests pass even though build is red"
- the worst correctness and security footguns are removed rather than documented away

#### P1: turn quality checks into durable release controls

- [x] Add staged release automation for at least a reproducible staging deploy and a documented production approval gate.
- [x] Turn `.github/CODEOWNERS` into real path ownership rather than bootstrap placeholders.
- [x] Version and store observability assets in-repo:
  - dashboards
  - alert rules
  - scrape config or equivalent metrics wiring
  - failure triage notes for common incidents
- [x] Introduce performance regression checks:
  - nightly or pre-release smoke/load validation
  - explicit budgets for first-token latency, full response latency, and desktop startup where relevant
- [x] Upgrade single-process reliability assumptions behind replaceable interfaces where scaling may grow:
  - rate limiting
  - idempotency
  - durable background execution
- [x] Add desktop smoke coverage for sidecar boot, health-wait handshake, and first-run diagnostics.
- [x] Exercise backup, restore, and rollback paths rather than treating them as documentation-only flows.

P1 exit criteria:

- releases are reproducible and reviewable
- operational alerts and dashboards exist for critical user-facing paths
- performance and deployment regressions are detectable before production
- ownership, release, and rollback paths are explicit enough to survive team hand-offs

#### P2: finish the move from mature codebase to industrial operating model

- Add signed-release and provenance/SBOM workflows for distributable artifacts.
- Establish vulnerability response, dependency-refresh cadence, and credential-rotation policy.
- Add targeted fault-injection or chaos-style validation for upstream timeouts, SSE interruption, file-system failure, and sidecar boot failure.
- Continue decomposing large multi-responsibility modules until typical feature changes stay localized.
- Extend architecture-drift controls to shared DTOs, desktop bridges, and future connector/runtime boundaries.
- Track quality trends over time:
  - coverage trend
  - CI stability
  - defect escape rate
  - performance trend
  - dependency vulnerability backlog

P2 exit criteria:

- artifacts are traceable, signed where applicable, and auditable
- reliability and security are proven by drills, not only by code inspection
- core engineering scores stay stable release over release instead of depending on individual contributors

Score target by end of this uplift track:

- Correctness: `>= 9/10`
- Testability: `>= 9/10`
- Maintainability: `>= 8.5/10`
- Readability: `>= 8/10`
- Architecture & Decoupling: `>= 9/10`
- Reliability: `>= 9/10`
- Performance: `>= 8.5/10`
- Security: `>= 9/10`
- Observability: `>= 9/10`
- Delivery Maturity: `>= 9/10`

### WSL-first local development baseline

Move day-to-day local development toward Linux semantics on developer Windows machines while preserving the Windows-native paths that are still required for packaging or operator workflows.

Why this track:

- Codex on Windows can run either in native PowerShell mode or through Windows Subsystem for Linux (WSL), and WSL is the closer match to this repo's Ubuntu CI and production behavior: [Codex app for Windows](https://developers.openai.com/codex/app/windows)
- this repository already treats Ubuntu as the production baseline and already requires WSL for Linux-targeted validation from Windows in `AGENTS.md` and `ENGINEERING_STANDARDS.md`
- local CI parity, shell-script behavior, Python packaging availability, and Linux-targeted desktop validation are all more predictable when the repo lives on the WSL filesystem instead of a Windows-mounted path

Decision:

- default local development baseline on Windows should become **WSL + repository stored inside the WSL filesystem**
- Windows-native development should remain only for flows that are required by Windows-only tooling or are materially more reliable on Windows

#### P0: establish WSL as the default working copy for Windows developers

- Define the canonical WSL workspace location:
  - default distro: `Ubuntu`
  - default repo root: `~/dev/GOAT_AI`
  - do not treat `/mnt/<drive>/...` working copies as the recommended default for active development
- Document the migration steps for an existing Windows checkout:
  - create the WSL workspace directory
  - clone the repository directly inside WSL rather than editing a Windows-mounted copy from Linux
  - move or re-clone any local virtualenv, npm cache assumptions, and Rust target assumptions so they are owned by the Linux environment
- Standardize the baseline Linux toolchain for this repo inside WSL:
  - Python `3.14`
  - `uv`
  - Node `24.x`
  - Rust stable toolchain
  - `cargo-audit`
  - repo-required Ubuntu packages for the Tauri/Linux desktop path
- Define Codex usage for Windows developers:
  - open the WSL-hosted repo from `\\wsl$\<distro>\home\<user>\dev\GOAT_AI` in the Codex app when using the Windows UI
  - prefer running the agent in WSL for repository work that targets backend, scripts, CI parity, or Linux artifacts
  - keep using the repo-local WSL skills in `.agents/skills` for Linux-targeted validation from Windows-hosted Codex sessions
- Publish the initial Windows-native exception list:
  - Windows installer generation and validation
  - `scripts/install_desktop_prereqs.ps1`
  - `deploy.ps1`
  - WebView2 / MSVC / Windows shell integration checks
- Exit criteria:
  - a new Windows developer can get a working WSL-hosted checkout without relying on tribal knowledge
  - the canonical repo path for Windows developers is documented as WSL-native, not `/mnt/<drive>`
  - Codex usage instructions are explicit enough that WSL becomes the default path instead of an optional aside

#### P1: make WSL the default validation path for Linux-facing work

- Update developer-facing docs so routine commands are presented in WSL/Linux form first, with Windows-native exceptions called out explicitly instead of mixed into the main path.
- Align local validation guidance around WSL-hosted execution for:
  - `python -m tools.*`
  - `pytest`
  - `npm ci`, `vitest`, and `vite build`
  - shell scripts such as `deploy.sh`, `watchdog.sh`, and `healthcheck.sh`
  - Linux desktop sidecar builds and `cargo test` parity for the Linux desktop path
- Add migration notes for local state and tooling:
  - how to recreate Python environments inside WSL
  - how to reinstall Node dependencies inside WSL
  - how to handle Docker/Ollama endpoint expectations when the app is launched from WSL instead of native Windows
- Make the Windows-native exception list operational rather than descriptive:
  - define which validations must still be re-run on Windows after a WSL-first implementation change
  - keep Windows desktop packaging and installer verification as a distinct release/dev flow, not part of the default inner loop
- Add a lightweight onboarding or smoke checklist that proves the WSL environment can run the repo's baseline commands from a fresh machine.
- Exit criteria:
  - the default local inner loop for Windows contributors is WSL-hosted
  - Linux-targeted regressions are no longer routinely debugged from PowerShell first
  - Windows-native paths are explicit exceptions rather than a parallel default

#### P2: harden the split between WSL-default development and Windows-only exceptions

- Audit and reduce remaining documentation drift that still implies Windows-native development is the normal path for Linux-facing work.
- Add or refine automated checks and smoke workflows that reinforce the split:
  - WSL-first local validation guidance for CI-equivalent commands
  - repeatable Windows-only packaging/installer validation guidance for desktop releases
- Evaluate whether helper scripts should gain explicit WSL/bootstrap wrappers for common setup tasks so developers do not need to hand-translate commands.
- Keep the Windows-native exception list narrow and versioned:
  - desktop installer creation and verification
  - PowerShell-specific deployment or rollback drills
  - Windows shell/runtime integration checks
- Revisit this baseline only if a future product direction meaningfully increases the amount of native Windows-only application logic.
- Exit criteria:
  - WSL is the stable, documented default for Windows-hosted development
  - Windows-native development is used intentionally for a short list of justified cases
  - Codex, docs, and local workflow expectations all point developers to the same default environment

### Immediate priority queue

These are already-visible or already-contracted capabilities that still have missing runtime implementation. Prioritize them before adding new product surfaces.

1. **Canvas task/runtime**
   - Public contract already accepts `task_kind = canvas`
   - Current state: task is accepted, then deterministically fails as not implemented
   - Why next: this is already in the durable task enum and should not remain a "known value that always fails" indefinitely
2. **Workbench web retrieval**
   - Public contract already exposes the `web` source in `/api/workbench/sources`
   - Current state: declarative source exists, but `runtime_ready = false` and no executor is attached
   - Why next: browse/deep-research semantics will remain partial until public-web retrieval is real
3. **Artifact workspace**
   - Public capability slot already exists in `/api/system/features`
   - Current state: no first-class workspace-output model beyond inline task results and chat artifacts
4. **Project memory**
   - Public capability slot already exists in `/api/system/features`
   - Current state: no project-scoped memory model or API surface is implemented
5. **Connectors**
   - Public capability slot already exists in `/api/system/features`
   - Current state: no runtime-ready connector-backed retrieval source is implemented

Sequencing rule:

- finish or explicitly narrow already-open capability surfaces first
- do not add new UI promises on top of these incomplete runtime seams

### Phase 16B: storage evolution

Revisit datastore changes only after authorization and resource boundaries are explicit.

- Goal: define the next storage shape without weakening current single-instance guarantees.
- Exit criteria: migration strategy, compatibility strategy, and rollback strategy are all defined before implementation.
- Dependencies: must wait on the Phase 16 authz envelope and any resulting resource scoping rules.
- Planning artifact: [`STORAGE_EVOLUTION_DECISION_PACKAGE.md`](STORAGE_EVOLUTION_DECISION_PACKAGE.md)

### Phase 17: agent/workbench runtime scaffolding

Prioritize the backend/runtime seams for the next frontend surfaces before exposing them in the SPA.

- Goal: ship a capability-discovered workbench/task envelope that can safely back future Plan Mode, Browse, Deep Research, Canvas, project memory, and connectors.
- Why this shape: modern coding/research products converge on capability discovery, long-running task envelopes, memory/context layers, and connector/tool registries instead of hard-wiring isolated UI buttons.
- Reference implementations:
  - OpenAI Codex product notes emphasize a threaded/task-oriented runtime, approvals, artifacts, and integrations rather than one-off pages: [Unlocking the Codex Harness](https://openai.com/index/unlocking-the-codex-harness/)
  - Claude Code docs expose slash commands, hierarchical `CLAUDE.md` memory, MCP-based connectors/tools, and custom subagents as first-class runtime concepts: [Claude Code overview](https://docs.anthropic.com/en/docs/claude-code/overview), [MCP](https://docs.anthropic.com/en/docs/claude-code/mcp), [Slash commands](https://docs.anthropic.com/en/docs/claude-code/slash-commands)
- Exit criteria:
  - `GET /api/system/features` advertises the workbench capability family without claiming unavailable runtime support
  - one stable task-entry contract exists for future long-running agent work
  - docs and error semantics make clear that unavailable runtime returns `503` / `FEATURE_UNAVAILABLE`

### Phase 17B: Plan Mode runtime integration

- Goal: server-side plan/task orchestration beyond the now-landed durable task skeleton (`POST /api/workbench/tasks` + `GET /api/workbench/tasks/{task_id}`)
- Current landed slice:
  - `task_kind = plan` now executes through a minimal in-process runner
  - polling returns durable `queued/running/completed/failed`
  - completed plan tasks expose a minimal inline markdown result on `GET`
  - `GET /api/workbench/tasks/{task_id}/events` now exposes a durable lifecycle timeline (`task.queued`, `task.started`, `task.completed`, `task.failed`)
- Backend prerequisites:
  - safe cancellation / retry semantics
  - execution beyond `plan`

### Phase 17 shared runtime foundations

Use the same runtime primitives across 17C/17D/17E instead of building isolated feature-specific endpoints.

- Why this shape:
  - OpenAI deep research uses background execution plus tool-driven retrieval (`web search`, `file search`, remote MCP) rather than a single request/response search route: [Deep research guide](https://developers.openai.com/api/docs/guides/deep-research)
  - MCP standardizes external data sources, tools, and workflows behind one connector surface instead of one-off app integrations: [MCP introduction](https://modelcontextprotocol.io/docs/getting-started/intro)
  - LangGraph durable execution guidance emphasizes persisted progress, replay safety, and side-effect boundaries for long-running workflows: [Durable execution](https://docs.langchain.com/oss/javascript/langgraph/durable-execution)
- Required shared primitives:
  - durable task timeline / checkpoints, not status-only rows
  - source registry abstraction for web, knowledge, and future connector-backed retrieval
  - typed workspace outputs that stay distinct from the task row itself
- Sequencing rule:
  - land shared runtime foundations first
  - then expose Browse / Deep Research / Canvas / project memory behaviors on top of them

### Phase 17C: Browse and Deep Research runtime

- Goal: add retrieval/browse execution primitives before exposing real Search/Browse and Deep Research in the UI
- Current landed slice:
  - `GET /api/workbench/sources` exposes a declarative source registry
  - current visible sources are `web` and `knowledge`
  - `web` is registered for future browse/deep-research work but remains runtime-unready
  - `knowledge` is runtime-ready and already reuses existing retrieval/authz boundaries
  - task creation now validates requested source ids through the shared registry instead of treating `connector_ids` as opaque strings
  - `task_kind = browse` and `task_kind = deep_research` now execute a minimal retrieval pipeline
  - execution writes `retrieval.sources_resolved`, `retrieval.step.completed`, and `retrieval.step.skipped` events into the durable task timeline
  - completed browse/research tasks return markdown plus citations gathered from runtime-ready sources
- Backend prerequisites:
  - bounded multi-step task execution backed by durable task events instead of direct request/response only
  - staged safety boundaries for public-web research vs private-source retrieval
  - actual web execution and remote-connector adapters behind the new registry

### Phase 17D: canvas and artifact workspace

- Goal: make artifacts/work products first-class so research and planning outputs can be revisited and iterated
- Priority: highest remaining workbench runtime gap after code sandbox because `canvas` is already present in the public task-kind contract
- Backend prerequisites:
  - typed workspace-output metadata beyond chat-only downloadable files
  - task-to-output linkage (artifact and future canvas document refs)
  - history/session restoration rules for workbench outputs

### Phase 17E: project memory and connectors

- Goal: add project-scoped memory and external source plumbing after task/runtime contracts exist
- Priority: after canvas and real web retrieval because these capabilities are already advertised as slots but do not yet have runnable backends
- Backend prerequisites:
  - explicit project scope and tenancy rules
  - connector registry / capability metadata
  - memory write/read boundaries that do not bypass existing authz/resource rules
  - read-only retrieval contracts for browse/research connectors before any write-capable integration is enabled

### Phase 18 follow-ons: code sandbox beyond the MVP

- Goal: extend the landed Docker-first sync+async sandbox without weakening the current operator/safety posture
- Current landed slice:
  - `POST /api/code-sandbox/exec` now executes provider-backed shell runs in `sync` and `async` modes
  - durable execution, event, and log rows are persisted in SQLite
  - `GET /api/code-sandbox/executions/{execution_id}`, `/events`, and `/logs` expose status, auditability, and replayable stdout/stderr
  - Docker remains the default isolated backend; `localhost` is available as a trusted-dev fallback with weaker isolation
- Remaining priority items:
  - cancel / retry semantics for async runs
  - multi-file workspace ergonomics beyond inline text seeding
  - allowlisted egress modes instead of all-or-nothing network disablement
  - alternate providers behind the same sandbox boundary (for example E2B/Daytona-style adapters)
  - richer terminal / PTY UX beyond replayable chunked logs

### Phase 18B: Rust sandbox supervisor

- Goal: move the most systems-heavy sandbox supervision responsibilities into a Rust runtime component while preserving the existing HTTP/API contract.
- Why this route:
  - process lifecycle control, timeout enforcement, cancellation, log streaming, and resource-boundary enforcement are a better fit for a memory-safe systems language than for growing Python orchestration code
  - the sandbox boundary is already a separable runtime seam, so it is a safer migration target than higher-level chat or domain logic
- Planned scope:
  - execution supervisor process or library written in Rust
  - child-process lifecycle management
  - timeout and cancellation enforcement
  - stdout/stderr event streaming and bounded buffering
  - workspace and egress policy enforcement at the supervisor boundary
- Non-goals for this phase:
  - no rewrite of chat, knowledge, authz, or other application/domain logic into Rust
  - no public API contract expansion solely because the runtime implementation changed
- Sequencing:
  - begin after P0 engineering gates are green enough to prove parity
  - keep the existing Python-facing adapter thin and contract-stable during rollout
- Exit criteria:
  - the Rust supervisor can back the existing execution contract without changing API semantics
  - parity tests cover success, failure, timeout, cancellation, and log replay behavior
  - rollout can be feature-gated so the Python path remains a fallback until the Rust path is proven

### Phase 19: desktop app packaging and native distribution

- Goal: turn GOAT AI into a first-class desktop app for Windows, macOS, and Linux instead of relying on "open localhost in a browser" as the primary local experience.
- Chosen implementation route: **Tauri 2 desktop shell + bundled Python sidecar backend**.
- Why this route:
  - the current frontend already uses **React + Vite**, which Tauri explicitly supports as an existing web stack
  - Tauri 2 has first-class packaging/distribution for **Windows, macOS, and Linux**
  - Tauri supports bundling **external binaries / sidecars**, and its docs explicitly call out **Python CLI applications or API servers bundled using PyInstaller**
  - this keeps the existing FastAPI/Ollama/runtime architecture largely intact instead of rewriting the backend into Rust or Electron/Node-only process code
- Why this is preferred over alternatives:
  - **plain PyInstaller only** is not enough for the desired product shape because it can freeze a Python process, but it does not give us the modern native desktop shell, updater story, permissions model, or polished installer UX by itself
  - **Electron Forge** remains a viable fallback, but it adds a heavier runtime and is not the preferred first route unless Tauri sidecar integration or WebView constraints become blockers
- Official reference implementations:
  - Tauri 2 homepage and positioning: [Tauri 2](https://tauri.app/)
  - Tauri sidecars / bundled external binaries: [Embedding External Binaries](https://tauri.app/develop/sidecar/)
  - Tauri distribution targets: [Distribute](https://v2.tauri.app/distribute/)
  - Tauri updater plugin: [Updater](https://v2.tauri.app/plugin/updater/)
  - PyInstaller packaging constraints for Python sidecars: [PyInstaller Manual](https://pyinstaller.org/en/stable/)
  - Electron Forge as fallback desktop shell: [Packaging Your Application](https://www.electronjs.org/docs/latest/tutorial/tutorial-packaging), [Makers](https://www.electronforge.io/config/makers)

### Phase 19A: desktop shell scaffold

- Goal: add a native desktop shell around the existing SPA without changing the API contract first.
- Planned route:
  - create a `desktop/` or `src-tauri/` application shell using **Tauri 2**
  - load the existing Vite frontend in dev and the built frontend bundle in release
  - start the backend as a managed sidecar process instead of asking the user to run `uvicorn` manually
  - define an app bootstrap handshake:
    - launch sidecar
    - wait for `/api/health`
    - then show the main window
- Exit criteria:
  - dev mode launches one native window instead of requiring a browser tab
  - desktop shell can start and stop the local backend reliably

### Phase 19B: packaged backend sidecar

- Goal: bundle the Python backend so end users do not need to install Python manually.
- Landed:
  - `goat_ai.desktop_sidecar` now provides a desktop-friendly backend entrypoint
  - `python -m tools.build_desktop_sidecar` builds a per-platform frozen sidecar with **PyInstaller**
  - Tauri packaging now bundles that binary via `externalBin`
  - release-mode desktop builds launch the bundled sidecar and wait for `/api/health` before showing the main window
  - packaged desktop launches now move SQLite/data writes into the platform app-local-data directory instead of the repository root
- Current Windows packaging output:
  - `npm run desktop:build` now produces both a `.msi` installer and an NSIS `setup.exe`
- Follow-on work:
  - validate and ship the same frozen-sidecar path on macOS and Linux
  - improve first-run diagnostics for missing Ollama or misconfigured local runtimes
  - harden release build automation around signed installer pipelines
- Important packaging constraint:
  - **PyInstaller is not a cross-compiler**, so Windows, macOS, and Linux artifacts must each be built on the target OS (or an equivalent VM/runner for that OS)
- Exit criteria:
  - Windows, macOS, and Linux each produce a working packaged app that can launch the frozen backend sidecar locally
  - first-run failure states are explicit when Ollama is missing or unreachable

### Phase 19C: platform installers, signing, and updates

- Goal: ship real installable desktop artifacts instead of ad hoc zips or developer-only bundles.
- Planned distribution targets:
  - **Windows**: NSIS or MSI installer
  - **macOS**: DMG for direct download
  - **Linux**: AppImage first, then `.deb` / `.rpm` as needed
- Planned route:
  - add platform icons, bundle metadata, and installer branding
  - add **code signing** for Windows and macOS before public distribution
  - add Tauri updater only after signed installer flow is stable
  - decide whether offline WebView2 embedding is needed for Windows deployments that cannot assume internet access
  - ship and maintain a documented prerequisite/bootstrap story instead of relying on tribal knowledge:
    - **end-user runtime bootstrap** for `WebView2` and external local inference runtime (`Ollama` for the current architecture)
    - **developer bootstrap** for Rust toolchain + Windows build tools
    - one-click scripts for Windows and equivalent documented flows for macOS/Linux
- Exit criteria:
  - signed installers are produced in CI/release workflows
  - updater strategy is documented and wired for the signed desktop build only
  - prerequisite installation paths are explicit enough that new users can complete setup without manual package hunting

### Phase 19D: desktop-native UX and local-runtime operations

- Goal: make the packaged app behave like a real desktop product rather than a wrapped website.
- Planned route:
  - add desktop-native status for backend/Ollama readiness
  - add durable desktop shell log sinks and log viewing instead of relying on transient process stdout/stderr
  - keep workbench outputs and future desktop-native artifacts discoverable from the per-user app data directory
  - add basic desktop settings for:
      - Ollama endpoint selection
      - model/runtime diagnostics
      - local data directory reveal/open
  - keep code sandbox disabled by default in packaged builds unless the selected provider/runtime is explicitly available and documented
- Exit criteria:
  - desktop app can be installed, launched, updated, and diagnosed without dropping users into raw terminal workflows

### Phase 19E: Rust desktop runtime bridge

- Goal: harden packaged-app startup and local-runtime operations by moving desktop process supervision deeper into the native Rust layer that already exists in the Tauri shell.
- Why this route:
  - sidecar lifecycle management, startup handshake, restart/backoff behavior, log sinks, and first-run diagnostics are desktop/runtime concerns rather than frontend concerns
  - the Tauri shell already provides a natural Rust host boundary, so this improves reliability without forcing a rewrite of the SPA or backend API semantics
- Planned scope:
  - native sidecar boot coordination
  - `/api/health` and readiness handshake before window reveal
  - native log sink wiring for shell and sidecar diagnostics
  - restart/backoff and clearer first-run failure reporting
  - desktop-safe local data and path handling at the Rust boundary
- Non-goals for this phase:
  - no rewrite of the SPA into Rust
  - no rewrite of backend business logic solely for desktop packaging
- Sequencing:
  - start only after P0 release-confidence work is in place
  - prefer incremental migration of startup/diagnostic responsibilities instead of replacing the entire desktop flow at once
- Exit criteria:
  - packaged desktop launches remain contract-compatible with the current backend sidecar
  - first-run diagnostics, startup timing, and failure recovery are measurably better than the current shell-managed flow
  - desktop startup, shutdown, and recovery paths are covered by repeatable smoke checks

### UI surfaces waiting on backend/runtime

These items should remain roadmap-only in the frontend until the corresponding backend/runtime slice exists.

- Cloud model API integration for non-local inference backends
- Real Search / Browse mode
- Deep Research
- Canvas / artifact workspace
- Project-scoped knowledge / memory
- Connected apps / external sources

---

## Dependencies / Constraints

- Phase 16A capability gates now build on the completed credential-backed authorization context and tenancy envelope from Phase 16C.
- Capability gates should continue to separate runtime unavailability from policy denial.
- Storage evolution must preserve the current single-writer / SQLite-first operational contract unless a separate decision log changes that assumption.
- Search, research, canvas, connector UI, and future cloud model selection should not expose fake capabilities before the backend/runtime can actually support them.

---

## Decision Pending

### `/api/knowledge/answers` semantic alignment

The product still needs a decision on whether `/api/knowledge/answers` should keep returning a raw retrieved snippet summary or move to the same LLM synthesis behavior used by chat with `knowledge_document_ids`.

- Current state: chat synthesizes retrieved context; `/api/knowledge/answers` returns a snippet-dump style response.
- Decision needed: keep the divergence and document it, or unify the answer semantics across both endpoints.
- Impact: this affects user expectations, API documentation, and the long-term shape of the retrieval UX.
