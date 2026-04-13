# GOAT AI API Reference

Base path: `/api`

## Global behavior

- If `GOAT_API_KEY` is configured, every endpoint except `GET /api/health` and `GET /api/ready` requires `X-GOAT-API-Key`
- If `GOAT_API_KEY_WRITE` is configured, mutating routes (`POST`, `PATCH`, `DELETE`) require the write key or an equivalent write-scoped credential; otherwise the API returns `403` with `code = AUTH_WRITE_KEY_REQUIRED`
- If `GOAT_REQUIRE_SESSION_OWNER` is enabled, chat and history routes require `X-GOAT-Owner-Id`; owner-mismatched protected reads resolve as `404` to avoid leaking resource existence
- The bundled browser UI exposes these protected headers in `Settings -> Protected access` and stores them locally in the browser for subsequent API calls
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
| `PATCH` | `/api/history/{session_id}` | Rename one session |
| `DELETE` | `/api/history` | Delete all sessions |
| `DELETE` | `/api/history/{session_id}` | Delete one session |
| `GET` | `/api/system/gpu` | GPU telemetry |
| `GET` | `/api/system/inference` | Rolling chat latency |
| `GET` | `/api/system/runtime-target` | Runtime target resolution |
| `GET` | `/api/system/features` | Capability-gated feature flags (config + host probe) |
| `GET` | `/api/system/desktop` | Desktop runtime diagnostics for packaged installs |
| `POST` | `/api/code-sandbox/exec` | Execute one sandbox run in `sync` or `async` mode |
| `GET` | `/api/code-sandbox/executions/{execution_id}` | Read one persisted sandbox execution |
| `POST` | `/api/code-sandbox/executions/{execution_id}/cancel` | Cancel one queued sandbox execution |
| `POST` | `/api/code-sandbox/executions/{execution_id}/retry` | Retry one terminal sandbox execution as a new durable run |
| `GET` | `/api/code-sandbox/executions/{execution_id}/events` | Read one persisted sandbox execution timeline |
| `GET` | `/api/code-sandbox/executions/{execution_id}/logs` | Stream replayable sandbox logs over SSE |
| `POST` | `/api/workbench/tasks` | Create and enqueue a durable workbench task |
| `GET` | `/api/workbench/sources` | List declarative workbench retrieval sources |
| `GET` | `/api/workbench/workspace-outputs` | List durable workspace outputs by session or project scope |
| `GET` | `/api/workbench/workspace-outputs/{output_id}` | Read one durable workspace output |
| `POST` | `/api/workbench/workspace-outputs/{output_id}/exports` | Export one durable workspace output into a downloadable artifact |
| `GET` | `/api/workbench/tasks/{task_id}` | Read one durable workbench task status |
| `POST` | `/api/workbench/tasks/{task_id}/cancel` | Cancel one queued durable workbench task |
| `POST` | `/api/workbench/tasks/{task_id}/retry` | Retry one terminal durable workbench task as a new queued task |
| `GET` | `/api/workbench/tasks/{task_id}/events` | Read one durable workbench task event timeline |

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
    "allowed_by_config": true,
    "available_on_host": true,
    "effective_enabled": true,
    "provider_name": "docker",
    "isolation_level": "container",
    "network_policy_enforced": true,
    "deny_reason": null
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
    "artifact_exports": {
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
- `code_sandbox.provider_name`, `isolation_level`, and `network_policy_enforced` describe the currently selected backend contract; `localhost` is a weaker trusted-dev fallback than Docker
- `workbench.*` is reported per capability and per caller; the same deployment may return different `allowed_by_config`, `effective_enabled`, and `deny_reason` values for different credentials
- `workbench.agent_tasks`, `browse`, `deep_research`, and `connectors` are write-scoped capability views; `artifact_workspace` and `project_memory` are read-scoped capability views; `artifact_exports` is the export-scoped capability view for turning durable outputs into downloadable artifacts
- `workbench.browse` / `workbench.deep_research` report capability-level readiness, not source-specific readiness; use `GET /api/workbench/sources` to decide whether the global `web` source itself is runnable
- `workbench.artifact_workspace` reflects the shipped baseline for durable workspace output visibility
- `workbench.artifact_exports` reflects the shipped export-to-artifact linkage and stays denied unless the caller also has `workbench:export` plus `artifact:write`
- `workbench.project_memory` remains a caller-visible placeholder for future widening and should stay `deny_reason = "not_implemented"` until a real runtime exists
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
  "capabilities": ["completion", "tools", "vision"],
  "supports_tool_calling": true,
  "supports_chart_tools": true,
  "supports_vision": true,
  "supports_thinking": false,
  "context_length": 32768
}
```

`supports_chart_tools` tracks native tool support, while `supports_vision`, `supports_thinking`, and `context_length` expose additional Ollama capability metadata when discoverable.

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
  "theme_style": "urochester",
  "temperature": 0.3,
  "max_tokens": 512,
  "top_p": 0.9,
  "think": "medium",
  "plan_mode": false
}
```

