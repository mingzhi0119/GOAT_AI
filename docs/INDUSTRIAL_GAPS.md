# GOAT AI — Industrial-Grade Gaps (Backlog)

This document records **known gaps** relative to a production SaaS–style bar (tests, resilience, observability, abstraction). The app already meets the **CIS 438 / course** bar for layered modules and Streamlit deployment; items below are **optional follow-ups**.

**Last reviewed:** 2026-03-30

---

## 1. Testing & CI

| Gap | Why it matters | Suggested direction |
|-----|----------------|---------------------|
| No automated tests | Regressions in `tools`, `uploads`, or message shaping are caught only manually | Add `pytest`; unit-test `goat_ai.tools`, `goat_ai.uploads`, `messages_for_ollama` / `conversation_transcript` |
| No CI pipeline | No gate on PRs | GitHub Actions: `pip install -r requirements.txt`, `pytest`, optional `ruff` or `python -m compileall` |
| Ollama not mocked in tests | Network flakiness if integration tests hit real Ollama | Use `responses`, `pytest-httpserver`, or inject a fake `OllamaService` |

---

## 2. Resilience & HTTP client

| Gap | Why it matters | Suggested direction |
|-----|----------------|---------------------|
| `requests` without retries | Transient failures on shared Jupyter / lab hosts | `urllib3` Retry adapter or `tenacity` around Ollama calls |
| No circuit breaker | Cascading slowness if Ollama is down | Simple failure state + user-visible “degraded” banner |
| No request timeouts on streaming edge cases | Long-hanging streams | Already have `OLLAMA_GENERATE_TIMEOUT`; validate behavior under slow streams |

---

## 3. Observability

| Gap | Why it matters | Suggested direction |
|-----|----------------|---------------------|
| Logs only to stderr / no rotation | Hard to operate on long runs | `RotatingFileHandler` or log shipper; document in `docs/OPERATIONS.md` |
| No metrics | Cannot see error rate or latency | Minimal counters (e.g. requests, failures) or external metrics if host allows |
| No correlation IDs | Hard to trace one user action across log lines | Optional request/session id in log context |

---

## 4. Architecture & extensibility

| Gap | Why it matters | Suggested direction |
|-----|----------------|---------------------|
| `OllamaService` is concrete | Swapping LLM backend requires edits | `Protocol` + factory; or `LLMClient` interface with `OllamaClient` implementation |
| UI tied to Streamlit | Reuse business logic in other surfaces | Further extract pure “chat orchestration” in `goat_ai/services/` (optional) |
| Session state keys centralized but not persisted | Refresh loses chat; no multi-tab story | By design for privacy; document if needed |

---

## 5. Security & compliance (stretch)

| Gap | Notes |
|-----|--------|
| Auth / rate limiting at app | Usually handled at reverse proxy; document if not in scope |
| Uploaded data | In-memory only; re-confirm if retention is required |

---

## 6. Definition of done (when closing this backlog)

- [ ] `pytest` passes locally and in CI.
- [ ] Ollama integration covered by mock or contract tests.
- [ ] Operational docs updated for logging and any new env vars.

---

*See also: `docs/CIS438_INDUSTRIALIZATION_PLAN.md`, `docs/OPERATIONS.md`.*
