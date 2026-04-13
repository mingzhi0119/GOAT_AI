# GOAT AI - Engineering Story & Portfolio Readiness

This document is a **durable narrative and checklist** for presenting GOAT AI on a personal homepage **when the industrial work is real**, not when a version number increments. The bar is intentional:

This is a portfolio narrative, not a canonical repository-truth surface. Use
[PROJECT_STATUS.md](PROJECT_STATUS.md), [ROADMAP.md](ROADMAP.md),
[ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md), and
[ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md) for the live
repo state and policy split.

- **Six-month maintainable** - changes do not require archeology across implicit coupling.
- **Shared, no-root host** - deployable where you do not own the machine.
- **SQLite-first** - honest data posture for the current scale and ops model.
- **Ollama-backed** - local inference boundary, not a thin wrapper around a hosted API only.
- **Ten-axis industrial bar toward ~9/10 *for this codebase*** - as defined by the canonical engineering contract in [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md), evidenced by shipped state in [PROJECT_STATUS.md](PROJECT_STATUS.md), and sequenced through the historical phase record in [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md).

**Homepage signal:** you are not claiming "I called an LLM." You are claiming **you can run an AI product as an engineering system under real constraints**.

---

## 1. What to record *now* (so the story stays honest later)

Keep these artifacts **current** as release-quality work lands. They become your "before -> after" evidence.

| Record | Why it matters for a portfolio |
|--------|----------------------------------|
| **Dated snapshots of constraints** | Example: shared host, no `sudo`, reverse proxy + single port, sub-path deployment-proves the design fits **real** constraints, not only a greenfield stack. |
| **Phase / release exit criteria -> evidence** | Each completed phase or release slice should map to a **PR, doc section, or runbook command** - not "we improved logging" in the abstract. |
| **Before/after bullets** | Short list: what was true *before* Wave A (e.g. text logs only, no `/ready`, silent persistence failures) vs *after*. |
| **Trade-off log** | Link to [decision records](../decisions/README.md); add 1-2 sentences per major choice (Postgres deferred, error model before big split, policies before directory migration). |
| **Quantified quality** | Test counts, black-box coverage areas, CI gates (`lint-imports`, contract sync), latency percentiles you actually expose - **numbers you can defend**. |
| **Runbook pointers** | Where to read: deploy, rollback, backup, metrics scrape, readiness check - even if some sections are "TODO until Wave A lands."|

**Anti-pattern:** claiming "industrial grade" on the homepage while the repo still has ad-hoc schema changes, no metrics, and no readiness split. This document assumes **honesty lags marketing**.

---

## 2. The problem (portfolio framing)

**One-line pitch (refine for your voice):**  
A strategic-analysis chat product whose **reference** deployment includes **shared, unprivileged** infrastructure (no root, predictable port, browser-friendly SPA)-while the **same codebase** targets dev machines and other server layouts-with **local Ollama** inference and **durable session history**, without pretending every environment is a greenfield Kubernetes cluster.

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

5. **From governable -> semantically stable** (Phase 15)  
   Policy objects and invariants **before** large `application/` / `domain/` moves; session schema contract and normalization when migrations are already a first-class artifact.

6. **From semantically stable -> capability-gated runtime** (Phase 16A + Phase 17)
   Optional features stopped pretending to be boolean toggles. Code sandbox moved to separate **policy** vs **runtime** gates; workbench stopped being a placeholder-only idea and became a real task runtime with durable task rows, event timelines, source discovery, and minimal `plan` / `browse` / `deep_research` execution.

7. **From single-agent coding -> governed parallel change flow**
   The repo now carries a more explicit engineering-process story too: `CODEOWNERS`, stricter CI intent, contract sync, and Lead/subagent coordination rules mean the system is being shaped for **multi-threaded development under review**, not only solo hacking.

**Portfolio line:** *I did not optimize for demo screenshots; I optimized for the next engineer (often me in six months) to change the system safely.*

---

## 4. Key engineering decisions (senior-visible)

These are worth a **"Trade-offs"** subsection on a homepage. Align wording with the repo-native [decision record entrypoint](../decisions/README.md).

| Decision | Rough story |
|----------|-------------|
| **Postgres not by default** | Data and ops model fits SQLite until migration discipline and multi-instance needs force a move - avoid database theater. |
| **Wave A = observe + ready + persistence signals first** | Without logs, metrics, and readiness, retries and breakers are blind; client resilience is **Wave B** so it does not block operational lift. |
| **Migrations as artifacts (Phase 13 Section 13.0)** | Schema and session evolution are continuous; ad-hoc `ALTER` chains do not scale with feature velocity. |
| **Error model before / alongside observability** | Stable `code`s feed metrics labels and retry policy; runbooks reference the same taxonomy. |
| **Policies and invariants before big package split** | Semantic convergence reduces blast radius of directory refactors (Phase 15 ordering). |
| **Single-tenant / shared API key** | Threat model documented honestly; authz roadmap separated from "looks secure" shortcuts. |
| **Capability discovery before UI promises** | `/api/system/features` and `/api/workbench/sources` should say what is truly runnable today, not what is merely on the roadmap. |
| **Durable task contract before autonomous workflows** | `task_id`, polling, events, and source registry came before richer browse/research/canvas UX so future work can extend one runtime instead of spawning incompatible endpoints. |
| **Lead-integrated parallelism over uncontrolled agent edits** | Subagents are useful as auditors and analysts, but final patches and merge decisions stay centralized so architecture and contract drift do not accelerate with concurrency. |

