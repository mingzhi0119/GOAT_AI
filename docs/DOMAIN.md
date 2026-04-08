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

## PR checklist (user-visible behavior)

- [ ] Updated this file if any term above changed meaning, or added a new ubiquitous term.
- [ ] Contract artifacts (`docs/openapi.json`, `docs/api.llm.yaml`) regenerated if HTTP schemas changed.

