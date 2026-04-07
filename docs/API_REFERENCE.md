# GOAT AI API Reference

Base path: `/api`

## Global behavior

- If `GOAT_API_KEY` is configured, every endpoint except `GET /api/health` requires `X-GOAT-API-Key`
- Responses include `X-Request-ID`
- Rate-limited requests return `429` with `Retry-After`
- Standard error shape:

```json
{
  "detail": "Human-readable error message"
}
```

## Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/models` | List Ollama models |
| `GET` | `/api/models/capabilities` | Read capabilities for one model |
| `POST` | `/api/chat` | Stream chat SSE |
| `POST` | `/api/upload` | Stream upload analysis SSE |
| `POST` | `/api/upload/analyze` | Upload analysis as JSON |
| `GET` | `/api/history` | List saved sessions |
| `GET` | `/api/history/{session_id}` | Read one session |
| `DELETE` | `/api/history` | Delete all sessions |
| `DELETE` | `/api/history/{session_id}` | Delete one session |
| `GET` | `/api/system/gpu` | GPU telemetry |
| `GET` | `/api/system/inference` | Rolling chat latency |
| `GET` | `/api/system/runtime-target` | Runtime target resolution |

## `GET /api/health`

Returns:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

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
  "session_id": "session-123",
  "system_instruction": "Answer in bullet points.",
  "temperature": 0.3,
  "max_tokens": 512,
  "top_p": 0.9
}
```

SSE event types:

- `token`
- `chart_spec`
- `error`
- `done`

Token frame:

```text
data: {"type":"token","token":"Hello"}
```

Chart frame:

```text
data: {"type":"chart_spec","chart":{"version":"2.0","engine":"echarts","kind":"line"}}
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

- If the selected model does not support native tools, chat remains text-only
- Unsafe prompts are converted into a safe refusal instead of passing through the raw request
- Unsafe model output is replaced server-side before streaming

## `POST /api/upload`

Purpose:

- Parse CSV/XLSX
- Return reusable file context for the next chat turn

Form field:

- `file`: `.csv` or `.xlsx`

SSE event types:

- `file_context`
- `error`
- `done`

Success frame:

```text
data: {"type":"file_context","filename":"sales.csv","prompt":"[User uploaded tabular data for analysis] ..."}
```

Notes:

- This endpoint does not emit `chart_spec`
- Charts are created later during `/api/chat` tool calls

## `POST /api/upload/analyze`

Returns:

```json
{
  "filename": "sales.csv",
  "prompt": "[User uploaded tabular data for analysis] ...",
  "chart": null
}
```

`chart` is retained only for backward compatibility.

## `GET /api/history`

Returns session metadata list:

```json
{
  "sessions": [
    {
      "id": "session-123",
      "title": "Porter analysis",
      "model": "gemma4:26b",
      "created_at": "2026-04-07T14:00:00+00:00",
      "updated_at": "2026-04-07T14:01:30+00:00"
    }
  ]
}
```

## `GET /api/history/{session_id}`

Returns one stored session with messages:

```json
{
  "id": "session-123",
  "title": "Porter analysis",
  "model": "gemma4:26b",
  "created_at": "2026-04-07T14:00:00+00:00",
  "updated_at": "2026-04-07T14:01:30+00:00",
  "messages": [
    { "role": "user", "content": "Explain Porter." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Stored history may also contain compatibility roles such as `__chart__`, `__file_context__`, and `__file_context_ack__`.

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
  "chat_sample_count": 20
}
```

## `GET /api/system/runtime-target`

Returns deploy target resolution information:

```json
{
  "deploy_target": "auto",
  "current": {
    "name": "server",
    "host": "127.0.0.1",
    "port": 62606
  },
  "ordered_targets": [
    {
      "name": "server",
      "host": "127.0.0.1",
      "port": 62606
    },
    {
      "name": "local",
      "host": "127.0.0.1",
      "port": 8002
    }
  ]
}
```

## Canonical sources

For machine-readable contract details, prefer:

- [openapi.json](openapi.json)
- [api.llm.yaml](api.llm.yaml)
- `__tests__/test_api_blackbox_contract.py`