Optional `knowledge_document_ids` binds the turn to already indexed knowledge documents and switches chat to retrieval-backed generation for those documents. Legacy `file_context: true` messages remain readable for old sessions but are no longer the primary upload path.

Optional **`think`** accepts `true`, `false`, or `"low" | "medium" | "high"` when the model supports Ollama thinking mode. Omit it to use model defaults.

Optional boolean **`plan_mode`** asks the system prompt to plan before answering.

Optional **`theme_style`** accepts `classic`, `urochester`, or `thu`. When no explicit `GOAT_SYSTEM_PROMPT` override is configured, the backend uses it to select the default assistant persona:

- `classic`: standard general-purpose assistant
- `urochester`: slightly business-oriented assistant from the University of Rochester Simon Business School
- `thu`: slightly research/engineering-oriented assistant from Tsinghua University

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
- `download_url` should be treated as an opaque API route; clients should not infer filesystem paths or storage-provider URLs from it
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

- provide one stable task-entry contract for Plan Mode, Browse, Deep Research, and Canvas
- create a durable queued record and enqueue best-effort execution

Request body:

```json
{
  "task_kind": "plan",
  "prompt": "Draft a research plan for the attached documents.",
  "session_id": "session-123",
  "project_id": "project-123",
  "knowledge_document_ids": ["doc-123"],
  "source_ids": ["knowledge"]
}
```

Returns `202 Accepted`:

```json
{
  "task_id": "wb-123",
  "task_kind": "plan",
  "status": "queued",
  "created_at": "2026-04-10T18:00:00+00:00"
}
```

Notes:

- current deployments return `503` with `FEATURE_UNAVAILABLE` when the shared workbench runtime is operator-disabled
- callers need `workbench:write` to create tasks, plus any source-specific read scopes required by the requested sources
- task creation persists a durable queued task, then workbench launches best-effort in-process execution
- the task record is stored in SQLite so polling survives process restarts
- terminal task statuses are `completed`, `failed`, and `cancelled`
- lifecycle updates are also written to a durable event timeline for future long-running browse/research execution
- `source_ids` are resolved through the shared source registry instead of being treated as opaque strings
- legacy `connector_ids` is still accepted as a deprecated alias for `source_ids`
- when `knowledge_document_ids` are attached, the task implicitly includes the `knowledge` source even if the caller omitted it from `source_ids`
- when `browse` or `deep_research` omits both `source_ids` and `knowledge_document_ids`, the task defaults to the global `web` source
- every resolved source must explicitly advertise the requested `task_kind`; mixed source sets that include an incompatible source now fail fast with `422`
- `browse` and `deep_research` now fail fast with `422` when no runtime-ready retrieval source is available to the caller
- request shape is intentionally forward-compatible for future task execution and output linkage
- current task-kind behavior:
  - `plan`: completed markdown result
  - `browse`: bounded multi-step plan -> retrieve -> synthesize execution over runtime-ready sources; completed results may include citations and additive timeline detail
  - `deep_research`: same bounded multi-step runtime with a larger step budget and evidence surface; it is step-limited research, not open-ended autonomous long-horizon execution
  - `canvas`: completes with a durable `canvas_document` workspace output plus inline markdown result content; that output can later be exported to a downloadable artifact
