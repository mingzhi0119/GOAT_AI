# GOAT AI API Reference

## Overview

GOAT AI exposes its core backend logic through FastAPI endpoints grouped by capability:

- Chat orchestration: stream LLM completions and optional chart directives.
- Upload analysis: parse CSV/XLSX files into reusable analysis prompts and starter chart specs.
- Session history: list, inspect, and delete persisted chat sessions.
- System telemetry: inspect GPU state and rolling chat latency.
- Model discovery: enumerate available Ollama models.

Base path: `/api`

Authentication:

- If `GOAT_API_KEY` is configured, every endpoint except `GET /api/health` requires the `X-GOAT-API-Key` header.
- All API responses include `X-Request-ID`.
- Rate-limited requests return `429 Too Many Requests` with `Retry-After`.

Error format:

```json
{
  "detail": "Human-readable error message"
}
```

## Endpoint Summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/models` | List available Ollama models |
| `POST` | `/api/chat` | Stream a chat completion over SSE |
| `POST` | `/api/upload` | Stream upload analysis events over SSE |
| `POST` | `/api/upload/analyze` | Analyze an uploaded file and return JSON |
| `GET` | `/api/history` | List saved chat sessions |
| `GET` | `/api/history/{session_id}` | Get one saved chat session |
| `DELETE` | `/api/history` | Delete all saved chat sessions |
| `DELETE` | `/api/history/{session_id}` | Delete one saved chat session |
| `GET` | `/api/system/gpu` | Read GPU telemetry |
| `GET` | `/api/system/inference` | Read rolling chat latency telemetry |

## `GET /api/health`

Purpose: verify the service is live without requiring model access.

Request parameters: none.

Success response:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

Error codes:

- `200 OK`

## `GET /api/models`

Purpose: list locally available Ollama model names.

Headers:

- `X-GOAT-API-Key` optional unless API key protection is enabled.

Success response:

