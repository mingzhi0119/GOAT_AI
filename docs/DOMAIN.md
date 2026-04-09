# Domain language (ubiquitous terms)

This document names **user-visible and persistence concepts** shared across chat, charts, knowledge, and safeguards. When behavior changes, update this file in the same PR.

## Session and turns

| Term | Meaning |
|------|---------|
| **Session** | One saved conversation (SQLite row) keyed by `session_id`, with versioned JSON payload. |
| **Turn** | One logical exchange: user message(s) plus assistant reply in the live chat buffer; persisted as a snapshot after streaming completes. |
| **Schema version** | `SESSION_PAYLOAD_VERSION` in `session_message_codec` - bump when stored JSON shape changes. Full field list: [SESSION_SCHEMA.md](SESSION_SCHEMA.md). |

## Chat content

| Term | Meaning |
|------|---------|
| **File context** | Tabular or upload-derived text injected for analysis; may be stored as `file_context_prompt` or legacy markers. |
| **Knowledge attachment** | References to indexed documents (`knowledge_document_ids` / persisted `knowledge_documents`). |
| **Vision attachment** | Image ids from `POST /api/media/uploads` (`image_attachment_ids`). |

## Charts (native tool path)

| Term | Meaning |
|------|---------|
| **ChartIntentV2** | Constrained intent from the LLM tool call; compiled in-process. |
| **ChartSpecV2** | Persisted chart payload; must include **`version`** (e.g. `"2.0"`) when stored on the session. |
| **Chart data source** | `uploaded` (user tabular context), `demo` (built-in fallback frame), or `none`. Resolved by **chart provenance policy** (`backend.domain.chart_provenance_policy`). |

## Safeguards

| Term | Meaning |
|------|---------|
| **SafeguardAssessment** | `allowed` / `reason_code` / `stage` - output of **safeguard policy** (`backend.domain.safeguard_policy`) on combined user+system text (input) or assistant text (output). |
| **Policy refusal** | Fixed refusal copy + blocked title when input or streaming output fails policy. |

## Rate limiting

| Term | Meaning |
|------|---------|
| **RateLimitSubject** | Stable subject for a rate-limit bucket: `api_key_fingerprint`, `owner_id`, `route_group`, `method_class`. |
| **RateLimitPolicy** | Pure sliding-window policy that owns `window_sec`, `max_requests`, subject key derivation, and admission decisions. |
| **RateLimitStore** | Storage adapter for sliding-window timestamps. The in-memory implementation keeps per-key request times and prunes expired entries on read. |
| **RateLimitDecision** | Immutable result of one rate-limit evaluation (`allowed: bool`, `retry_after: int`). Defined in `backend.domain.rate_limit_policy`. |
| **Sliding window** | `RateLimitPolicy.decide()` evaluates the timestamps returned by `RateLimitStore` against `window_sec`, blocking when `max_requests` is reached. |
| **Clock injection** | HTTP security passes `Clock.monotonic()` into the rate-limit policy/store path so tests can use a `FakeClock` without real time passing. |

## Authorization and tenancy

| Term | Meaning |
|------|---------|
| **Credential principal** | Minimal trusted caller identity derived from an API credential. It is not end-user identity. |
| **Tenant** | Explicit resource boundary carried in authz context and persisted metadata; v1 defaults to `tenant:default`. |
| **Scope** | Stable authorization capability string such as `history:read` or `artifact:write`. |
| **AuthorizationContext** | Request-scoped authz state: `principal_id`, `tenant_id`, `scopes`, `credential_id`, legacy owner header, and auth mode. |
| **AuthorizationDecision** | Pure allow/deny result with a stable `reason_code` plus optional concealment semantics for `404`-style denials. |

## Session payload versioning

| Term | Meaning |
|------|---------|
| **SESSION_PAYLOAD_VERSION** | Current version integer (`4` as of Phase 15.11) in `session_message_codec`. Bump when the persisted JSON shape changes in a non-backwards-compatible way. |
| **SessionSchemaError** | Raised when a stored payload carries a version integer higher than `SESSION_PAYLOAD_VERSION`. Older versions are decoded tolerantly; future versions fail loud on read. |
| **Legacy list payload** | Pre-version-dict format: a JSON array of role-tagged objects. Decoded by `_decode_legacy_session_payload` for backwards compatibility. |

## PR checklist (user-visible behavior)

- [ ] Updated this file if any term above changed meaning, or added a new ubiquitous term.
- [ ] Contract artifacts (`docs/openapi.json`, `docs/api.llm.yaml`) regenerated if HTTP schemas changed.
