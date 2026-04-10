# GOAT AI API Reference

Base path: `/api`

## Global behavior

- If `GOAT_API_KEY` is configured, every endpoint except `GET /api/health` and `GET /api/ready` requires `X-GOAT-API-Key`
- Responses include `X-Request-ID`
- Rate-limited requests return `429` with `Retry-After`
- Standard error shape:

```json
{
  "detail": "Human-readable error message",
  "code": "STABLE_ERROR_CODE",
  "request_id": "uuid"
}
```

## Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/ready` | Readiness (SQLite + optional Ollama) |
| `GET` | `/api/system/metrics` | Prometheus text metrics |
| `GET` | `/api/models` | List Ollama models |
| `GET` | `/api/models/capabilities` | Read capabilities for one model |
| `POST` | `/api/chat` | Stream chat SSE |
| `POST` | `/api/upload` | Stream upload analysis SSE |
| `POST` | `/api/upload/analyze` | Upload analysis as JSON |
| `POST` | `/api/knowledge/uploads` | Register and persist a knowledge upload |
| `GET` | `/api/knowledge/uploads/{document_id}` | Read one persisted knowledge upload |
| `POST` | `/api/knowledge/ingestions` | Start a knowledge ingestion job |
| `GET` | `/api/knowledge/ingestions/{ingestion_id}` | Read one ingestion job |
| `POST` | `/api/knowledge/search` | Search indexed knowledge chunks |
| `POST` | `/api/knowledge/answers` | Retrieval-backed answer with citations |
| `POST` | `/api/media/uploads` | Register a vision image attachment (PNG/JPEG/WebP) for `image_attachment_ids` on chat |
| `GET` | `/api/artifacts/{artifact_id}` | Download one generated chat artifact |
| `GET` | `/api/history` | List saved sessions |
| `GET` | `/api/history/{session_id}` | Read one session |
| `DELETE` | `/api/history` | Delete all sessions |
| `DELETE` | `/api/history/{session_id}` | Delete one session |
| `GET` | `/api/system/gpu` | GPU telemetry |
| `GET` | `/api/system/inference` | Rolling chat latency |
| `GET` | `/api/system/runtime-target` | Runtime target resolution |
| `GET` | `/api/system/features` | Capability-gated feature flags (config + host probe) |
| `POST` | `/api/code-sandbox/exec` | Code sandbox scaffold (503 when runtime gate closed; 403 when policy denies; 501 when enabled but not implemented) |
| `POST` | `/api/workbench/tasks` | Future agent/workbench task scaffold (503 when runtime gate closed; 501 when enabled but not implemented) |

## `GET /api/health`

Returns:

```json
{
  "status": "ok",
  "version": "1.2.0"
}
```

## `GET /api/ready`

Returns JSON `{ "ready": boolean, "checks": { ... } }`. HTTP `503` when any required check fails, for example SQLite is unreachable or the optional Ollama probe fails. Set `GOAT_READY_SKIP_OLLAMA_PROBE=1` to omit the Ollama HTTP check.

## `GET /api/system/metrics`

Returns Prometheus exposition text (`text/plain`). Requires `X-GOAT-API-Key` when `GOAT_API_KEY` is set. Includes `http_requests_total`, `http_request_duration_seconds`, `chat_stream_completed_total`, `ollama_errors_total`, `sqlite_log_write_failures_total`, `feature_gate_denials_total{feature,gate_kind,reason}` (when any), and **Section 14.7** retrieval counters: `knowledge_retrieval_requests_total{retrieval_profile,outcome}` and `knowledge_query_rewrite_applied_total{retrieval_profile}`.

## `GET /api/system/features`

Returns machine-readable capability state for optional/high-risk features.

Example:

```json
{
  "code_sandbox": {
    "policy_allowed": true,
    "allowed_by_config": false,
    "available_on_host": false,
    "effective_enabled": false,
    "deny_reason": "disabled_by_operator"
  },
  "workbench": {
    "agent_tasks": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "plan_mode": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "browse": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "deep_research": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "artifact_workspace": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "project_memory": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    },
    "connectors": {
      "allowed_by_config": false,
      "available_on_host": false,
      "effective_enabled": false,
      "deny_reason": "disabled_by_operator"
    }
  }
}
```

Notes:

- `code_sandbox.policy_allowed` remains caller-specific and separate from runtime readiness
- `workbench.*` advertises planned surfaces without claiming runtime support before execution is implemented
- frontend UI should use this endpoint to hide or disable unavailable surfaces instead of assuming that a visible button implies runtime support

