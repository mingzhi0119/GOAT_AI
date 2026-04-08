# RAG Architecture Decision Draft

> Status: draft  
> Last updated: 2026-04-08

---

## Scope

This document fixes the first-round architecture decisions for Retrieval-Augmented Generation (RAG) in GOAT AI:

- final priority order
- API route draft
- SQLite schema direction
- local file layout
- first-version vector storage selection principles

This draft assumes the current repo state described in [ROADMAP.md](ROADMAP.md): the project is not yet a RAG baseline implementation, and the current `/api/upload` flow remains file-context extraction for prompt injection rather than knowledge-base indexing.

---

## 1. Final priority order

### Decision

RAG should land **before full multimodal expansion**.

The recommended sequence is:

| Priority | Track | Reason |
|----------|-------|--------|
| **P0** | Close remaining Phase 13 stability work | RAG needs stable readiness, error codes, metrics, and deploy behavior. |
| **P1** | **RAG-0**: contract and storage design | Prevents `/api/upload` from turning into a mixed upload/index side-effect endpoint. |
| **P2** | **RAG-1**: ingestion MVP | Establishes document lifecycle, chunking, embeddings, and persistence. |
| **P3** | **RAG-2**: retrieval + answer MVP | Produces the first true retrieval-backed user feature with citations. |
| **P4** | **Vision MVP** only if isolated and capability-gated | Image understanding is useful, but it should not delay the knowledge subsystem. |
| **P5** | **RAG-3**: rerank, query rewrite, evaluation | Quality work is meaningful only after ingestion + retrieval are real. |
| **P6** | **Video multimodal** | Highest pipeline complexity and least aligned with the current product center of gravity. |

### Why this order

- The current product is still text/chat-centric, so RAG reuses more of the existing backend and API foundation than video does.
- RAG fits the current engineering strengths: service layering, SSE orchestration, typed models, readiness/metrics, and session history.
- Video requires a larger media pipeline, higher storage/compute costs, and more operational surface area.
- A narrow image MVP can still happen before later RAG quality work, but it should be explicitly bounded and must not displace the RAG ingestion/retrieval track.

### Non-decision

This draft does **not** recommend folding RAG into the current multimodal phase. They should be tracked separately even if release timing overlaps.

---

## 2. API route draft

### Design rule

RAG must be a **separate API family**. Do not overload the existing `/api/upload` contract with hidden indexing behavior.

### Route family

All first-version endpoints should live under a dedicated prefix:

- `POST /api/knowledge/uploads`
- `GET /api/knowledge/uploads/{upload_id}`
- `POST /api/knowledge/ingestions`
- `GET /api/knowledge/ingestions/{ingestion_id}`
- `POST /api/knowledge/search`
- `POST /api/knowledge/answers`
- `GET /api/knowledge/documents`
- `GET /api/knowledge/documents/{document_id}`
- `DELETE /api/knowledge/documents/{document_id}`

### Route responsibilities

#### `POST /api/knowledge/uploads`

Purpose: persist the raw user file and register document metadata.

Request:

- multipart file
- optional `source_label`
- optional `tags`

Response:

- `upload_id`
- `document_id`
- `status` = `uploaded`
- file metadata

Notes:

- This endpoint only stores the file and metadata.
- It does not parse, chunk, embed, or index.

#### `GET /api/knowledge/uploads/{upload_id}`

Purpose: expose upload metadata and storage result.

Response:

- upload/document metadata
- storage status
- checksum

#### `POST /api/knowledge/ingestions`

Purpose: start a typed ingestion job from an uploaded document.

Request:

- `document_id`
- `parser_profile`
- `chunking_profile`
- `embedding_profile`
- optional `force_reindex`

Response:

- `ingestion_id`
- `status` = `queued` or `running`

Notes:

- This is the contract boundary for parsing, chunking, embeddings, and vector writes.
- The backend may execute synchronously in v1 if needed, but the API contract should still model ingestion as its own job/status object.

#### `GET /api/knowledge/ingestions/{ingestion_id}`

Purpose: retrieve ingestion progress and errors.

Response:

- `status`
- `document_id`
- counters such as `chunk_count`
- `error_code`
- `error_detail`
- timestamps

#### `POST /api/knowledge/search`

Purpose: pure retrieval API.

Request:

- `query`
- optional `document_ids`
- optional `top_k`
- optional retrieval profile

Response:

- ranked chunk hits
- document metadata
- score fields
- citation payloads

Notes:

- No answer generation happens here.
- This endpoint is the retrieval black-box contract.

#### `POST /api/knowledge/answers`

Purpose: retrieval-backed answer generation outside the chat session contract.

