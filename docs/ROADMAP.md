# GOAT AI Roadmap

> Last updated: 2026-04-09
> Current release tag: **v1.2.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This roadmap only tracks **unfinished work**. Completed phases and archived closeout notes live in [PROJECT_STATUS.md](PROJECT_STATUS.md), [OPERATIONS.md](OPERATIONS.md), [DOMAIN.md](DOMAIN.md), and [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md).

---

## Open Work

### Phase 16B: storage evolution

Revisit datastore changes only after authorization and resource boundaries are explicit.

- Goal: define the next storage shape without weakening current single-instance guarantees.
- Exit criteria: migration strategy, compatibility strategy, and rollback strategy are all defined before implementation.
- Dependencies: must wait on the Phase 16 authz envelope and any resulting resource scoping rules.
- Planning artifact: [`STORAGE_EVOLUTION_DECISION_PACKAGE.md`](STORAGE_EVOLUTION_DECISION_PACKAGE.md)

### Frontend backlog

These items remain roadmap-only until the supporting runtime exists.

- Plan Mode runtime integration
- Cloud model API integration for non-local inference backends
- Real Search / Browse mode
- Deep Research
- Canvas / artifact workspace
- Project-scoped knowledge / memory
- Connected apps / external sources

---

## Dependencies / Constraints

- Phase 16A capability gates now build on the completed credential-backed authorization context and tenancy envelope from Phase 16C.
- Capability gates should continue to separate runtime unavailability from policy denial.
- Storage evolution must preserve the current single-writer / SQLite-first operational contract unless a separate decision log changes that assumption.
- Search, research, canvas, connector UI, and future cloud model selection should not expose fake capabilities before the backend/runtime can actually support them.

---

## Decision Pending

### `/api/knowledge/answers` semantic alignment

The product still needs a decision on whether `/api/knowledge/answers` should keep returning a raw retrieved snippet summary or move to the same LLM synthesis behavior used by chat with `knowledge_document_ids`.

- Current state: chat synthesizes retrieved context; `/api/knowledge/answers` returns a snippet-dump style response.
- Decision needed: keep the divergence and document it, or unify the answer semantics across both endpoints.
- Impact: this affects user expectations, API documentation, and the long-term shape of the retrieval UX.