---

## 5. Verifiable outcomes (what visitors can check)

Now that Phases 13-15 are complete and `v1.2.0` aligns the shipped docs, your homepage or README should point to **concrete hooks**:

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

- `goat_ai/llm/ollama_client.py` + `__tests__/backend/services/test_ollama_client_cache.py`
- `backend/services/idempotency_service.py` + `backend/migrations/005_add_idempotency_keys.sql`
- `backend/routers/upload.py` + `backend/routers/chat.py`
- `__tests__/backend/routers/test_upload_router.py` + `__tests__/contracts/test_api_blackbox_contract.py`
- `docs/operations/OPERATIONS.md` (multi-instance limitations + mitigations)

Phase 16A / 17 evidence anchors in this repo:

- `backend/services/system_telemetry_service.py` + `__tests__/backend/platform/test_feature_gates.py`
- `backend/routers/workbench.py` + `backend/application/workbench.py`
- `backend/services/workbench_runtime.py`
- `backend/services/workbench_execution_service.py`
- `backend/services/workbench_source_registry.py`
- `__tests__/backend/services/test_workbench_runtime.py`
- `__tests__/backend/services/test_workbench_source_registry.py`
- `__tests__/contracts/test_api_blackbox_contract.py`
- `docs/api/API_REFERENCE.md` + `docs/architecture/WORKBENCH_TERMINOLOGY_DECISION.md`

---

## 6. "Homepage-ready" bar (not tied to marketing-only version bumps)

Treat the project as **homepage-worthy** when **most** of the following are true -grounded in **Phase 13/14/15 exit criteria**, not a version string:

- [ ] Clear **README** + **architecture overview** (diagram or layered description).
- [ ] **Demo** (short video or screenshots) showing chat + upload + chart path -product, not only infra.
- [ ] A **before ->after** engineering section (this file or a linked case study) with **dated** milestones.
- [ ] A **trade-offs / decisions** page or section (can be this doc + [decision records](../decisions/README.md)).
- [ ] **Quantified** testing and CI story (what gates exist, what they protect).
- [ ] **Operational evidence**: how logs and metrics are consumed; how readiness and rollback are run; how migrations are validated.
- [ ] **Honest constraint paragraph**: shared host, no root, SQLite-first -and why that is **reasonable**, not accidental.
- [ ] **Capability honesty**: task/runtime surfaces only claim what is actually runnable; docs and telemetry match real behavior.
- [ ] **Reviewable engineering process**: CI, ownership, contract sync, and architecture gates show that parallel change does not mean uncontrolled change.

**Optional stretch (strong portfolio):** one paragraph on **what you would do next** if the product gained ten times the traffic (without hand-waving -reference Phase 15 normalization, Postgres gate, etc.).

---

## 7. Why this belongs on a personal homepage (summary)

- **Full product shape** -SPA, streaming API, persistence, charts, access controls -not a single-script demo.
- **Real constraints** -shared machine, no root, local inference -reads as production-adjacent engineering.
- **Governance story** -boundaries, tests, observability, data migration, runbooks -reads as **systems thinking**, not feature churn.
- **Runtime story** -the product now has the start of a real agent/workbench runtime rather than only a chat shell, which is a more senior systems signal than adding another front-end mode toggle.

The differentiator is not the stack list; it is **the documented path from demo-quality to maintainable-quality** under constraints you did not choose.

---

## Related documents

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - shipped release inventory and current known boundaries.
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md) - historical phase closeouts and archived sequencing context.
- [ROADMAP.md](ROADMAP.md) - unfinished work only.
- [OPERATIONS.md](../operations/OPERATIONS.md) -deploy, env, host constraints (keep aligned with claims on your homepage).
- [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md) - canonical engineering contract.
- [AGENTS.md](../../AGENTS.md) - agent memory and collaboration guide; canonical engineering rules stay in ENGINEERING_STANDARDS.

---

### 8. Current portfolio posture at v1.2.0

`v1.2.0` is a sensible portfolio checkpoint because the codebase now combines:

- completed backend industrialization and hardening across Phases 11-15
- a real retrieval and media path rather than a chat-only shell
- frontend control-surface polish that makes upload management, model controls, options, and dark-mode presentation look like a maintained product
- the first credible workbench/runtime layer: durable task creation, polling, event timelines, source registry, and minimal retrieval-backed task execution
- capability-gated feature reporting that separates "operator enabled" from "actually runnable right now"
- clearer multi-thread development governance via ownership, review, and contract-sync discipline
- supporting docs that explain not just what shipped, but why the sequencing and trade-offs were chosen

That does **not** mean the story is "finished." The next senior-visible chapter is the unfinished work still tracked in [ROADMAP.md](ROADMAP.md): deeper workbench/runtime behavior, project memory and connectors, sandbox follow-ons, and broader desktop distribution maturity.

An honest homepage summary at this point is not "I built an AGI product." It is: **I turned an AI app into an increasingly governable system, then started building the runtime substrate that future agent workflows can safely stand on.**

---

*Last updated: 2026-04-13 - aligned with the current roadmap/status/archive split so the portfolio narrative stays separate from canonical repo-truth docs.*