- unknown or caller-invisible source ids return `422`
- missing workbench scopes or denied requested-source scopes return `403`

## `GET /api/workbench/sources`

Returns the caller-visible retrieval sources that workbench tasks may reference.

Current behavior:

- callers need `workbench:read`
- returns `200` with `sources`
- current built-in source ids are:
  - `web`
  - `knowledge`
- each source includes:
  - `source_id`
  - `display_name`
  - `kind`
  - `scope_kind`
  - `capabilities`
  - `task_kinds`
  - `read_only`
  - `runtime_ready`
  - optional `deny_reason`
  - `description`
- `knowledge` is hidden unless the caller can read knowledge resources
- `web` is runtime-ready by default when `GOAT_WORKBENCH_WEB_PROVIDER=duckduckgo`
- `web` reports `runtime_ready = false` with `deny_reason = "disabled_by_operator"` when `GOAT_WORKBENCH_WEB_PROVIDER=disabled`
- current public-web retrieval is experimental and uses the DDGS DuckDuckGo-style provider to return bounded search-result evidence
- callers without `workbench:read` receive `403`

## `GET /api/workbench/workspace-outputs`

Lists visible durable workspace outputs for one restoration scope.

Query parameters:

- `session_id`: restore outputs linked to one session
- `project_id`: restore outputs linked to one project

Current behavior:

- callers need `workbench:read`
- provide exactly one of `session_id` or `project_id`
- returns `200` with `outputs`
- unauthorized or non-existent scope members are simply omitted from the list
- current output kinds are:
  - `canvas_document`
- each output also surfaces any linked downloadable `artifacts` that were created from it

Example:

```json
{
  "outputs": [
    {
      "output_id": "wbo-123",
      "output_kind": "canvas_document",
      "title": "Draft canvas",
      "content_format": "markdown",
      "content": "# Draft canvas\n\n## Objective\n- ...",
      "created_at": "2026-04-10T18:00:02+00:00",
      "updated_at": "2026-04-10T18:00:02+00:00",
      "metadata": {
        "editable": true
      },
      "artifacts": []
    }
  ]
}
```

## `GET /api/workbench/workspace-outputs/{output_id}`

Reads one durable workspace output by stable id.

Current behavior:

- callers need `workbench:read`
- returns `200` with one typed output payload
- missing workbench read scope returns `403`
- missing or caller-invisible output ids return `404`
- this is the canonical reopen/read endpoint for a durable workbench output

## `POST /api/workbench/workspace-outputs/{output_id}/exports`

Exports one durable workspace output into a downloadable artifact and links that
artifact back onto the output payload.

Request body:

```json
{
  "format": "markdown",
  "filename": "draft-canvas.md"
}
```

Current behavior:

- callers need `workbench:read`, `workbench:export`, and `artifact:write`
- returns `201` with a normal `ChatArtifact` payload
- missing export scopes return `403`
- missing or caller-invisible output ids return `404`
- invalid export requests return `422`, for example when `filename` has an extension that does not match `format`
- exported artifacts are appended to the output's `artifacts` list and are also visible through the existing `GET /api/artifacts/{artifact_id}` download route
- exported artifact bytes use the same configured object-store boundary as chat-generated artifacts
- the returned `download_url` remains an opaque API download route rather than a direct backend-storage URL

## `GET /api/workbench/tasks/{task_id}`

Returns the current durable state for one workbench task.

Current behavior:

- callers need `workbench:read`
- returns `200` with `task_id`, `task_kind`, `status`, `created_at`, `updated_at`, optional `error_detail`, optional `result`, and `workspace_outputs`
- completed `plan` tasks return:

```json
{
  "task_id": "wb-123",
  "task_kind": "plan",
  "status": "completed",
  "created_at": "2026-04-10T18:00:00+00:00",
  "updated_at": "2026-04-10T18:00:02+00:00",
  "error_detail": null,
  "result": {
    "format": "markdown",
    "content": "## Goal\n- ..."
  }
}
```