## `GET /api/models`

Returns:

```json
{
  "models": ["gemma4:26b", "qwen3"]
}
```

If Ollama is unavailable, returns `503`.

## `GET /api/models/capabilities`

Query:

- `model`: exact Ollama model name

Returns:

```json
{
  "model": "qwen3",
  "capabilities": ["completion", "tools"],
  "supports_tool_calling": true,
  "supports_chart_tools": true
}
```

## `POST /api/chat`

Purpose:

- Stream LLM responses over SSE
- Persist session history when `session_id` is present
- Emit chart specs only from real native tool calls
- Apply lightweight safeguard blocking for clearly unsafe misuse

Request body:

```json
{
  "model": "gemma4:26b",
  "messages": [
    { "role": "user", "content": "Summarize Porter's Five Forces." }
  ],
  "knowledge_document_ids": ["doc-123"],
  "session_id": "session-123",
  "system_instruction": "Answer in bullet points.",
  "temperature": 0.3,
  "max_tokens": 512,
  "top_p": 0.9,
  "think": false
}
```

Optional `knowledge_document_ids` binds the turn to already indexed knowledge documents and switches chat to retrieval-backed generation for those documents. Legacy `file_context: true` messages remain readable for old sessions but are no longer the primary upload path.

Optional boolean **`think`** toggles Ollama thinking mode when the model supports it (`true` = thinking trace, `false` = quick path). Omit to use model defaults.

SSE event types:

- `thinking` (reasoning trace chunk; not merged into persisted assistant `content`)
- `token` (answer text chunk)
- `chart_spec`
- `artifact`
- `error`
- `done`

Thinking frame:

```text
data: {"type":"thinking","token":"..."}
```

Token frame:

```text
data: {"type":"token","token":"Hello"}
```

Chart frame:

```text
data: {"type":"chart_spec","chart":{"version":"2.0","engine":"echarts","kind":"line"}}
```

Artifact frame:

```text
data: {"type":"artifact","artifact_id":"art-123","filename":"brief.md","mime_type":"text/markdown","byte_size":128,"download_url":"/api/artifacts/art-123","source_message_id":"session-123:assistant:0"}
```

Error frame:

```text
data: {"type":"error","message":"AI service temporarily unavailable."}
```

Done frame:

```text
data: {"type":"done"}
```

Notes:

- Thinking-capable models may emit `thinking` before or interleaved with `token`; the web UI shows thinking in a collapsed disclosure; only `token` content is moderated by output safeguards and persisted as the assistant message body
- If the selected model does not support native tools, chat remains text-only
- Retrieval-backed chat reuses the normal chat streaming path; knowledge search builds bounded context for the model instead of streaming raw snippet dumps
- Unsafe prompts are converted into a safe refusal instead of passing through the raw request
- Unsafe model output is replaced server-side before streaming
- Downloadable generated files are emitted as `artifact` events and must be fetched from the server-provided `download_url`
- Optional `Idempotency-Key` is supported when `session_id` is present
- Duplicate `Idempotency-Key` plus the same payload replays the same SSE body and avoids duplicate session/conversation writes
- Reusing a key with a different payload returns `409` with `code = IDEMPOTENCY_CONFLICT`
- Capacity guardrails reject oversized requests with `422` when message count or total payload bytes exceed configured limits (`GOAT_MAX_CHAT_MESSAGES`, `GOAT_MAX_CHAT_PAYLOAD_BYTES`)

## `POST /api/upload`

Purpose:

- Persist and ingest a supported knowledge file
- Return readiness metadata for the next retrieval-backed chat turn

Form field:

- `file`: `.csv`, `.xlsx`, `.txt`, `.md`, `.pdf`, or `.docx`

SSE event types:

- `knowledge_ready`
- `error`
- `done`

Success frame:

```text
data: {"type":"knowledge_ready","filename":"sales.csv","document_id":"doc-123","ingestion_id":"ing-123","status":"completed","retrieval_mode":"knowledge_rag"}
```

Notes:

- This endpoint performs synchronous upload + ingestion for the first RAG slice
- The frontend should store `document_id` and pass it back through `knowledge_document_ids` on `POST /api/chat`
- This endpoint does not emit `chart_spec`

## `POST /api/upload/analyze`

Returns:

```json
{
  "filename": "sales.csv",
  "document_id": "doc-123",
  "ingestion_id": "ing-123",
  "status": "completed",
  "retrieval_mode": "knowledge_rag",
  "chart": null
}
```

## `POST /api/workbench/tasks`

Purpose:

