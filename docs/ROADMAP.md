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

- Goal: extend the landed Docker-first synchronous sandbox without weakening the current operator/safety posture
- Current landed slice:
  - `POST /api/code-sandbox/exec` now executes short synchronous shell runs
  - durable execution and event rows are persisted in SQLite
  - `GET /api/code-sandbox/executions/{execution_id}` and `/events` expose auditability
  - network remains disabled by default
- Remaining priority items:
  - async run envelope for long-lived or queued executions
  - SSE log streaming for richer user feedback
  - multi-file workspace ergonomics beyond inline text seeding
  - allowlisted egress modes instead of all-or-nothing network disablement
  - alternate providers behind the same sandbox boundary (for example E2B/Daytona-style adapters)

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