- completed `browse` / `deep_research` tasks may also include citations in `result`:

```json
{
  "task_id": "wb-456",
  "task_kind": "browse",
  "status": "completed",
  "created_at": "2026-04-10T18:00:00+00:00",
  "updated_at": "2026-04-10T18:00:02+00:00",
  "error_detail": null,
  "result": {
    "format": "markdown",
    "content": "## Browse Summary\n- Query: ...",
    "citations": [
      {
        "document_id": "doc-123",
        "chunk_id": "chunk-123",
        "filename": "strategy.txt",
        "snippet": "Porter Five Forces explains competitive pressure.",
        "score": 0.98
      }
    ]
  }
}
```

- web-backed citations reuse the `KnowledgeCitation` shape for now:
  - `document_id` and `chunk_id` both carry the canonical URL
  - `filename` carries the human-readable result title
  - `snippet` carries the normalized result excerpt

- completed `canvas` tasks also include durable typed outputs:

```json
{
  "task_id": "wb-789",
  "task_kind": "canvas",
  "status": "completed",
  "created_at": "2026-04-10T18:00:00+00:00",
  "updated_at": "2026-04-10T18:00:02+00:00",
  "error_detail": null,
  "result": {
    "format": "markdown",
    "content": "# Draft canvas\n\n## Objective\n- ..."
  },
  "workspace_outputs": [
    {
      "output_id": "wbo-123",
      "output_kind": "canvas_document",
      "title": "Draft canvas",
      "content_format": "markdown",
      "content": "# Draft canvas\n\n## Objective\n- ...",
      "created_at": "2026-04-10T18:00:02+00:00",
      "updated_at": "2026-04-10T18:00:02+00:00",
      "metadata": {
        "editable": true
      },
      "artifacts": [
        {
          "artifact_id": "art-123",
          "filename": "draft-canvas.md",
          "mime_type": "text/markdown",
          "byte_size": 128,
          "download_url": "/api/artifacts/art-123",
          "source_message_id": "canvas-session-1:assistant:0"
        }
      ]
    }
  ]
}
```

- queued and running tasks return `result = null`
- failed and cancelled tasks return `result = null` plus a stable `error_detail`
- `workspace_outputs` is filtered per output using the same visibility rules as the history/output listing surfaces; a visible task can still return an empty `workspace_outputs` list when some linked outputs are caller-hidden
- missing workbench read scope returns `403`
- missing or caller-invisible task ids return `404`
- the same runtime gate still applies: if workbench is disabled for the deployment, the route returns `503` with `FEATURE_UNAVAILABLE`

## `POST /api/workbench/tasks/{task_id}/cancel`

Cancels one visible `queued` workbench task.

Current behavior:

- callers need `workbench:write`
- only `queued` tasks can be cancelled
- success returns `200` with the normal task status payload and `status = cancelled`
- cancelled tasks return `result = null` and `error_detail = "Task cancelled before execution."`
- the response applies the same per-output visibility filter as `GET /api/workbench/tasks/{task_id}`
- missing workbench write scope returns `403`
- running or terminal tasks return `409` with `code = RESOURCE_CONFLICT`
- missing or caller-invisible task ids return `404`

## `POST /api/workbench/tasks/{task_id}/retry`

Creates a brand-new durable task from one visible terminal task.

Current behavior:

- callers need `workbench:write`
- only terminal tasks can be retried: `completed`, `failed`, or `cancelled`
- retry always creates a new `task_id`; the original task is preserved and only gains a lineage event
- the new task reuses the original `task_kind`, `prompt`, `session_id`, `project_id`, `knowledge_document_ids`, and connector/source request shape, but it re-resolves sources and stores the current caller auth snapshot
- success returns `202 Accepted` with the same accepted-task payload shape as `POST /api/workbench/tasks`
- missing workbench write scope or source-read scope returns `403`
- retry now fails with `422` if the re-resolved source set no longer supports the original task kind, even when the source ids are still visible
- queued or running tasks return `409` with `code = RESOURCE_CONFLICT`
- missing or caller-invisible task ids return `404`