- provide one stable future task-entry contract for Plan Mode, Browse, Deep Research, and Canvas
- validate request shape now while the runtime remains gated off

Request body:

```json
{
  "task_kind": "plan",
  "prompt": "Draft a research plan for the attached documents.",
  "session_id": "session-123",
  "project_id": "project-123",
  "knowledge_document_ids": ["doc-123"],
  "connector_ids": ["web"]
}
```

Notes:

- current deployments should expect `503` with `FEATURE_UNAVAILABLE` until the runtime exists
- if operators enable the feature family before task execution lands, the route returns `501`
- this endpoint is intentionally scaffold-only; it exists to stabilize the task envelope before frontend exposure

`chart` is retained only for backward compatibility.

Idempotency:

- Optional `Idempotency-Key` deduplicates retries
- Duplicate key plus the same file bytes returns the same JSON body
- Reusing a key with different file bytes returns `409` with `code = IDEMPOTENCY_CONFLICT`

## `POST /api/knowledge/uploads`

Persist a supported knowledge file and register document metadata.

Current behavior:

- Supported file types are `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`
- Raw files are stored under `GOAT_DATA_DIR/uploads/knowledge/<document_id>/original/`
- Returns `upload_id`, `document_id`, filename metadata, and `status = uploaded`

## `GET /api/knowledge/uploads/{document_id}`

Returns metadata for one persisted knowledge upload.

Current behavior:

- Returns `uploaded` before indexing and `indexed` after a successful ingestion
- Missing documents return `404` with `code = KNOWLEDGE_NOT_FOUND`

## `POST /api/knowledge/ingestions`

Start a knowledge ingestion job for one uploaded document.

Current behavior:

- Normalizes supported source types into text
- Chunks text into bounded sections
- Writes SQLite metadata rows plus a local persistent vector index (`simple_local_v1`)
- Returns an ingestion record with `status = completed` when the synchronous MVP path succeeds

## `GET /api/knowledge/ingestions/{ingestion_id}`

Read the current status of one ingestion attempt.

Current behavior:

- Returns `queued`, `running`, `completed`, or `failed`
- Includes `chunk_count` and optional `error_code` / `error_detail`
- Missing ingestions return `404` with `code = KNOWLEDGE_NOT_FOUND`

## `POST /api/knowledge/search`

Pure retrieval endpoint for indexed knowledge chunks.

Current behavior:

- Returns ranked hits with `document_id`, `chunk_id`, `filename`, `snippet`, and `score`
- Supports `document_ids` filtering and `top_k`
- `retrieval_profile` selects quality behavior: `default` (vector order; optional `GOAT_RAG_RERANK_MODE=lexical` for the default profile), `rag3_lexical` (lexical overlap rerank), `rag3_quality` (lexical rerank plus conservative whitespace query normalization). When rewrite applies, `effective_query` echoes the normalized query used for retrieval.

## `POST /api/knowledge/answers`

Retrieval-backed answer endpoint outside the chat session contract.

Current behavior:

- Returns a retrieval-backed answer plus citation payloads
- Defines explicit no-hit behavior: `No relevant context found in the indexed knowledge base.`
- When `document_ids` are provided and lexical retrieval misses, the first indexed chunks from those attached documents are used as a bounded fallback scope

## `POST /api/media/uploads`

Multipart upload of one image for vision chat.

Current behavior:

- Accepts **PNG**, **JPEG**, or **WebP**; validates size/type and persists under `GOAT_DATA_DIR` for the lifetime of the attachment id
- Returns `attachment_id`, `filename`, `mime_type`, `byte_size`, and optional `width_px` / `height_px`
- Use the `attachment_id` values in `image_attachment_ids` on `POST /api/chat` when the model reports Ollama **vision** capability; otherwise the chat request may fail validation (`422`, `VISION_NOT_SUPPORTED`)

## `GET /api/artifacts/{artifact_id}`

Download one persisted generated file from chat.

Current behavior:

- Returns the exact stored file with `Content-Disposition: attachment`
- Requires the same API key protection as the rest of `/api`
- When session-owner scoping is enabled, download access is limited to the matching owner scope
- Missing artifacts return `404`

## `GET /api/history`

Returns session metadata list:

```json
{
  "sessions": [
    {
      "id": "session-123",
      "title": "Porter analysis",
      "model": "gemma4:26b",
      "schema_version": 4,
      "created_at": "2026-04-07T14:00:00+00:00",
      "updated_at": "2026-04-07T14:01:30+00:00"
    }
  ]
}
```

