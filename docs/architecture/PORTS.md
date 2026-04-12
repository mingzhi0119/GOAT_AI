# Ports (injectable boundaries)

`backend.application.ports` is the stable import surface for routers and application use cases. Import shared `Protocol` types, settings annotations, and shared exception semantics from there; keep implementation details in `backend.services.*`.

`backend.application.exceptions` remains the home for application-specific exception classes such as history, chat idempotency, and upload idempotency errors.

| Export | Origin | Role |
|--------|--------|------|
| `SessionRepository` | `backend/services/chat_runtime.py` | Load, list, upsert, and delete persisted chat sessions. |
| `ConversationLogger` | `backend/services/chat_runtime.py` | Append-only audit log of completed turns. |
| `TitleGenerator` | `backend/services/chat_runtime.py` | Optional LLM-backed session title generation. |
| `LLMClient` | `goat_ai/llm/ollama_client.py` | Model listing, streaming, and tool-calling boundary for tests and adapters. |
| `SafeguardService` | `backend/services/safeguard_service.py` | Chat safeguard boundary used by orchestration and streaming. |
| `TabularContextExtractor` | `backend/services/tabular_context.py` | Shared table extraction boundary for chat and upload flows. |
| `Settings` | `goat_ai/config/settings.py` | Typed app settings for dependency injection and use-case signatures. |
| `ChatCapacityError` | `backend/services/chat_capacity_service.py` | Chat request capacity guardrail. |
| `FeatureNotAvailable` | `backend/services/exceptions.py` | Feature-gate denial semantics. |
| `InferenceBackendUnavailable` | `backend/services/exceptions.py` | Inference backend reachability semantics. |
| `KnowledgeDocumentNotFound` | `backend/services/exceptions.py` | Missing knowledge document or ingestion semantics. |
| `KnowledgeValidationError` | `backend/services/exceptions.py` | Knowledge request validation semantics. |
| `MediaNotFound` | `backend/services/exceptions.py` | Missing media attachment semantics. |
| `MediaValidationError` | `backend/services/exceptions.py` | Media upload validation semantics. |
| `VisionNotSupported` | `backend/services/exceptions.py` | Selected model lacks vision capability. |

Routers should remain thin: validate input, call application or service layers, and return responses. Prefer adding use-case functions under `backend/application/` over growing router modules.

See [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) for allowed import direction.