## `GET /api/workbench/tasks/{task_id}/events`

Returns the current durable event timeline for one workbench task.

Current behavior:

- callers need `workbench:read`
- returns `200` with `task_id` and ordered `events`
- each event includes:
  - `sequence`
  - `event_type`
  - `created_at`
  - optional `status`
  - optional `message`
  - optional `metadata`
- current lifecycle event names are:
  - `task.queued`
  - `task.started`
  - `task.cancelled`
  - `task.retry_requested`
  - `task.retry_created`
  - `retrieval.sources_resolved`
  - `research.plan.created`
  - `retrieval.step.started`
  - `retrieval.step.completed`
  - `retrieval.step.skipped`
  - `research.follow_up.scheduled`
  - `research.synthesis.completed`
  - `workspace_output.created`
  - `workspace_output.exported`
- `task.completed`
- `task.failed`
- missing workbench read scope returns `403`
- missing or caller-invisible task ids return `404`
- the same runtime gate still applies: if workbench is disabled for the deployment, the route returns `503` with `FEATURE_UNAVAILABLE`

## `POST /api/knowledge/uploads`

Persist a supported knowledge file and register document metadata.

Current behavior:

- Supported file types are `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`
- Raw files are persisted through the configured object store using a canonical `storage_key`; `local` stores use `GOAT_OBJECT_STORE_ROOT`, while `s3` stores use the configured bucket/prefix
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
- Persists normalized text/metadata and the current `simple_local_v1` vector-index payloads through the configured object store while SQLite keeps the metadata rows
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

- Accepts **PNG**, **JPEG**, or **WebP**; validates size/type and persists through the configured object store for the lifetime of the attachment id
- Returns `attachment_id`, `filename`, `mime_type`, `byte_size`, and optional `width_px` / `height_px`
- Use the `attachment_id` values in `image_attachment_ids` on `POST /api/chat` when the model reports Ollama **vision** capability; otherwise the chat request may fail validation (`422`, `VISION_NOT_SUPPORTED`)

## `GET /api/artifacts/{artifact_id}`

Download one persisted generated file from chat.

Current behavior:

- Returns the exact stored file with `Content-Disposition: attachment`
- Resolves the payload by persisted `storage_key`; local backends may stream directly from disk, while remote backends proxy object bytes through the API response
- Requires the same API key protection as the rest of `/api`
- When session-owner scoping is enabled, download access is limited to the matching owner scope
- clients should treat the route as the stable download contract even when the storage backend changes
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
- `workspace_outputs` contains visible durable workbench outputs linked through tasks that were created with the same `session_id`
- `workspace_outputs` is only populated when the caller also has `workbench:read`; otherwise the history response still succeeds and returns an empty list
- each workspace output may include linked downloadable `artifacts` exported from that durable output
- session-linked restoration assumes that session id already exists in persisted history; workbench does not create chat-session stubs on its own in this slice
- `chart_data_source` indicates where chart data came from: `uploaded`, `demo`, or `none`
- Legacy stored sessions are still readable; compatibility decode lives in the backend storage codec, not the API contract

## `PATCH /api/history/{session_id}`

Request body:

```json
{
  "title": "Renamed Title"
}
```

Current behavior:

- Returns `204 No Content` after the title is updated
- Empty titles are rejected with `422`
- When owner scoping is active, rename follows the same visibility rules as history reads and deletes

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

Returns machine-readable flags for optional high-risk features (see `docs/standards/ENGINEERING_STANDARDS.md` Section 15). Example:

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

`policy_allowed` is evaluated per caller from the current request's authorization context; for `code_sandbox`, the scope is `sandbox:execute`. For `workbench`, each entry is also a caller-scoped capability view rather than a deployment-global mirror: read-scoped callers can still see `artifact_workspace` as enabled while `agent_tasks`, `browse`, or `deep_research` remain denied, and `artifact_exports` remains denied until the caller also has export scopes. `deny_reason` when the **runtime** gate is closed is one of: `disabled_by_operator`, `docker_unavailable`, `localhost_unavailable`, or `not_implemented` (controlled enum; not raw exception text).

