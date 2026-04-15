# GOAT AI - Engineering Story & Portfolio Copy

This document is a portfolio-facing writing surface rather than a canonical
repository-truth document.

Use these files for the live repo state instead:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [ROADMAP.md](ROADMAP.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)
- [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md)

The goal here is simpler: keep high-quality finished copy that can be reused for
portfolio pages, resume bullets, LinkedIn project entries, or application
materials without having to reconstruct the story from commit history later.

---

## Long Version

### Portfolio headline

**GOAT AI**  
Personal Full-Stack AI Systems Project · React 19 + TypeScript + Vite +
FastAPI + Python + Ollama + SQLite/Postgres + Tauri

Built and shipped a local-first / self-hostable AI product that combines chat,
retrieval, durable sessions, artifact generation, browser-gated public access,
bounded research workflows, and deployment-grade operational controls across
desktop, local server, school server, and public remote hosting modes.

Architected the application as a typed React SPA + FastAPI backend with stable
JSON error contracts, typed SSE streaming, persisted history, artifact download
surfaces, and environment-driven deployment isolation. The shipped system
supports three explicitly separated deployment modes (`local`,
`school_server`, `remote`) with fail-fast config validation, mode-specific
operational behavior, and remote-only authentication controls.

Engineered a production-style LLM interaction layer on top of Ollama, including
typed stream events (`thinking`, `token`, `chart_spec`, `artifact`, `error`,
`done`), server-side model-surface control, process-local inference concurrency
gating, FIFO request queueing, rate limiting, and public-safe allowlist
enforcement for hosted deployments. The same codebase still preserves
unrestricted local and school-server model visibility where operator-controlled
environments need full installed-model access.

Built a durable retrieval and knowledge pipeline covering uploads, ingestion,
normalization, retrieval-backed answering, and chat-grounded synthesis for
tabular and document formats (`csv`, `xlsx`, `txt`, `md`, `pdf`, `docx`).
Storage evolved from direct local-path assumptions into an explicit metadata +
object-store boundary with canonical `storage_key` handling, backup/restore
parity tooling, and an opt-in Postgres runtime metadata path for
hosted/server-side operation.

Designed and shipped a browser-facing authentication model that preserved
backward compatibility while expanding capability: shared-password browser
isolation, account login, Google login, signed HttpOnly session cookies, and
unified `/api/auth/session` state handling. The implementation kept the
original shared-password flow intact while adding a parallel account-based path
that integrates with the same protected API surface for history, uploads,
artifacts, model access, and chat.

Implemented bounded runtime surfaces instead of open-ended “AI autopilot”
claims. The shipped workbench runtime supports durable tasks, event timelines,
typed workspace outputs, bounded browse/deep-research flows, and caller-scoped
source access. Retrieval sources, capability discovery, and runtime execution
were progressively split into narrower seams so the platform could grow without
collapsing router, runtime, and persistence concerns into one monolith.

Built a Docker-first code sandbox execution path with durable execution records,
replayable logs, queued/running cancellation, fail-closed restart recovery,
workspace manifesting, and explicit capability gating between policy denial and
runtime unavailability. The localhost fallback remains available for trusted
development, but the shipped contract keeps operator intent and runtime
readiness explicit rather than pretending risky capabilities are universally on.

Expanded the project into a desktop-distribution path with a Tauri 2 shell, a
PyInstaller-built backend sidecar, Windows MSI/NSIS packaging, packaged startup
diagnostics, restart/backoff behavior before UI reveal, and retained
provenance/fault evidence in CI. Linux packaged-desktop provenance is also
wired, while macOS distribution remains honestly blocked behind
signing/notarization prerequisites rather than being overstated in
documentation.

Treated engineering governance as part of the product surface rather than
after-the-fact cleanup. The repository carries contract artifacts, decision
records, release governance, rollback and backup runbooks, observability
assets, branch/deploy posture docs, and mechanical proof gates across backend,
frontend, desktop packaging, contracts, and selected fault-injection flows. CI
is structured so fast failure layers catch formatting, contract drift, and
path-boundary regressions before deeper runtime checks run.

Refactored multiple brownfield hotspots into narrower composition seams across
backend orchestration, workbench execution, knowledge-chat integration, and
frontend chat-session control. The goal was not abstract “clean architecture”
theater, but preserving delivery speed while steadily reducing places where one
file silently owned too much runtime behavior.

The result is a repository that demonstrates not only AI feature delivery, but
also the harder parts of real software engineering in AI products:
deterministic contract maintenance, deployment isolation, operational rollback
posture, capability gating, evidence-backed runtime claims, and honest handling
of what is shipped versus what is intentionally deferred.

