# GOAT AI — Project status snapshot

> **Purpose:** compact handoff for new chats / reviewers when context is full.  
> **Last updated:** 2026-04-07  
> **Authoritative detail:** [OPERATIONS.md](OPERATIONS.md) (run/deploy/env), [ROADMAP.md](ROADMAP.md) (phases), [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) (code rules).

---

## 1. What this repo is

- **Product:** Simon Business School “GOAT AI” — React SPA + FastAPI, Ollama for LLM, SSE streaming.
- **Prod URL:** `https://ai.simonbb.com/mingzhi/` → nginx → FastAPI on host port **62606** (not 8002 on server).
- **Repo:** `https://github.com/mingzhi0119/GOAT_AI` — active production work is currently happening directly on the server checkout; keep `main` and docs aligned.

---

## 2. Stack (unchanged core)

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| LLM | Ollama HTTP (`OLLAMA_BASE_URL`) |
| Frontend | React 19, TypeScript strict, Vite 8, Tailwind 3 |
| Data | pandas + openpyxl for CSV/XLSX |
| Logs | SQLite `chat_logs.db` (`GOAT_LOG_PATH`) |

---

## 3. Shipped capabilities (recent + core)

- **Chat:** `POST /api/chat` — SSE tokens, optional `session_id`, logging + **session persistence** in SQLite (`sessions` table + `conversations.session_id`).
- **Upload:** `POST /api/upload` — parse CSV/XLSX, SSE stream; emits **`file_context`** (filename + analysis prompt for follow-up) and **`chart_spec`** (structured chart for Recharts when numeric data exists).
- **History API:** `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history/{id}` — sidebar list / restore / delete.
- **GPU telemetry:** `GET /api/system/gpu` — real `nvidia-smi` stats; UI polls ~5s; env **`GOAT_GPU_UUID`** (preferred) or **`GOAT_GPU_INDEX`** (default `0`).
- **Inference latency:** `GET /api/system/inference` — rolling average duration (ms) of completed chat streams; shown in GPU dot tooltip; window size **`GOAT_LATENCY_ROLLING_MAX_SAMPLES`** (default `20`).
- **HTTP safety:** optional shared-secret protection on all non-health routes via **`GOAT_API_KEY`** + `X-GOAT-API-Key`, request tracing with `X-Request-ID`, and per-key in-memory rate limiting via **`GOAT_RATE_LIMIT_WINDOW_SEC`** / **`GOAT_RATE_LIMIT_MAX_REQUESTS`**.
- **Modular API surface:** upload parsing is now available both as SSE (`POST /api/upload`) and plain JSON (`POST /api/upload/analyze`) so external services can reuse the same core analysis logic without consuming a stream.
- **Frontend:** Sidebar history, file-context chip, **GPU status strip** under Actions, **ChartCard** (Recharts) when `chart_spec` received; static sidebar label styles in `sidebarStaticText.ts`.
- **Deploy fix (important):** `deploy.sh` runs **`npm ci` before every `npm run build`** so new deps (e.g. `recharts`) are never missing on servers that already had `node_modules/`. By default it now deploys the current local checkout on the server; `SYNC_GIT=1` is opt-in.

---

## 4. API surface (current)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/health` | Liveness |
| GET | `/api/models` | Ollama model list |
| POST | `/api/chat` | SSE; body includes optional `session_id` |
| POST | `/api/upload` | SSE; see events below |
| POST | `/api/upload/analyze` | JSON upload analysis payload for external integrations |
| GET | `/api/history` | Session list (metadata) |
| GET | `/api/history/{session_id}` | Full session + messages JSON |
| DELETE | `/api/history/{session_id}` | Delete session |
| GET | `/api/system/gpu` | GPU JSON for status strip |
| GET | `/api/system/inference` | Rolling avg chat stream ms + sample count |

---

## 5. SSE conventions

- **Chat / upload token stream:** `data: <json string>\n\n` per token; ends with `"[DONE]"`.
- **Upload structured events (JSON object in `data:` line):**
  - `type: "file_context"` — `filename`, `prompt`
  - `type: "chart_spec"` — `chart` (line/bar spec + rows)

Frontend parsers: `frontend/src/api/chat.ts`, `frontend/src/api/upload.ts`.

---

## 6. SQLite (high level)

- **`conversations`:** per-completion log rows; includes optional **`session_id`**.
- **`sessions`:** one row per chat session (`id`, `title`, `model`, `messages` JSON, timestamps).

---

## 7. Tests & CI commands (local)

```bash
# Backend
python -m pytest __tests__/ -v

# Frontend
cd frontend && npm test -- --run && npm run build
```

CI: `.github/workflows/ci.yml` — `pytest` + `npm test` + `npm run build` on pushes/PRs to `main` (frontend job uses **Node 24.14.1** to match `.nvmrc` and the project build target).

Note: `test_history_router.py` may **skip** if `fastapi` is not installed in the active Python env.

---

## 8. Server deploy pitfalls (memory)

1. **Wrong directory:** run `deploy.sh` from repo root (e.g. `~/GOAT_AI`), not `~`.
2. **`Cannot find module 'recharts'`:** fixed by deploy script always running `npm ci` before build; or manually `cd frontend && npm ci`.
3. **Pip “dependency conflicts”** on shared Jupyter images: usually warnings from unrelated packages; GOAT’s own `requirements.txt` install still completes — treat as noise unless install fails.
4. **GPU strip “unavailable”:** check `nvidia-smi`, `GOAT_GPU_UUID` / `GOAT_GPU_INDEX`, and that the process can execute `nvidia-smi`.

---

## 8b. Server permissions snapshot (JupyterHub A100)

**Last verified:** 2026-03-31 · User: `jupyter-mhu29@simon.roches-bde1e` · Host: `simon.roches-bde1e` (A100).

| You have | You do not have |
|----------|-----------------|
| Home dir + `~/GOAT_AI`, venv, bind **`0.0.0.0:62606`**, run **uvicorn** as your user | **sudo/root** (*no new privileges* blocks elevation) |
| **`nvidia-smi`** (GPU 0 = A100, UUID `GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`; GPU 1 = GT 1030) | System **logrotate** writes, **`apt install`**, **supervisor** |
| Read **`/etc/nginx/nginx.conf`**; **`loginctl` → Linger=yes** | **`systemctl --user`** in SSH often fails (*No medium found*); **nginx reload**; **`/etc/logrotate.d`** |

Authoritative table and implications: [OPERATIONS.md](OPERATIONS.md) (section **Shared host permissions**). **Deploy:** use `deploy.sh` nohup fallback when user systemd is unavailable.

**Ops without root:** log rotation, SQLite backup, healthcheck, optional tmux watchdog — [OPERATIONS.md — User-space ops](OPERATIONS.md#user-space-ops-no-root).

---

## 9. Docs map

| File | Role |
|------|------|
| [OPERATIONS.md](OPERATIONS.md) | Env vars, deploy, health, GPU probes, API table |
| [API_REFERENCE.md](API_REFERENCE.md) | Full request/response/error contract for backend consumers |
| [ROADMAP.md](ROADMAP.md) | Phases, shipped vs planned |
| [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) | Coding and test standards |
| **PROJECT_STATUS.md** (this file) | **Compact snapshot for context reset** |

---

## 10. Current maintenance notes

- `ROADMAP.md` Phase 7-9 are now reflected as shipped and should stay aligned with the actual repo state.
- Deploy changes should keep the no-root server constraints and local-checkout deploy workflow intact.