## `GET /api/system/desktop`

Returns desktop-only diagnostics used by the packaged shell settings panel. Non-desktop or server deployments return `desktop_mode: false` and leave the desktop-specific fields empty instead of pretending desktop capabilities are available.

Example:

```json
{
  "desktop_mode": true,
  "backend_base_url": "http://127.0.0.1:62606",
  "readiness_ok": false,
  "failing_checks": ["ollama"],
  "skipped_checks": [],
  "code_sandbox_effective_enabled": true,
  "workbench_effective_enabled": false,
  "app_data_dir": "C:/Users/alice/AppData/Local/GOAT AI",
  "runtime_root": "C:/Users/alice/AppData/Local/GOAT AI",
  "data_dir": "C:/Users/alice/AppData/Local/GOAT AI/data",
  "log_dir": "C:/Users/alice/AppData/Local/GOAT AI/logs",
  "log_db_path": "C:/Users/alice/AppData/Local/GOAT AI/chat_logs.db",
  "packaged_shell_log_path": "C:/Users/alice/AppData/Local/GOAT AI/logs/desktop-shell.log"
}
```

## `POST /api/code-sandbox/exec`

Executes one shell run through the configured sandbox provider. Phase 18A uses:

- one shell-capable runtime preset: `shell`
- an ephemeral workspace
- Docker isolation with **network disabled by default**, or a localhost dev fallback when `GOAT_CODE_SANDBOX_PROVIDER=localhost`
- durable execution, event, and log rows in SQLite for later reads
- `sync` by default, with optional in-process durable `async` dispatch plus queued-execution recovery on startup

Request body:

```json
{
  "execution_mode": "sync",
  "runtime_preset": "shell",
  "code": "echo \"hello from the sandbox\" > outputs/report.txt",
  "command": "sh ./snippet.sh",
  "stdin": "optional stdin text",
  "timeout_sec": 8,
  "network_policy": "disabled",
  "files": [
    {
      "filename": "notes/input.txt",
      "content": "seed file text"
    }
  ]
}
```

Behavior:

- `code` and/or `command` must be provided
- when `command` is omitted, the server executes `code` as a shell script
- inline files must use relative workspace paths only
- files created under `outputs/` are reported back as metadata in the response
- `network_policy` currently only allows `disabled`; other values return `422`
- Docker enforces that policy. The `localhost` provider reports `network_policy_enforced: false` and should be treated as a trusted development fallback rather than a strong-isolation sandbox
- `execution_mode` defaults to `sync`; `async` returns immediately after durable acceptance and continues in a background dispatcher

Success response (`200` for `sync`, `202` for accepted `async`):

```json
{
  "execution_id": "cs-123",
  "status": "completed",
  "execution_mode": "sync",
  "runtime_preset": "shell",
  "network_policy": "disabled",
  "created_at": "2026-04-10T00:00:00Z",
  "updated_at": "2026-04-10T00:00:01Z",
  "started_at": "2026-04-10T00:00:00Z",
  "finished_at": "2026-04-10T00:00:01Z",
  "provider_name": "docker",
  "isolation_level": "container",
  "network_policy_enforced": true,
  "exit_code": 0,
  "stdout": "hello from sandbox\n",
  "stderr": "",
  "timed_out": false,
  "error_detail": null,
  "output_files": [
    {
      "path": "report.txt",
      "byte_size": 21
    }
  ]
}
```

Error semantics:

- **`403 FEATURE_DISABLED`** when the caller lacks `sandbox:execute`
- **`503 FEATURE_UNAVAILABLE`** when runtime gating fails or the selected provider is unavailable
- **`422 REQUEST_VALIDATION_ERROR`** for invalid request shape, unsupported network mode, path traversal, oversized payloads, or timeout beyond the configured cap

## `GET /api/code-sandbox/executions/{execution_id}`

