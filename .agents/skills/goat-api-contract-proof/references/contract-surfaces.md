# API Contract Surfaces

Treat these files as one governed surface:

- [API_REFERENCE.md](../../../../docs/api/API_REFERENCE.md)
- [openapi.json](../../../../docs/api/openapi.json)
- [api.llm.yaml](../../../../docs/api/api.llm.yaml)
- [frontend generated OpenAPI types](../../../../frontend/src/api/generated/openapi.ts)
- [frontend API adapter types](../../../../frontend/src/api/types.ts)
- [backend routers](../../../../backend/routers)
- [backend API models](../../../../backend/models)

## Shared-boundary reminder

`AGENTS.md` treats contract surfaces such as `frontend/src/api/types.ts`, `docs/api/openapi.json`, and `docs/api/api.llm.yaml` as explicit shared-boundary files.
