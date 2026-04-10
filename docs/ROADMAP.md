# GOAT AI Roadmap

> Last updated: 2026-04-09
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This roadmap only tracks **unfinished work**. Completed phases and archived closeout notes live in [PROJECT_STATUS.md](PROJECT_STATUS.md), [OPERATIONS.md](OPERATIONS.md), [DOMAIN.md](DOMAIN.md), and [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md).

---

## Open Work

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

### Phase 17A: workbench contract and capability discovery

- Backend-first scaffold:
  - shared `workbench` capability family in `GET /api/system/features`
  - stable task envelope for `plan`, `browse`, `deep_research`, and `canvas`
  - disabled-by-default operator flag plus runtime-gated stub route
- Non-goals:
  - no fake task execution
  - no frontend exposure beyond capability-aware hiding/disabled states

### Phase 17B: Plan Mode runtime integration

- Goal: server-side plan/task orchestration with durable task ids, status polling/streaming, and artifact references
- Backend prerequisites:
  - task state model
  - task event stream or polling contract
  - safe cancellation / retry semantics

### Phase 17C: Browse and Deep Research runtime

- Goal: add retrieval/browse execution primitives before exposing real Search/Browse and Deep Research in the UI
- Backend prerequisites:
  - source registry abstraction for web and connector-backed retrieval
  - citation model shared by chat and research outputs
  - bounded multi-step task execution rather than direct request/response only

### Phase 17D: canvas and artifact workspace

- Goal: make artifacts/work products first-class so research and planning outputs can be revisited and iterated
- Backend prerequisites:
  - artifact/workspace metadata beyond chat-only downloadable files
  - task-to-artifact linkage
  - history/session restoration rules for workbench outputs

### Phase 17E: project memory and connectors

- Goal: add project-scoped memory and external source plumbing after task/runtime contracts exist
- Backend prerequisites:
  - explicit project scope and tenancy rules
  - connector registry / capability metadata
  - memory write/read boundaries that do not bypass existing authz/resource rules

### UI surfaces waiting on backend/runtime

These items should remain roadmap-only in the frontend until the corresponding backend/runtime slice exists.

- Plan Mode runtime integration
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
