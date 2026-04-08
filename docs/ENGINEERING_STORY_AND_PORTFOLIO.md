# GOAT AI - Engineering Story & Portfolio Readiness

This document is a **durable narrative and checklist** for presenting GOAT AI on a personal homepage **when the industrial work is real**, not when a version number increments. The bar is intentional:

- **Six-month maintainable** - changes do not require archeology across implicit coupling.
- **Shared, no-root host** - deployable where you do not own the machine.
- **SQLite-first** - honest data posture for the current scale and ops model.
- **Ollama-backed** - local inference boundary, not a thin wrapper around a hosted API only.
- **Ten-axis industrial bar toward ~9/10 *for this codebase*** - as defined in [ROADMAP.md](ROADMAP.md) Phases 13-4 (prerequisites, Wave A/B, semantics-before-structure).

**Homepage signal:** you are not claiming "I called an LLM." You are claiming **you can run an AI product as an engineering system under real constraints**.

---

## 1. What to record *now* (so the story stays honest later)

Keep these artifacts **current** as Phase 13 items land. They become your "before -> after" evidence.

| Record | Why it matters for a portfolio |
|--------|----------------------------------|
| **Dated snapshots of constraints** | Shared host, no `sudo`, single port via nginx, JupyterHub-style path - proves the design is situational, not generic tutorial stack. |
| **Phase 13 exit criteria -> evidence** | Each checkbox in Phase 13 should map to a **PR, doc section, or runbook command** - not "we improved logging" in the abstract. |
| **Before/after bullets** | Short list: what was true *before* Wave A (e.g. text logs only, no `/ready`, silent persistence failures) vs *after*. |
| **Trade-off log** | Link to [ROADMAP.md](ROADMAP.md) Decision Log; add 1-2 sentences per major choice (Postgres deferred, error model before big split, policies before directory migration). |
| **Quantified quality** | Test counts, black-box coverage areas, CI gates (`lint-imports`, contract sync), latency percentiles you actually expose - **numbers you can defend**. |
| **Runbook pointers** | Where to read: deploy, rollback, backup, metrics scrape, readiness check - even if some sections are "TODO until Wave A lands."|

**Anti-pattern:** claiming "industrial grade" on the homepage while the repo still has ad-hoc schema changes, no metrics, and no readiness split. This document assumes **honesty lags marketing**.

---

## 2. The problem (portfolio framing)

**One-line pitch (refine for your voice):**  
A strategic-analysis chat product that must run on **school/shared infrastructure** - no root, predictable port, browser-friendly SPA - with **local Ollama** inference and **durable session history**, without pretending the ops environment is a greenfield Kubernetes cluster.

