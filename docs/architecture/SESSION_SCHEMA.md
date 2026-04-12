# Session storage JSON schema

Persisted chat sessions store a **versioned JSON blob** in the SQLite `sessions.messages` column (see `backend/services/log_service.py`). Encoding and decoding live in `backend/services/session_message_codec.py`.

**Phase 15.4:** visible turns are also stored in table **`session_messages`** (dual-write / dual-read with this JSON). See [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md).

## Version constant

- **`SESSION_PAYLOAD_VERSION`** is currently **`4`** (see `session_message_codec.py`).
- Bump this constant when you change the **semantic shape** of the stored object (new required fields, incompatible message layout, renamed keys consumed at read time).
- After a bump, ensure `decode_session_payload` accepts both the new shape and any in-flight legacy rows you still need to support. Future schema versions must raise `SessionSchemaError` on older binaries rather than silently downgrade.

## Versioned object shape (`build_session_payload` / dict decode)

New snapshots are built with `build_session_payload()` and persist as a **JSON object** with at least:

| Field | Type | Notes |
|-------|------|--------|
| `version` | int | Must match `SESSION_PAYLOAD_VERSION` for newly written rows. |
| `messages` | array of objects | Each item has `role` (`user` \| `assistant` \| `system`) and string `content`; optional `image_attachment_ids`. |
| `chart_data_source` | string | One of `uploaded`, `demo`, `none`. |
| `chart_spec` | object or omitted | Present when a chart is stored; must satisfy chart version rules (`backend.domain.invariants.chart_spec_requires_version_field`). |
| `file_context_prompt` | string or omitted | Upload / tabular context text when applicable. |
| `knowledge_documents` | array or omitted | Items with `document_id`, `filename`, `mime_type`. |

`decode_session_payload()` accepts this dict and returns a normalized `DecodedSessionPayload`.

## Legacy list shape

Older rows may store **`messages` as a JSON array** (not wrapped in a versioned object). That list uses **role-tagged pseudo-messages**, including:

- `__chart__` - chart JSON embedded as content.
- `__file_context__` / `__file_context_ack__` - file context and acknowledgements.

`decode_session_payload()` detects `list` vs `dict` and normalizes to the same `DecodedSessionPayload` abstraction.

## When to bump `SESSION_PAYLOAD_VERSION`

- Adding a new top-level field that readers must understand to render or safeguard correctly.
- Changing how real chat turns are represented in `messages` (e.g. new required roles or structures).
- Incompatible changes to `chart_spec` or knowledge document embedding.

Cosmetic or backward-compatible additions (optional fields ignored by older readers) may not require a bump if all readers tolerate unknown keys-still prefer a version bump when in doubt.

## Related docs

- Domain terms: [DOMAIN.md](DOMAIN.md) (session / turn / schema version).
- Normalized rows: [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md).
- Ports and layers: [PORTS.md](PORTS.md), [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md).

## Integration test time budget (Phase 15.3)

Backend CI runs `pytest` over `__tests__/` including **`integration`**-marked tests. Keep the **integration slice** small enough that the full backend test job stays **under ~30 seconds** on CI; if the suite grows, split with `pytest -m "not integration"` vs `-m integration` (see `pytest.ini`).

