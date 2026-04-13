# GOAT AI Roadmap Archive

This file preserves historical roadmap content that was removed from [ROADMAP.md](ROADMAP.md) on 2026-04-09. The active roadmap now tracks only unfinished work.

## 2026-04-13 roadmap cleanup

The live roadmap was trimmed again on 2026-04-13 so it stops carrying shipped
closeout detail, operator instructions, or engineering-policy reminders that
already have canonical homes elsewhere.

The following content moved out of the active roadmap in this cleanup:

- April 2026 audit-remediation closeout narrative and shipped evidence bullets,
  which now belong in this archive and in [PROJECT_STATUS.md](PROJECT_STATUS.md)
- landed governance-tooling pilot inventory, which remains tracked in
  [PROJECT_STATUS.md](PROJECT_STATUS.md)
- CI triage and admission-gate reminders that are already canonical in
  [OPERATIONS.md](../operations/OPERATIONS.md) and
  [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md)

## 2026-04-11 roadmap cleanup

The live roadmap was reduced again on 2026-04-11 so it only tracks open work.

The following landed or completed content was removed from the active roadmap and is preserved here or in [PROJECT_STATUS.md](PROJECT_STATUS.md):

- engineering quality uplift `P0` and `P1`
- landed slices from Phase 17A / 17B / 17C that had been described inline next to unfinished work
- landed Phase 18A sandbox baseline details
- landed desktop foundation phases 19 / 19A / 19B
- previously completed rationale blocks and "landed slice" notes that no longer belonged in an unfinished-work file

## Shipped v1.2.0

Phases 11-15 are complete and documented. The shipped release also includes the frontend control-surface polish landed on `main`.

- Phase 11: `ChatStreamService` owns SSE/tool/safeguard streaming; orchestration was split into `chat_orchestration.py`; `chat_service.py` became a thin entry point; architecture boundaries were tested.
- Phase 12: chart data-source policy, architecture guardrails, latency buckets, expanded black-box coverage, deploy post-checks, contract sync gate, and model capability cache landed.
- Frontend polish: composer menus, upload management panel, Plan badge, responsive chat shell, dark-mode-safe surfaces, unified options callout, and quieter history/message presentation landed on `main`.

## Archived phase closeouts

### Phase 13

Run, observe, recover work completed the operational baseline for the shared-host deployment. The major outcomes were numbered SQL migrations with checksum tracking, stable JSON error envelopes, `X-Request-ID` propagation, structured logging, Prometheus metrics, health/readiness split, Ollama retry and circuit-breaker hardening, optional idempotency keys, load-smoke tooling, chat size guardrails, session audit fields, CI hardening, and graceful-shutdown / rollback guidance.

### Phase 14

RAG-first expansion and vision capability were completed. The phase introduced the `/api/knowledge/*` contract family, persistent file storage under the then-current `GOAT_DATA_DIR` model, normalization and chunking for `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`, the local `simple_local_v1` vector index, retrieval-backed chat, image uploads via `/api/media/uploads`, and optional lexical reranking plus conservative query rewriting through `retrieval_profile`.

### Phase 15

Semantics and structure were completed. Phase 15 established the ubiquitous-language doc, typed policy objects, the `backend.application` structural migration, injectable `Clock`, append-only `session_messages` with legacy compatibility, scoped API keys plus optional owner scoping, lazy OpenTelemetry tracing, rate-limit policy/domain hardening, and the router/application boundary audit.

## Final closeout slices

These slices were the last deferred items before Phase 16 planning.

- 15.8: clock injection reached rate-limit and title/session-persist paths.
- 15.9: router/application boundary audit closed.
- 15.10: integration tests expanded to cover session history, knowledge ingestion/search, and retrieval-backed chat.
- 15.11: rate-limit policy/domain hardening completed and future-version session payloads now fail loudly on read.

## Phase 16 sequencing history

Phase 16 was re-sequenced so credential-backed authorization and tenancy context land before capability gates and storage evolution.

Historical note: the bullets immediately below preserve the labels that were current at
that point in the roadmap. The later storage-decoupling closeout reused `16C` for the
object/file-storage slice after the authz and capability work had already shipped.

- 16C: credential-backed authorization context and tenancy envelope.
- 16A: production-safe capability gates built on the 16C authz context.
- 16B: storage evolution after authz and resource boundaries are explicit.

### Phase 16B closeout

Phase 16B closed without a datastore-shape migration. The landed work standardized
persisted-resource ownership at repository boundaries and brought `knowledge` and
`media` onto explicit repository contracts, while preserving the SQLite-first,
single-writer deployment model. Any future schema or datastore change now requires a
new migration/compatibility/rollback decision package instead of extending Phase 16B
in place.

### Phase 16C storage closeout

The later storage-decoupling slice that reused the `16C` label is now complete. The
shipped outcome keeps SQLite metadata/runtime persistence in place while moving
persisted file/blob payloads behind one canonical object-store contract.

Completed in this closeout:

