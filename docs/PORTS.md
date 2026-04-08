# Ports (injectable boundaries)

This list names **stable Protocol-shaped boundaries** used for orchestration and persistence. Implementations live in services or adapters; callers depend on the interface, not SQLite or HTTP details.

| Port | Location | Role |
|------|----------|------|
| **SessionRepository** | `backend/services/chat_runtime.py` | Load/list/upsert/delete persisted chat sessions (`SessionSummaryRecord`, `SessionDetailRecord`, `SessionUpsertPayload`). |
| **ConversationLogger** | `backend/services/chat_runtime.py` | Append-only audit log of completed turns (`ConversationLogEntry`). |
| **TitleGenerator** | `backend/services/chat_runtime.py` | Optional LLM-backed session title generation. |
| **LLMClient** | `goat_ai/ollama_client.py` | Model listing, streaming, tools; swapped in tests via `Protocol` / fakes. |
| **Telemetry / latency** | `goat_ai/latency_metrics.py` (and related hooks) | Rolling latency and operational metrics; initialized from app settings. |

Routers should remain thin: validate input, call **application or service** layers, return responses. Prefer adding use-case functions under `backend/application/` over growing router modules.

See [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) for allowed import direction.
