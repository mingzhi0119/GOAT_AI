# GOAT AI Roadmap

> Last updated: 2026-04-10
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This roadmap only tracks **unfinished work**. Completed phases and archived closeout notes live in [PROJECT_STATUS.md](PROJECT_STATUS.md), [OPERATIONS.md](OPERATIONS.md), [DOMAIN.md](DOMAIN.md), and [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md).

---

## Open Work

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