Returns the same durable execution shape as `POST /api/code-sandbox/exec` after the run is persisted. Owner/tenant/principal visibility rules apply; non-visible records resolve as `404`. During `async` execution the record progresses through `queued` and `running` before reaching a terminal state. Terminal statuses are `completed`, `failed`, `denied`, and `cancelled`.

## `POST /api/code-sandbox/executions/{execution_id}/cancel`

Cancels one visible `queued` sandbox execution.

Current behavior:

- only `queued` executions can be cancelled
- success returns `200` with the normal durable execution payload and `status = cancelled`
- cancelled executions set `finished_at` and `error_detail = "Execution cancelled before start."`
- running or terminal executions return `409` with `code = RESOURCE_CONFLICT`
- missing or caller-invisible execution ids return `404`
- cancelled executions are terminal and cause `GET /logs` to emit a final `done` event

## `POST /api/code-sandbox/executions/{execution_id}/retry`

Creates a brand-new durable execution from one visible terminal execution.

Current behavior:

- only terminal executions can be retried: `completed`, `failed`, `denied`, or `cancelled`
- retry always creates a new `execution_id`; the original record remains unchanged except for an added lineage event
- the retried execution reuses the original request payload and persisted auth snapshot
- retrying an originally `sync` execution returns `200` with the new terminal payload
- retrying an originally `async` execution returns `202` when the new run is still `queued` or `running`
- queued or running executions return `409` with `code = RESOURCE_CONFLICT`
- missing or caller-invisible execution ids return `404`

## `GET /api/code-sandbox/executions/{execution_id}/events`

Returns the durable execution timeline:

```json
{
  "execution_id": "cs-123",
  "events": [
    {
      "sequence": 1,
      "event_type": "execution.queued",
      "created_at": "2026-04-10T00:00:00Z",
      "status": "queued",
      "message": "Execution accepted.",
      "metadata": {
        "network_policy": "disabled",
        "runtime_preset": "shell"
      }
    },
    {
      "sequence": 2,
      "event_type": "execution.started",
      "created_at": "2026-04-10T00:00:00Z",
      "status": "running",
      "message": "Execution started.",
      "metadata": {
        "provider_name": "docker"
      }
    },
    {
      "sequence": 3,
      "event_type": "execution.log.stdout",
      "created_at": "2026-04-10T00:00:00Z",
      "status": "running",
      "message": null,
      "metadata": {
        "stream_name": "stdout",
        "log_sequence": 1,
        "byte_size": 18
      }
    },
    {
      "sequence": 4,
      "event_type": "execution.completed",
      "created_at": "2026-04-10T00:00:01Z",
      "status": "completed",
      "message": "Execution completed successfully.",
      "metadata": {
        "exit_code": 0,
        "output_file_count": 1
      }
    }
  ]
}
```

Additional lifecycle events include:

- `execution.cancelled` when a queued execution is cancelled before start
- `execution.retry_requested` on the original record, with `metadata.retry_execution_id`
- `execution.retry_created` on the new record, with `metadata.source_execution_id`

## `GET /api/code-sandbox/executions/{execution_id}/logs`

Streams replayable stdout/stderr chunks plus status updates as SSE. Use the optional `after_seq` query parameter to resume from the next unseen log chunk sequence after reconnect.

SSE frame examples:

```text
data: {"type":"status","execution_id":"cs-123","status":"running","provider_name":"docker","updated_at":"2026-04-10T00:00:00Z","timed_out":false}
```

```text
data: {"type":"stdout","execution_id":"cs-123","sequence":1,"created_at":"2026-04-10T00:00:00Z","chunk":"hello from sandbox\n"}
```

```text
data: {"type":"done"}
```

Notes:

- `GET /events` remains the canonical audit timeline
- `GET /logs` is for live/replayable process output, not lifecycle history
- clients should fall back to `GET /api/code-sandbox/executions/{execution_id}` if the SSE stream disconnects

## Canonical sources

For machine-readable contract details, prefer:

- [openapi.json](openapi.json)
- [api.llm.yaml](api.llm.yaml)
- `__tests__/contracts/test_api_blackbox_contract.py`
- `__tests__/contracts/test_api_authz.py`
