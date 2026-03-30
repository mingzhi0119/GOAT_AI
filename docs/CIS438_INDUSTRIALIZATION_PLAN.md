# GOAT AI — Industrialization Plan

**Course:** CIS 438 — *Agentic AI Application*  
**Target:** Production-grade web application, **Python-only** (Streamlit + backend services).  
**Runtime:** JupyterLab / shared Linux server (typical constraints: long-running jobs, ports, no root).  
**Status:** Project 1 / Pre 1 rubrics **not yet published** — section below is a placeholder to map work once announced.

---

## 1. What “industrial-grade” means (for this project)

| Area | Minimum bar | Stretch |
|------|-------------|---------|
| **Reliability** | Process survives disconnects (`nohup`/supervisor), health checks, clear restart path | systemd user unit or Jupyter “Services” pattern |
| **Security** | Secrets via env vars, no API keys in repo, HTTPS at reverse proxy, Ollama not exposed to public internet without auth | Basic auth or SSO at proxy; rate limits |
| **Observability** | Structured logs (`streamlit.log`), timestamps, error messages that don’t leak internals | Log rotation, simple metrics (request counts / errors) |
| **Maintainability** | `requirements.txt` pinned, `deploy.sh` idempotent, `.streamlit/config.toml` in repo | CI smoke test (import app, lint) |
| **Agentic AI fit** | Clear agent loop: user goal → model + tools → grounded answer | Tool definitions (e.g. data summary, retrieval), guardrails |
| **UX** | Readable in light/dark, branding assets local, responsive layout where Streamlit allows | Upload limits, progress for long runs |

“Industrial” here does **not** require React — it requires **predictable operations**, **safe defaults**, and **clear failure modes**.

---

## 2. Constraints: JupyterLab server

- Prefer **one** long-lived app process (Streamlit) on a **dedicated port** (e.g. `62606`), started from the project directory so `.streamlit/` and `static/` resolve.
- Avoid binding ports `<1024` without admin; use **reverse proxy** (or Jupyter proxy) for HTTPS and path prefixes.
- **Ollama** should listen on `127.0.0.1` unless strictly firewalled; app talks via `OLLAMA_BASE_URL`.
- Note **session lifetime**: Jupyter kernels ≠ Streamlit server; document that `deploy.sh` / `nohup` is the supported way to run the site.

---

## 3. Phase 0 — Remove React (single frontend stack)

**Goal:** One deployable surface: **Streamlit (`app.py`)** only.

**Actions (checklist):**

- [x] Remove `frontend/` (Vite/React) from the repository.
- [x] Update `deploy.sh`: drop `npm ci` / `npm run build` branches; comment header should say Streamlit-only.
- [x] `DEVELOPMENT_PLAN.md` — deprecation notice at top; React sections kept as archive only.
- [ ] Confirm public URL strategy: Streamlit only (no `/mingzhi/` SPA unless you still proxy static assets elsewhere).

**Why:** Fewer moving parts (no Node on server), one dependency graph (`pip`), aligned with “Python-only industrial” delivery.

---

## 4. Phase 1 — Streamlit hardening (product shell)

- **Configuration:** Keep `.streamlit/config.toml` (theme, base) under version control; document required env vars (`OLLAMA_BASE_URL`, `OLLAMA_GENERATE_TIMEOUT`).
- **Assets:** `static/` for logos; never rely on blocked external CDNs for critical UI.
- **CSS:** Keep main content readable under system dark mode; avoid white-on-white (already addressed — maintain as regression checks).
- **Errors:** User-facing messages vs. log-only details; avoid leaking stack traces in UI.
- **Uploads:** Max size and row limits for CSV/XLSX; clear message when exceeded.
- **Dependencies:** Pin versions in `requirements.txt` (or `requirements.lock` via `pip freeze` in a controlled env).

---

## 5. Phase 2 — Agentic AI (align with **CIS 438** title)

Map features to a simple **agent loop** (even if implemented incrementally):

1. **Perceive:** User message + optional tabular context from upload.
2. **Plan:** Decide whether to call tools (e.g. summarize dataframe, answer from scratch).
3. **Act:** Call Ollama (`/api/generate` or chat API if you migrate).
4. **Verify:** Short self-check or citation of dataframe shape/columns in the answer.

**Concrete upgrades:**

- [ ] **System prompt** stored in one place (env or config), Simon/UR policy-safe.
- [ ] **Tool-style functions** in Python (e.g. `describe_dataframe(df)` → inject into prompt) — *agentic* without a second framework.
- [ ] Optional: **Ollama chat** endpoint with message history for multi-turn coherence.
- [ ] Optional: **Retrieval** (RAG) only if course scope allows; otherwise skip to keep scope tight.

---

## 6. Phase 3 — Deployment & operations (JupyterLab-friendly)

- [ ] **Single command:** `bash deploy.sh` (or `./deploy.sh` after chmod) from `$HOME/GOAT_AI`.
- [ ] **PID + logs:** `streamlit.pid`, `streamlit.log`; document how to stop: `kill $(cat streamlit.pid)`.
- [ ] **Health:** `curl` to `/_stcore/health` locally; optional cron or manual check.
- [ ] **Reverse proxy:** Document path for your school host (e.g. `https://…/mingzhi/` → `http://127.0.0.1:62606/`) with WebSocket notes for Streamlit.
- [ ] **Resource:** If GPU is shared, note expected Ollama concurrency and model size.

---

## 7. Phase 4 — Security & compliance (minimum viable)

- [ ] **Secrets:** never commit `.env`; document `export` lines for the server.
- [ ] **Network:** Ollama bound to localhost; Streamlit behind proxy if exposed.
- [ ] **Data:** Uploaded files only in memory/session; no persistent storage of user data unless required — state in report if needed.

---

## 8. Placeholder: Project 1 / Pre 1 rubrics

When the instructor publishes rubrics, paste them here and map each to a section:

| Rubric item | Where we address it | Status |
|-------------|---------------------|--------|
| *TBD* | | |

---

## 9. Definition of done (release checklist)

- [ ] `deploy.sh` runs end-to-end on JupyterLab host without Node.js.
- [ ] Streamlit loads logo from `static/`; chat readable in dark/light.
- [ ] Ollama integration works with env-configured base URL.
- [ ] README or `docs/` explains: install, run, deploy, stop, logs, env vars.
- [ ] Agentic narrative (short paragraph) for the report: loop + tools + limitations.

---

## 10. Suggested timeline (adjust after rubrics drop)

| Week | Focus |
|------|--------|
| 1 | Phase 0–1 complete; rubric mapping |
| 2 | Agentic features + prompts + upload safety |
| 3 | Ops hardening + proxy doc + demo script |
| 4 | Polish + report + recording |

---

*Last updated: 2026-03-30 (course code CIS 438; subject to rubric updates).*