**Why SQLite + Ollama + shared host is a feature in the story:**  
They are **constraints that force** clear boundaries, observable failure modes, and migration discipline. The portfolio reads better when you say **what you refused to fake** (e.g. swapping Postgres "for show" and **what you built instead** (migrations as artifacts, backup runbook, metrics under single-process limits).

---

## 3. Engineering evolution arc (narrative spine)

Use this arc on a homepage or case-study page. Dates and scores are **yours to fill** as work lands.

1. **From runnable assistant -> bounded product**  
   FastAPI + React SSE chat, uploads, history, charts - a **complete product slice**, not a notebook.

2. **From product -> layered backend**  
   Routers thin; services own orchestration; shared `goat_ai` layer without FastAPI; import boundaries enforced (`lint-imports`, router direct-import tests).

3. **From layered -> operable** (Phase 13 focus)  
   Structured logs + request correlation; Prometheus-style metrics; **liveness vs readiness**; persistence failures visible; **error model + registry** so logs, metrics, retries, and runbooks share one vocabulary.

4. **From operable -> resilient and governable** (Phase 13 Wave B landed)  
   Ollama read-policy now includes retries/backoff/jitter plus circuit-breaker states (`closed` / `open` / `half_open`) for `/api/tags` and `/api/show`; idempotency now protects upload-analyze JSON and chat session append retries; OPERATIONS now documents explicit multi-instance limits for per-process rate limiting and rolling metrics.

5. **From governable -> semantically stable** (Phase 14)  
   Policy objects and invariants **before** large `application/` / `domain/` moves; session schema contract and normalization when migrations are already a first-class artifact.

**Portfolio line:** *I did not optimize for demo screenshots; I optimized for the next engineer (often me in six months) to change the system safely.*

---

## 4. Key engineering decisions (senior-visible)

These are worth a **"Trade-offs"** subsection on a homepage. Align wording with [ROADMAP.md](ROADMAP.md) Decision Log.

| Decision | Rough story |
|----------|-------------|
| **Postgres not by default** | Data and ops model fits SQLite until migration discipline and multi-instance needs force a move - avoid database theater. |
| **Wave A = observe + ready + persistence signals first** | Without logs, metrics, and readiness, retries and breakers are blind; client resilience is **Wave B** so it does not block operational lift. |
| **Migrations as artifacts (Phase 13 §13.0)** | Schema and session evolution are continuous; ad-hoc `ALTER` chains do not scale with feature velocity. |
| **Error model before / alongside observability** | Stable `code`s feed metrics labels and retry policy; runbooks reference the same taxonomy. |
| **Policies and invariants before big package split** | Semantic convergence reduces blast radius of directory refactors (Phase 14 ordering). |
| **Single-tenant / shared API key** | Threat model documented honestly; authz roadmap separated from "looks secure" shortcuts. |

---

## 5. Verifiable outcomes (what visitors can check)

When Phase 13 is **substantially landed**, your homepage or README should point to **concrete hooks**:

| Area | Example of verifiable claim |
|------|------------------------------|
| **Tests** | Black-box API contract suite; architecture / import-layer gates; integration tier (when added). |
| **Observability** | Sample structured log line; `/api/system/metrics` scrape example; `X-Request-ID` behavior. |
| **Ops** | `/api/health` vs `/api/ready`; rollback + backup runbook excerpt; post-deploy check script. |
| **Data** | Migration directory, version table, how to validate upgrade from an old DB file. |
| **Reliability** | Ollama policy table (timeouts, retries, breaker); idempotency behavior for chosen endpoints. |
| **Capacity** | SLO table + load script command + how to read p50/p95 from existing telemetry. |

If a claim has **no** anchor in the repo or docs, do not put it on the homepage.

Wave B evidence anchors in this repo:

- `goat_ai/ollama_client.py` + `__tests__/test_ollama_client_cache.py`
- `backend/services/idempotency_service.py` + `backend/migrations/005_add_idempotency_keys.sql`
- `backend/routers/upload.py` + `backend/routers/chat.py`
- `__tests__/test_upload_router.py` + `__tests__/test_api_blackbox_contract.py`
- `docs/OPERATIONS.md` (multi-instance limitations + mitigations)

---

## 6. "Homepage-ready" bar (not tied to v1.5)

Treat the project as **homepage-worthy** when **most** of the following are true -grounded in **Phase 13/14 exit criteria**, not a version string:

- [ ] Clear **README** + **architecture overview** (diagram or layered description).
- [ ] **Demo** (short video or screenshots) showing chat + upload + chart path -product, not only infra.
- [ ] A **before ->after** engineering section (this file or a linked case study) with **dated** milestones.
- [ ] A **trade-offs / decisions** page or section (can be this doc + ROADMAP Decision Log).
- [ ] **Quantified** testing and CI story (what gates exist, what they protect).
- [ ] **Operational evidence**: how logs and metrics are consumed; how readiness and rollback are run; how migrations are validated.
- [ ] **Honest constraint paragraph**: shared host, no root, SQLite-first -and why that is **reasonable**, not accidental.

**Optional stretch (strong portfolio):** one paragraph on **what you would do next** if the product gained ten times the traffic (without hand-waving -reference Phase 14 normalization, Postgres gate, etc.).

---

## 7. Why this belongs on a personal homepage (summary)

- **Full product shape** -SPA, streaming API, persistence, charts, access controls -not a single-script demo.
- **Real constraints** -shared machine, no root, local inference -reads as production-adjacent engineering.
- **Governance story** -boundaries, tests, observability, data migration, runbooks -reads as **systems thinking**, not feature churn.

The differentiator is not the stack list; it is **the documented path from demo-quality to maintainable-quality** under constraints you did not choose.

---

## Related documents

- [ROADMAP.md](ROADMAP.md) -Phase 13 (§13.0, Wave A/B) and Phase 14 sequencing.
- [OPERATIONS.md](OPERATIONS.md) -deploy, env, host constraints (keep aligned with claims on your homepage).
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) -day-to-day engineering contract.
- [AGENTS.md](../AGENTS.md) -durable repo memory for automation and contributors.

---

*Last updated: 2026-04-08 -created to anchor portfolio narrative to **industrial outcomes**, not version marketing.*