Request:

- `query`
- optional `document_ids`
- optional `top_k`
- optional `session_id`

Response:

- `answer`
- `citations`
- retrieval summary
- optional `request_id`

Notes:

- This endpoint is useful for testing and black-box verification even if the UI later prefers chat-first integration.

#### `GET /api/knowledge/documents`

Purpose: list stored knowledge documents and current index status.

#### `GET /api/knowledge/documents/{document_id}`

Purpose: fetch one document’s metadata, latest ingestion state, and index summary.

#### `DELETE /api/knowledge/documents/{document_id}`

Purpose: soft-delete or tombstone a document and remove its active vector records from the searchable index.

### Chat integration rule

`POST /api/chat` remains a chat API.

If chat uses retrieval later, it should do so through a backend `RetrieverService` / `AnswerOrchestrator` dependency, not by sharing route logic with the knowledge endpoints. This preserves thin routers and keeps chat and knowledge as separate contracts.

---

## 3. SQLite schema direction

### Design rule

SQLite should store **metadata, lifecycle state, lineage, and citations**, while the first-version vector index remains a distinct storage concern even if it also lives on local disk.

### Table set

#### `knowledge_documents`

One logical source document.

Suggested columns:

- `id TEXT PRIMARY KEY`
- `source_type TEXT NOT NULL`
- `original_filename TEXT NOT NULL`
- `mime_type TEXT NOT NULL`
- `sha256 TEXT NOT NULL`
- `storage_path TEXT NOT NULL`
- `byte_size INTEGER NOT NULL`
- `status TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `deleted_at TEXT NULL`

Indexes:

- unique on `sha256` only if duplicate suppression is desired
- index on `status`
- index on `created_at`

#### `knowledge_ingestions`

One ingestion/indexing attempt for a document.

Suggested columns:

- `id TEXT PRIMARY KEY`
- `document_id TEXT NOT NULL`
- `status TEXT NOT NULL`
- `parser_profile TEXT NOT NULL`
- `chunking_profile TEXT NOT NULL`
- `embedding_profile TEXT NOT NULL`
- `vector_backend TEXT NOT NULL`
- `started_at TEXT NULL`
- `completed_at TEXT NULL`
- `error_code TEXT NULL`
- `error_detail TEXT NULL`
- `chunk_count INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Foreign keys:

- `document_id -> knowledge_documents(id)`

Indexes:

- index on `document_id`
- index on `status`
- index on `created_at`

#### `knowledge_chunks`

Chunk metadata and citation text for one ingestion.

Suggested columns:

- `id TEXT PRIMARY KEY`
- `ingestion_id TEXT NOT NULL`
- `document_id TEXT NOT NULL`
- `chunk_index INTEGER NOT NULL`
- `text_content TEXT NOT NULL`
- `text_hash TEXT NOT NULL`
- `token_count INTEGER NULL`
- `char_start INTEGER NULL`
- `char_end INTEGER NULL`
- `page_number INTEGER NULL`
- `section_label TEXT NULL`
- `vector_ref TEXT NOT NULL`
- `created_at TEXT NOT NULL`

Foreign keys:

- `ingestion_id -> knowledge_ingestions(id)`
- `document_id -> knowledge_documents(id)`

Indexes:

- unique on `(ingestion_id, chunk_index)`
- index on `document_id`
- index on `vector_ref`

#### `knowledge_retrieval_events`

Audit and evaluation-friendly retrieval trace.

Suggested columns:

- `id TEXT PRIMARY KEY`
- `query_text TEXT NOT NULL`
- `request_context_json TEXT NULL`
- `top_k INTEGER NOT NULL`
- `retrieval_profile TEXT NOT NULL`
- `rerank_profile TEXT NULL`
- `result_count INTEGER NOT NULL`
- `created_at TEXT NOT NULL`

Notes:

- Keep this table lightweight in v1.
- It exists to support quality measurement and operational troubleshooting.

#### `knowledge_retrieval_hits`

Per-result linkage for one retrieval event.

Suggested columns:

- `id TEXT PRIMARY KEY`
- `retrieval_event_id TEXT NOT NULL`
- `chunk_id TEXT NOT NULL`
- `rank_position INTEGER NOT NULL`
- `raw_score REAL NULL`
- `rerank_score REAL NULL`
- `created_at TEXT NOT NULL`

Foreign keys:

- `retrieval_event_id -> knowledge_retrieval_events(id)`
- `chunk_id -> knowledge_chunks(id)`

### Explicit v1 exclusions

Do not add all of the following in v1 unless a concrete use case appears:

- document ACL tables
- tenant tables
- background worker queue tables beyond ingestion status
- chunk-level version graph tables

