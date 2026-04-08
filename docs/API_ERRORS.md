# API error model (Phase 13 §13.0)

JSON error responses use a **stable envelope** so logs, metrics, and clients share the same semantics:

```json
{
  "detail": "Human-readable message or structured validation payload",
  "code": "STABLE_ERROR_CODE",
  "request_id": "uuid-or-client-supplied-id"
}
```

- **`detail`** — String for most 4xx/5xx from handlers; **array of objects** for `422` validation (FastAPI / Pydantic shape unchanged, wrapped with `code` and `request_id`).
- **`code`** — Machine-readable, **do not rename** once shipped (breaking change for clients and dashboards).
- **`request_id`** — Omitted only if context is missing (should not happen on normal HTTP requests after middleware runs). Clients may send **`X-Request-ID`**; the server echoes it here and in the response header. The active id is stored in **`goat_ai.request_context`** (re-exported from `backend.api_errors` for convenience).

## Registry

| `code` | HTTP | Retry hint* | Typical meaning |
|--------|------|-------------|-----------------|
| `AUTH_INVALID_API_KEY` | 401 | no | Missing or wrong `X-GOAT-API-Key` when `GOAT_API_KEY` is set |
| `AUTH_WRITE_KEY_REQUIRED` | 403 | no | `GOAT_API_KEY_WRITE` is set but the request used the read key on a write route |
| `AUTH_SESSION_OWNER_REQUIRED` | 403 | no | `GOAT_REQUIRE_SESSION_OWNER=1` but `X-GOAT-Owner-Id` was missing on chat/history |
| `RATE_LIMITED` | 429 | yes (after Retry-After) | Per-key rate limit exceeded |
| `BAD_REQUEST` | 400 | no | Bad upload / business validation |
| `IDEMPOTENCY_CONFLICT` | 409 | no | `Idempotency-Key` reused with different payload or while original request is still pending |
| `REQUEST_VALIDATION_ERROR` | 422 | no | Body / query validation failed |
| `NOT_FOUND` | 404 | no | Resource does not exist |
| `KNOWLEDGE_NOT_FOUND` | 404 | no | Knowledge document or ingestion record does not exist |
| `MEDIA_NOT_FOUND` | 404 | no | Vision image attachment id missing or invalid |
| `VISION_NOT_SUPPORTED` | 422 | no | Image attachments sent but the model does not report Ollama `vision` capability |
| `NOT_IMPLEMENTED` | 501 | no | Contract exists but the feature has not landed yet |
| `INFERENCE_BACKEND_UNAVAILABLE` | 503 | yes | Ollama (or equivalent) unreachable |
| `INTERNAL_ERROR` | 500 | no | Unhandled server error (detail sanitized) |
| `FEATURE_DISABLED` | 403 | no | Policy / AuthZ: caller is not allowed to use this capability (see §15 in `docs/ENGINEERING_STANDARDS.md`) |
| `FEATURE_UNAVAILABLE` | 503 | yes | Runtime / deployment: feature is off or a dependency (e.g. Docker) is not ready on this host—not an authorization decision |

\*Retry hint is **documentary** for Wave B client policy; server behavior is defined per endpoint.

## Source of truth

- Constants: `backend/api_errors.py` (request correlation: `goat_ai.request_context`)
- Handler registration: `backend/exception_handlers.py`
- OpenAPI schema: `ErrorResponse` in `backend/models/common.py` → `docs/openapi.json`

## Related

- [ROADMAP.md](ROADMAP.md) Phase 13 §13.0  
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) · [AGENTS.md](../AGENTS.md) (index)