## `GET /api/history/{session_id}`

Returns one normalized stored session:

```json
{
  "id": "session-123",
  "title": "Porter analysis",
  "model": "gemma4:26b",
  "schema_version": 4,
  "created_at": "2026-04-07T14:00:00+00:00",
  "updated_at": "2026-04-07T14:01:30+00:00",
  "chart_data_source": "uploaded",
  "chart_spec": { "version": "2.0", "engine": "echarts", "kind": "line" },
  "knowledge_documents": [
    {
      "document_id": "doc-123",
      "filename": "sales.csv",
      "mime_type": "text/csv"
    }
  ],
  "file_context": {
    "prompt": "[User uploaded tabular data for analysis] ..."
  },
  "messages": [
    { "role": "user", "content": "Explain Porter.", "artifacts": [] },
    {
      "role": "assistant",
      "content": "...",
      "artifacts": [
        {
          "artifact_id": "art-123",
          "filename": "brief.md",
          "mime_type": "text/markdown",
          "byte_size": 128,
          "download_url": "/api/artifacts/art-123",
          "source_message_id": "session-123:assistant:0"
        }
      ]
    }
  ]
}
```

Notes:

- `messages` contains only normalized chat roles: `user`, `assistant`, `system`
- `chart_spec`, `file_context`, and `knowledge_documents` are returned as dedicated fields instead of compatibility pseudo-roles
- `chart_data_source` indicates where chart data came from: `uploaded`, `demo`, or `none`
- Legacy stored sessions are still readable; compatibility decode lives in the backend storage codec, not the API contract

## `DELETE /api/history`

Returns `204 No Content`.

## `DELETE /api/history/{session_id}`

Returns `204 No Content`.

## `GET /api/system/gpu`

Returns real-time GPU telemetry, or a graceful fallback payload with `available=false` when telemetry cannot be read.

## `GET /api/system/inference`

Returns:

```json
{
  "chat_avg_ms": 842.3,
  "chat_sample_count": 20,
  "chat_p50_ms": 800.0,
  "chat_p95_ms": 1260.4,
  "first_token_avg_ms": 210.5,
  "first_token_sample_count": 20,
  "first_token_p50_ms": 190.2,
  "first_token_p95_ms": 320.1,
  "model_buckets": {
    "gemma4:26b": {
      "chat_avg_ms": 910.2,
      "chat_p50_ms": 870.0,
      "chat_p95_ms": 1410.3,
      "chat_sample_count": 15,
      "first_token_avg_ms": 220.8,
      "first_token_p50_ms": 205.3,
      "first_token_p95_ms": 340.0,
      "first_token_sample_count": 15
    }
  }
}
```

## `GET /api/system/runtime-target`

Returns deploy target resolution information:

```json
{
  "deploy_target": "auto",
  "current": {
    "mode": "server62606",
    "host": "127.0.0.1",
    "port": 62606,
    "base_url": "http://127.0.0.1:62606",
    "reason": "current process bound to server port"
  },
  "ordered_targets": [
    {
      "mode": "server62606",
      "host": "127.0.0.1",
      "port": 62606,
      "base_url": "http://127.0.0.1:62606",
      "reason": "server port is bindable"
    }
  ]
}
```

## `GET /api/system/features`

Returns machine-readable flags for optional high-risk features (see `docs/ENGINEERING_STANDARDS.md` Section 15). Example:

```json
{
  "code_sandbox": {
    "policy_allowed": false,
    "allowed_by_config": false,
    "available_on_host": false,
    "effective_enabled": false,
    "deny_reason": "disabled_by_operator"
  }
}
```

`policy_allowed` is evaluated per caller from the current request's authorization context; for `code_sandbox`, the scope is `sandbox:execute`. `deny_reason` when the **runtime** gate is closed is one of: `disabled_by_operator`, `docker_unavailable` (controlled enum; not raw exception text).

## `POST /api/code-sandbox/exec`

Scaffold endpoint: enforces the code-sandbox gate. When the **runtime** gate fails (operator off or Docker unavailable), returns **`503`** with `code: FEATURE_UNAVAILABLE` and a stable `detail` string mapped from `deny_reason`. When **policy** denies the caller (`sandbox:execute` missing), returns **`403`** with `code: FEATURE_DISABLED`. Returns **`501`** when the gate passes but execution is not implemented yet.

## Canonical sources

For machine-readable contract details, prefer:

- [openapi.json](openapi.json)
- [api.llm.yaml](api.llm.yaml)
- `__tests__/test_api_blackbox_contract.py`