Keep the first schema narrow and evolve through migrations.

---

## 4. Local file layout

### Design rule

Files must be stored in a deterministic local layout under a dedicated app data root, not mixed into the current ad hoc upload path.

### Proposed data root

- config key: `GOAT_DATA_DIR`
- default location: project-local `data/`

Within `GOAT_DATA_DIR`, add:

- `uploads/`
- `knowledge/`
- `vector_index/`
- `tmp/`

### Proposed layout

```text
data/
  uploads/
    knowledge/
      <document_id>/
        original/
          source.bin
        normalized/
          extracted.txt
          metadata.json
  vector_index/
    <backend_name>/
      active/
      staging/
  tmp/
    knowledge/
      <ingestion_id>/
```

### Storage rules

- Raw uploaded files live under `data/uploads/knowledge/<document_id>/original/`.
- Parser outputs and normalized text live under `data/uploads/knowledge/<document_id>/normalized/`.
- Vector index artifacts live under `data/vector_index/<backend_name>/`.
- Temporary chunking/embedding build artifacts live under `data/tmp/knowledge/<ingestion_id>/` and can be cleaned after success.

### Why this layout

- Keeps raw files, normalized text, and index artifacts separate.
- Makes backup/restore easier to reason about.
- Allows the vector backend to be replaced without moving raw document storage.
- Works on both Windows dev and Ubuntu prod with `pathlib.Path`.

---

## 5. First-version vector storage selection principles

### Decision

Version 1 should use a **local persistent vector backend** that works inside the current single-node, no-root deployment model.

### Hard constraints

- no root access
- shared host deployment
- current ops model is SQLite + local filesystem + app-managed process lifecycle
- backup/restore must remain understandable and scriptable
- the app must start cleanly even if the vector index is empty and rebuild is required

### Selection principles

The first backend should satisfy all of the following:

- embeddable as a Python library or local process-free component
- persistent on local disk
- no dependency on Redis, Postgres extensions, Milvus, Qdrant server, or other extra service processes for v1
- supports delete/update by document or chunk reference
- acceptable query latency at project scale
- rebuildable from SQLite metadata + stored source files if index artifacts are lost

### Preferred v1 stance

Use a **filesystem-backed local vector index** as the primary searchable store, and keep SQLite as the system of record for:

- document metadata
- ingestion state
- chunk text and citation payloads
- vector references

This means:

- SQLite is the control plane.
- The vector index is the retrieval plane.

### Explicit non-recommendations for v1

Do not start with:

- a remote managed vector database
- a multi-process local vector server that needs separate supervision
- storing full vectors directly in the existing chat/session tables
- coupling retrieval correctness to an in-memory-only index

### Upgrade path

If scale or operational needs later justify a dedicated vector store, the migration path should be:

1. keep the API contract unchanged
2. keep `RetrieverService` and `VectorIndex` as the seam
3. reindex from `knowledge_chunks` + stored documents into the new backend
4. preserve citation payloads and retrieval black-box behavior

---

## 6. Strong decoupling rules

These rules are mandatory for implementation:

- routers validate and translate HTTP only
- ingestion logic lives in services, not routes
- parsing, chunking, embeddings, vector writes, retrieval, reranking, and answer composition each get their own typed boundary
- `POST /api/upload` and `POST /api/knowledge/uploads` remain distinct contracts
- chat history/session tables must not become the hidden source of truth for knowledge documents
- startup validates storage roots and vector backend configuration loudly
- black-box API tests define behavior before internal implementation is treated as stable

### Suggested backend interfaces

- `DocumentStorage`
- `DocumentParser`
- `ChunkingService`
- `EmbeddingService`
- `VectorIndex`
- `RetrieverService`
- `RerankerService`
- `KnowledgeRepository`
- `AnswerOrchestrator`

---

## 7. Implementation entry recommendation

The first implementation PR should do only this:

1. add typed models and service interfaces
2. add the SQLite migration for `knowledge_documents`, `knowledge_ingestions`, and `knowledge_chunks`
3. add `POST /api/knowledge/uploads`
4. add `POST /api/knowledge/ingestions`
5. add `GET /api/knowledge/ingestions/{ingestion_id}`
6. persist raw files and normalized text without yet wiring retrieval into chat

That keeps the first slice small, verifiable, and reversible.

---

## 8. Summary

The project should treat RAG as the next major subsystem after Phase 13 stability, and it should be implemented as a dedicated API family with strict service boundaries. Raw files belong on local disk, lifecycle metadata belongs in SQLite, and the first vector backend should be a local persistent store that fits the current no-root single-node deployment model.