- storage-key-backed object persistence for knowledge source files, normalized text/metadata, vector-index payloads, media uploads, chat artifacts, and workspace-output export artifacts
- a local object-store default rooted at `GOAT_OBJECT_STORE_ROOT` (defaulting to `GOAT_DATA_DIR`) plus an optional `s3` backend behind the same application contract
- additive `storage_key` columns for `knowledge_documents`, `chat_artifacts`, and `media_uploads`, with compatibility for local file responses where a filesystem path still exists
- the canonical application/storage boundary is now documented in `docs/architecture/OBJECT_STORAGE_CONTRACT.md`
- operator runbooks for mixed local-vs-remote object-store modes, including backup/restore and rollback posture
- backend and black-box proof for upload, artifact download, media, and ingestion paths against the storage boundary

What stays open after this closeout:

- Phase 16D Postgres-backed runtime persistence
- hosted migration/compatibility/rollback posture for replacing the SQLite runtime metadata store

### Phase 16D runtime persistence closeout

Phase 16D is now fully out of the active roadmap. The shipped hosted/server posture
keeps local and desktop on SQLite while enabling Postgres-backed runtime metadata for
server deployments behind the existing repository boundaries.

Completed in this closeout:

- Alembic-owned Postgres runtime schema under `backend/alembic/`
- hosted/server repository adapters for sessions, `conversations`, artifacts,
  idempotency, knowledge, media, workbench, and sandbox runtime metadata
- deterministic SQLite snapshot export plus Postgres import and live parity tooling
- rollback and backup runbooks for the SQLite snapshot + object-store snapshot +
  hosted/server Postgres cutover path

What stays open after this closeout:

- shared runtime follow-ons under Phase 17
- future local or desktop storage-engine changes only if SQLite there becomes a real cost

### Engineering quality uplift P2 closeout

The industrial operating-model track is now fully archived. P0 and P1 had already
landed; P2 closed the remaining governance and evidence gaps without changing the
product feature roadmap.

Completed in this closeout:

- recurring quality evidence now captures backend/frontend coverage, security-review backlog, and optional performance-smoke summaries
- recurring security review evidence now records Python/Node/Rust audit state, Cargo audit exception review dates, and credential-rotation evidence inputs
- recurring fault-injection coverage now exercises upstream-unavailable, persistence-failure, recovery-drill, and desktop-boot-failure paths through a dedicated workflow
- artifact provenance remains in place through digest + SBOM + attestation-capable desktop provenance workflows
- architecture-drift and shared-boundary guardrails remain enforced through import-layer tests, contract-sync gates, desktop smoke coverage, and explicit engineering standards

What stays open after this closeout:

- target-platform desktop installer signing and updater readiness stay under Phase 19C
- ongoing module decomposition now belongs to the relevant feature/runtime phases instead of a standalone governance track

### Phase 17D closeout: canvas and artifact workspace baseline

Phase 17D is now fully out of the active roadmap. The shipped baseline turns
workbench outputs into first-class durable deliverables for the first `canvas`
slice without widening the public contract beyond the current workbench scope.

Completed in this closeout:

- `task_kind = canvas` no longer deterministically fails
- durable `workspace_output` persistence exists with `canvas_document` as the first shipped kind
- task status now returns typed `workspace_outputs`
- session restoration now returns visible workspace outputs through `GET /api/history/{session_id}`
- durable outputs can be reopened directly by id
- durable outputs can be listed by `session_id` or `project_id` restoration scope
- workspace outputs can now be exported to downloadable chat artifacts through `POST /api/workbench/workspace-outputs/{output_id}/exports`
- exported artifacts are linked back onto the durable output payload and task event timeline via `workspace_output.exported`

What stays open after this closeout:

- additional non-canvas workspace output kinds using the same typed output model
- broader workbench runtime work in real `web`, project memory, and connectors

The historical 16C checklist covered:

- credential/authz closeout work that originally used the 16C label before storage
  evolution was re-sequenced

- credential compatibility for `GOAT_API_KEY`, `GOAT_API_KEY_WRITE`, and `X-GOAT-Owner-Id`
- typed `PrincipalId`, `TenantId`, `Scope`, `AuthorizationDecision`, and `AuthorizationContext`
- a minimal credential registry with env fallback
- HTTP middleware / dependency binding for `AuthorizationContext`
- resource-level authorization in `backend.services.authorizer`
- structured allow/deny authz audit events
- additive `tenant_id` / `principal_id` columns for sessions and chat artifacts
- the same tenancy envelope extended to knowledge documents and media uploads
- docs and operations updates for multi-credential rollout

## Frontend backlog history

The remaining frontend work items were intentionally left roadmap-only until supporting runtime features exist:

- Plan Mode runtime integration
- Real Search / Browse mode
- Deep Research
- Canvas / artifact workspace
- Project-scoped knowledge / memory
- Connected apps / external sources

## Historical decision points

- `/api/knowledge/answers` still returned a raw snippet dump while chat used retrieval-backed synthesis.
- The project remained SQLite-first and single-writer for the data plane.
- Capability gates were modeled as runtime-vs-policy separation.
- Shared API keys stayed the current access-control baseline until Phase 16C.

## Reference snapshots

The following topics were kept in the live docs and are no longer repeated in the active roadmap:

- shipped state and release inventory: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- deployment and operational constraints: [OPERATIONS.md](../operations/OPERATIONS.md)
- ubiquitous language and domain semantics: [DOMAIN.md](../architecture/DOMAIN.md)