### Representative engineering themes

- AI application architecture with typed frontend/backend contracts
- local-first and self-hostable deployment design
- LLM streaming, model policy, rate limiting, and concurrency control
- retrieval-backed chat and document ingestion pipelines
- authentication expansion without breaking existing product behavior
- durable async/runtime workflows with bounded research execution
- safe code-execution boundaries with operator-visible capability gating
- desktop packaging, sidecar orchestration, and release evidence
- brownfield refactoring under active delivery pressure
- mechanical governance through tests, contracts, and CI workflows

### Core stack

- React 19
- TypeScript
- Vite
- FastAPI
- Python
- Ollama
- SQLite
- Postgres
- Tauri 2
- PyInstaller
- Vitest
- Pytest
- Ruff
- GitHub Actions
- Nginx
- Docker

---

## Resume Version

### Resume-ready project entry

**GOAT AI**  
Personal Full-Stack AI Systems Project · React 19 + TypeScript + Vite +
FastAPI + Python + Ollama + SQLite/Postgres + Tauri

- Engineered a self-hostable AI product spanning chat, retrieval, durable
  sessions, artifact generation, browser login, and bounded workbench/runtime
  flows across local, school-server, desktop, and public remote deployment
  modes.
- Architected typed frontend/backend contracts with stable JSON error models,
  typed SSE event streaming, persisted artifact/session surfaces, and
  fail-fast deployment-mode isolation for `local`, `school_server`, and
  `remote` runtime shapes.
- Built a production-style Ollama integration layer with server-side public
  model controls, FIFO inference queueing, request-rate limiting, and
  concurrency gating, while preserving unrestricted model visibility for local
  operator-controlled environments.
- Delivered durable retrieval and knowledge pipelines for tabular/document
  uploads plus retrieval-backed answering/chat, and evolved storage from direct
  local-path assumptions into an object-store-ready `storage_key` boundary with
  backup/restore and hosted Postgres metadata support.
- Implemented bounded workbench and code-sandbox runtimes with durable task and
  execution records, replayable logs, queued/running cancellation, fail-closed
  restart recovery, and explicit capability gating between policy denial and
  runtime unavailability.
- Added desktop packaging and release evidence through a Tauri 2 shell,
  PyInstaller sidecar, Windows MSI/NSIS packaging, Linux packaged provenance,
  startup fault diagnostics, and GitHub Actions workflows retaining packaging,
  smoke, and release-governance evidence.

### Resume keyword stack

- React 19
- TypeScript
- Vite
- FastAPI
- Python
- Ollama
- SQLite
- Postgres
- Tauri 2
- PyInstaller
- Docker
- GitHub Actions
- Nginx
- Vitest
- Pytest
- Ruff

---

## LinkedIn Version

### LinkedIn project summary

Built **GOAT AI**, a self-hostable full-stack AI product combining an Ollama
chat runtime, retrieval-backed document workflows, durable sessions/artifacts,
browser-based access control, and bounded research/task execution across local,
school-server, desktop, and public remote deployment modes.

On the engineering side, I treated it as a systems project rather than a thin
LLM wrapper: typed React/FastAPI contracts, stable SSE and error surfaces,
deployment-mode isolation, FIFO/concurrency control for local inference,
rate-limited hosted model exposure, backup/restore posture, and documented
rollback/deploy runbooks.

I also built the operational and release layer around it: Tauri desktop shell,
PyInstaller sidecar, Windows MSI/NSIS packaging, Linux packaged provenance,
fault-oriented startup diagnostics, and CI workflows that retain packaging,
contract, and release-governance evidence.

What I’m most proud of is that the repo demonstrates honest engineering
trade-offs: local-first AI, bounded runtime behavior, explicit capability
gating, and maintainable delivery under real deployment constraints rather than
inflated “autonomous AI” claims.

### LinkedIn keywords

React, TypeScript, Vite, FastAPI, Python, Ollama, SQLite, Postgres, Tauri,
PyInstaller, Docker, GitHub Actions, Nginx, Retrieval-Augmented Generation
(RAG), SSE streaming, deployment automation, desktop packaging, AI systems
engineering

---

## Notes for future trimming

- The **Long Version** is the source text for portfolio pages and case-study
  narratives.
- The **Resume Version** should be shortened again depending on space.
- The **LinkedIn Version** is intentionally less technical-dense and more
  product/system-oriented.
- Keep the claims here aligned with
  [PROJECT_STATUS.md](PROJECT_STATUS.md) and
  [ROADMAP.md](ROADMAP.md) if the shipped surface changes.

---

*Last updated: 2026-04-14.*