```json
{
  "models": ["llama3:latest", "mistral:latest"]
}
```

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`
- `503 Service Unavailable`

## `POST /api/chat`

Purpose: stream a chat response from the LLM.

Headers:

- `Content-Type: application/json`
- `X-User-Name` optional display name to fold into the effective system prompt.
- `X-GOAT-API-Key` optional unless API key protection is enabled.

Request body:

```json
{
  "model": "llama3:latest",
  "messages": [
    { "role": "user", "content": "Summarize Porter's Five Forces." }
  ],
  "session_id": "session-123",
  "system_instruction": "Answer in bullet points.",
  "temperature": 0.3,
  "max_tokens": 512,
  "top_p": 0.9
}
```

Request fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | `string` | Yes | Ollama model name |
| `messages` | `ChatMessage[]` | Yes | At least one item |
| `session_id` | `string \| null` | No | Enables session persistence |
| `system_instruction` | `string \| null` | No | Appended after the base system prompt |
| `temperature` | `number \| null` | No | Range `0.0` to `2.0` |
| `max_tokens` | `integer \| null` | No | Mapped to Ollama `num_predict` |
| `top_p` | `number \| null` | No | Range `0.0` to `1.0` |

`ChatMessage`:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `role` | `user \| assistant \| system` | Yes | Message role |
| `content` | `string` | Yes | Message content |

Success response:

- Content type: `text/event-stream`
- Frames are emitted in `data: ...` format

Token frame:

```text
data: "partial token"
```

Chart frame:

```text
data: {"type":"chart_spec","chart":{"type":"line","title":"Revenue trend","xKey":"month","series":[{"key":"revenue","name":"revenue"}],"data":[{"month":"Jan","revenue":10}]}}
```

Completion frame:

```text
data: "[DONE]"
```

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

Notes:

- Runtime model failures are emitted inside the stream as `"[ERROR] ..."` frames, followed by `"[DONE]"`.

## `POST /api/upload`

Purpose: parse a CSV/XLSX file and stream analysis metadata over SSE.

Headers:

- `Content-Type: multipart/form-data`
- `X-GOAT-API-Key` optional unless API key protection is enabled.

Form fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | binary | Yes | `.csv` or `.xlsx` only |

Success response:

- Content type: `text/event-stream`

`file_context` frame:

```text
data: {"type":"file_context","filename":"sales.csv","prompt":"[User uploaded tabular data for analysis] ..."}
```

Optional `chart_spec` frame:

```text
data: {"type":"chart_spec","chart":{"type":"line","title":"revenue trend","xKey":"month","series":[{"key":"revenue","name":"revenue"}],"data":[{"month":"Jan","revenue":10}]}}
```

Completion frame:

```text
data: "[DONE]"
```

Error codes:

- `400 Bad Request`
- `401 Unauthorized`
- `429 Too Many Requests`

Notes:

- Parse failures are surfaced as SSE error strings like `data: "[ERROR] Could not read this file..."`.

## `POST /api/upload/analyze`

Purpose: expose upload parsing as a plain JSON API for external integrations.

Headers:

- `Content-Type: multipart/form-data`
- `X-GOAT-API-Key` optional unless API key protection is enabled.

Form fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | binary | Yes | `.csv` or `.xlsx` only |

Success response:

```json
{
  "filename": "sales.csv",
  "prompt": "[User uploaded tabular data for analysis]\n\nDataframe shape: 2 rows x 2 columns.",
  "chart": {
    "type": "line",
    "title": "revenue trend",
    "xKey": "month",
    "series": [
      { "key": "revenue", "name": "revenue" }
    ],
    "data": [
      { "month": "Jan", "revenue": 10 },
      { "month": "Feb", "revenue": 12 }
    ]
  }
}
```

Response fields:

| Field | Type | Notes |
|-------|------|-------|
| `filename` | `string` | Original uploaded filename |
| `prompt` | `string` | Reusable analysis prompt generated from the uploaded data |
| `chart` | `ChartSpec \| null` | Suggested starter visualization |

Error codes:

- `400 Bad Request`
- `401 Unauthorized`
- `429 Too Many Requests`

## `GET /api/history`

Purpose: list saved chat sessions.

Success response:

```json
{
  "sessions": [
    {
      "id": "session-123",
      "title": "Porter analysis",
      "model": "llama3:latest",
      "created_at": "2026-04-07T14:00:00+00:00",
      "updated_at": "2026-04-07T14:01:30+00:00"
    }
  ]
}
```

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

## `GET /api/history/{session_id}`

Purpose: fetch one persisted session with full message history.

Path parameters:

| Name | Type | Required | Notes |
|------|------|----------|-------|
| `session_id` | `string` | Yes | Session identifier |

Success response:

```json
{
  "id": "session-123",
  "title": "Porter analysis",
  "model": "llama3:latest",
  "created_at": "2026-04-07T14:00:00+00:00",
  "updated_at": "2026-04-07T14:01:30+00:00",
  "messages": [
    { "role": "user", "content": "Explain Porter." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Error codes:

- `401 Unauthorized`
- `404 Not Found`
- `429 Too Many Requests`

## `DELETE /api/history`

Purpose: remove all saved chat sessions.

Success response:

- Status: `204 No Content`

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

## `DELETE /api/history/{session_id}`

Purpose: remove one saved chat session.

Path parameters:

| Name | Type | Required | Notes |
|------|------|----------|-------|
| `session_id` | `string` | Yes | Session identifier |

Success response:

- Status: `204 No Content`

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

## `GET /api/system/gpu`

Purpose: read real-time GPU telemetry from `nvidia-smi`.

Success response:

```json
{
  "available": true,
  "active": true,
  "message": "A100 Inference Engine: Active",
  "name": "NVIDIA A100-SXM4-80GB",
  "uuid": "GPU-xxxx",
  "utilization_gpu": 63.0,
  "memory_used_mb": 11234.0,
  "memory_total_mb": 81920.0,
  "temperature_c": 54.0,
  "power_draw_w": 201.5
}
```

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

Notes:

- Telemetry failures still return `200` with `available=false` and a fallback message.

## `GET /api/system/inference`

Purpose: inspect rolling average latency for completed chat streams.

Success response:

```json
{
  "chat_avg_ms": 842.3,
  "chat_sample_count": 20
}
```

Error codes:

- `401 Unauthorized`
- `429 Too Many Requests`

## OpenAPI / Swagger

Because the backend is FastAPI-based, the same contract is also available as generated OpenAPI metadata:

- OpenAPI version: `3.2.0`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
