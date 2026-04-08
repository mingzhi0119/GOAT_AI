# Phase 14.5-15.6 Implementation Plan

## Summary

Implement the remaining roadmap as one coordinated program in this order: deliver a real Vision MVP first, then complete RAG-3 quality controls, then perform the Phase 15 semantic and structural overhaul in one refactor window, finishing with data normalization, AuthZ baseline, and optional-by-default distributed tracing.

Chosen defaults for this plan:
- Vision: real end-to-end MVP
- Structural migration: one-time refactor, not split
- Security vs tracing: observability-first, with minimal service-layer AuthZ and default-off OpenTelemetry

## Key Changes

### 1. Phase 14.5 Vision MVP

- Extend model capability detection so `/api/models/capabilities` distinguishes `completion`, `tools`, and `vision`.
- Add typed image attachment support to chat contracts:
  - `POST /api/chat` accepts `image_attachment_ids` or equivalent typed image references.
  - Add upload API for image attachments with `png`, `jpg/jpeg`, `webp`, explicit size limits, and returned attachment metadata.
- Add a media service that stores uploaded images under `GOAT_DATA_DIR/uploads/media/<attachment_id>/`, normalizes them, applies safe resize/format checks, and produces the Ollama-native message payload for vision-capable models.
- Keep chat routing explicit:
  - text-only path stays unchanged
  - vision path activates only when image attachments are present
  - if the selected model lacks vision support, return a sanitized client-visible error and do not silently drop the image
- Frontend:
  - add image upload UI with preview, remove action, upload state, and model capability hints near model selector / composer
  - show attached-image state in the chat composer before send
- Update API docs and operations docs with image size/type/time budget limits.

### 2. Phase 14.6 RAG-3 Quality Layer

- Add a dedicated reranker seam behind a protocol, but keep the first shipped implementation local and lightweight:
  - default implementation: score-preserving passthrough with optional lexical re-ordering
  - future heavier reranker remains swappable without changing router contracts
- Add a query-rewrite seam behind a protocol:
  - first implementation uses conservative normalization / rewrite only for clearly detectable retrieval failures
  - rewrite must be opt-in by retrieval profile, not always-on
- Add retrieval evaluation artifacts:
  - small checked-in eval dataset covering precision, citation relevance, and no-hit behavior
  - scripted regression runner that reports pass/fail against defined thresholds
- Add a quality gate in docs/status:
  - README and PROJECT_STATUS only call the system “RAG-ready” after eval thresholds pass and are documented.

### 3. Phase 15.1-15.3 Semantic + Structural Refactor

- Add `docs/DOMAIN.md` defining the canonical terms and boundaries for:
  - Session, Turn, KnowledgeDocument, ImageAttachment, ChartIntent, ChartSpec, ToolCall, SafeguardDecision, RetrievalDecision
- Introduce pure policy/domain objects before moving code:
  - `SafeguardPolicy`
  - `ChartDataProvenancePolicy`
  - invariant helpers for session payload validity, chart persistence, knowledge attachment consistency, and image attachment constraints
- Perform one-time package split:
  - `backend/application/` for orchestrators/use cases
  - `backend/domain/` for policies, invariants, contracts, value models
  - `backend/infrastructure/` for SQLite/Ollama/filesystem adapters
  - keep `backend/services/` only as compatibility facades or thin re-export shims during transition
- Update dependency boundaries and import-linter rules to reflect the new package graph.
- Publish `docs/SESSION_SCHEMA.md`:
  - current schema version
  - read N-/write N policy
  - legacy compatibility rules for older payloads
- Update AGENTS memory / standards docs so the stable ports list is explicit:
  - `SessionRepository`
  - `LLMClient`
  - telemetry sink
  - media storage / media normalizer
  - retriever / reranker / query rewriter
- Add testability primitives:
  - `Clock` abstraction for wall and monotonic time
  - injectable random source where jitter or IDs need deterministic tests
  - switch CI/docs to pytest as the primary test entry
  - create `__tests__/integration/` for temp-SQLite + TestClient integration runs without live Ollama

### 4. Phase 15.4-15.6 Data, Security, Observability

- Normalize session storage by introducing append-only `session_messages` while keeping dual-read compatibility from legacy JSON session payloads during cutover.
- Migration plan:
  - add new table via numbered SQL migration
  - write both normalized rows and current snapshot during transition
  - read path prefers normalized rows when present, otherwise falls back to legacy payload decode
- Minimal AuthZ baseline:
  - add service-layer checks that prevent cross-session mutation/read when session ownership metadata is present
  - document the scoped-key/session-ownership roadmap in Decision Log and OPERATIONS
  - do not attempt full multi-tenant IAM in this pass
- Add secrets hygiene automation:
  - CI secret scan step
  - CONTRIBUTING rule requiring `.env.example` review when new env vars are introduced
- Add optional distributed tracing:
  - W3C `traceparent` propagation
  - OpenTelemetry spans around HTTP request lifecycle, Ollama calls, retrieval pipeline, and file/media ingestion
  - tracing disabled by default with near-zero overhead when off
  - document one export path and one local verification flow

## Public API / Interface Changes

- `GET /api/models/capabilities` gains a stable vision capability signal.
- New image upload endpoint returns typed attachment metadata and status.
- `POST /api/chat` gains typed image attachment references in addition to existing message and knowledge document fields.
- History/session detail adds image attachment metadata when present.
- Session persistence format increments schema version again once normalized message storage becomes authoritative.
- Internal service interfaces become explicit protocols for safeguard, provenance, retrieval quality, media normalization, tracing sink, and clock/time access.

## Test Plan

- Backend black-box:
  - image upload success, invalid type, oversize, and unsupported-model failure
  - chat with image attachments on vision and non-vision models
  - rerank/rewrite retrieval flows, no-hit behavior, and citation ordering
  - history/session contract with image + knowledge attachments
- Pure unit tests:
  - `SafeguardPolicy`
  - `ChartDataProvenancePolicy`
  - invariants
  - reranker/query-rewrite seams
  - `Clock`-driven idempotency/rate-limit/title paths
- Integration:
  - temp SQLite migration path including `session_messages`
  - dual-read session compatibility
  - one end-to-end media ingest -> chat -> history flow
- Frontend:
  - image upload state, preview, remove, unsupported-model UI, and send flow
  - capability-aware composer behavior
- Contract sync:
  - regenerate and verify `docs/openapi.json` and `docs/api.llm.yaml`
- CI:
  - pytest as primary
  - frontend Vitest + build
  - import-linter
  - secret scan
  - API contract sync check

## Assumptions and Defaults

- Vision is limited to images only: `png`, `jpeg/jpg`, `webp`; no video.
- Media files stay on local filesystem under `GOAT_DATA_DIR`; no external blob store is introduced.
- Ollama remains the only inference backend; vision support is gated by model capability detection, not by model-name allowlists alone.
- Reranker and query rewrite ship with lightweight local implementations first; the architecture is prepared for stronger replacements later.
- The structural refactor is done in one deliberate branch/window, but compatibility facades remain until tests and docs are green.
- AuthZ remains minimal in this phase: service-layer ownership enforcement plus roadmap/documentation, not full account system rollout.
- Tracing is default-off and must not become a runtime dependency for normal startup.
