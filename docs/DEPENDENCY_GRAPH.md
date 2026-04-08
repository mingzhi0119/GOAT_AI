# Backend dependency graph

Import direction is enforced by `lint-imports` (`pyproject.toml` -> `importlinter`). First layer in the contract is outermost and may import inward only.

## Target (Phase 15.2+)

```mermaid
flowchart TB
  subgraph target [Target dependency direction]
    routers[backend.routers]
    application[backend.application]
    services[backend.services]
    domain[backend.domain]
    models[backend.models]
    goat[goat_ai]
  end
  routers --> application
  application --> services
  services --> domain
  services --> models
  domain --> models
  models --> goat
```

- `backend.domain` (Phase 15.1) holds policies and invariants.
- `backend.application` is use-case orchestration.
- `goat_ai` is the innermost shared library and does not import `backend`.

## Current (incremental)

As of the Phase 15 structural closeout work, `backend.application` now owns the main history use cases, knowledge/media/system/model entry points, upload/analyze preflight, chat preflight, and the code-sandbox gate. The graph above is the directional target, not a claim that every helper inside those modules has been eliminated.

Partial wiring:

- `GET /api/history` and `DELETE /api/history` flow through `backend.application.history`.
- `GET /api/history/{id}` and `DELETE /api/history/{id}` flow through `backend.application.history`.
- `POST /api/knowledge/*` flows through `backend.application.knowledge`.
- `POST /api/media/uploads` flows through `backend.application.media`.
- `GET /api/models` and `GET /api/models/capabilities` flow through `backend.application.models`.
- `GET /api/system/*` and `GET /api/ready` flow through `backend.application.system`.
- `POST /api/upload` and `POST /api/upload/analyze` flow through `backend.application.upload`.
- `POST /api/chat` uses `backend.application.chat` for request preflight before streaming.
- `POST /api/code-sandbox/exec` uses `backend.application.code_sandbox` for the feature gate.
- `backend.application.ports` is the shared contract face for `Settings`, `LLMClient`, `SessionRepository`, `ConversationLogger`, `TitleGenerator`, `SafeguardService`, `TabularContextExtractor`, and the stable shared exceptions; `backend.application.exceptions` keeps application-specific error classes.
- Routers and application modules should not import `backend.services.exceptions` or `backend.services.chat_capacity_service` directly.

## Related

- Port list: [PORTS.md](PORTS.md)
- Session JSON: [SESSION_SCHEMA.md](SESSION_SCHEMA.md)
- Import contract: `pyproject.toml` (`[tool.importlinter]`)
