# GOAT AI — Roadmap

> Last updated: 2026-04-06 · Current release: **v1.1.0**  
> **Compact snapshot (APIs, SSE, deploy, tests):** [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## ✅ Shipped (v1.1.0)

| Phase | Content |
|-------|---------|
| 0 | Environment verification — Node 18, Vite 5, FastAPI smoke test |
| 1 | FastAPI backend: `/api/health`, `/api/models`, `/api/chat` SSE, `/api/upload` SSE |
| 2 | React frontend: Sidebar, ChatWindow, MessageBubble (Markdown), FileUpload, useChat/useModels/useTheme hooks, Tailwind CSS, navy+gold brand |
| 3 | Production deploy: `deploy.sh` (git pull → npm build → uvicorn :62606), nginx proxy via `ai.simonbb.com/mingzhi/` |
| 4 | Polish: copy button, ErrorBoundary, error message styling, gold SVG goat icon, Simon Business School logo, Actions alignment |
| 5 | Reliability + UX: stop streaming button, local session restore, SQLite conversation logging |
| 6 | Core feature expansion: conversation history sidebar (restore/delete), file context persistence across turns |

---

## 🔜 Phase 7 — Quality & Observability

**Goal:** make the app production-hardened before a wider audience.

**No-root production (JupyterHub / shared A100):** system `logrotate`, `supervisord`, and reliable `systemctl --user` are **not** guaranteed — see [OPERATIONS.md](OPERATIONS.md) (*Shared host permissions*, *User-space ops*). Prefer `deploy.sh` nohup + `scripts/watchdog.sh`, user crontab + [`scripts/rotate_fastapi_log.py`](../scripts/rotate_fastapi_log.py), and optional `goat-ai.service` **only after** `systemctl --user status` works on that host.

| Task | Notes |
|------|-------|
| Loading skeleton | Pulse animation on first SSE token wait (replace blinking cursor) |
| Process resilience | **Ideal:** `systemd --user` unit (`goat-ai.service`) *if* user bus works. **Fallback:** nohup + `fastapi.pid`, tmux, [`scripts/watchdog.sh`](../scripts/watchdog.sh) — see [OPERATIONS.md](OPERATIONS.md) |
| Log rotation | **Not** system `/etc/logrotate.d` without root. Use [`scripts/rotate_fastapi_log.py`](../scripts/rotate_fastapi_log.py) (`GOAT_LOG_MAX_MB`, archive under `logs/archive/`) + cron |
| Backend unit tests | `pytest` for services; mock Ollama via `FakeLLMClient` ([ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)) |
| Frontend tests | Vitest in `frontend/src/__tests__/` |
| CI (GitHub Actions) | `pytest` + `frontend` `npm test` on push to `main` |

---

## 🔜 Phase 8 — Demo Power Features

**Shipped (initial):** upload `chart_spec` + Recharts `ChartCard`; `GET /api/system/gpu` + sidebar strip; rolling chat inference latency via `GET /api/system/inference`; Markdown export (TopBar); `deploy.sh` always `npm ci` before build. **Still open:** richer chart contracts from LLM text, polish.

| Feature | Value |
|---------|-------|
| **Structured Data Viz (Recharts)** | CSV/XLSX analysis returns chart spec + narrative; frontend renders line/bar chart cards |
| **A100 live status strip (real telemetry)** | Left sidebar shows real GPU utilization, memory, power, and rolling inference latency |
| **Model info tooltip** | Show param count / context window on hover over model name |
| **Markdown export** | Download conversation as `.md` file (TopBar — client-side) |
| **System prompt editor** | Let user override the system prompt per session |

### Phase 8 implementation strategy

1. **Data Viz contract first (backend->frontend typed payload)**  
   Add structured chart payload (type/xKey/series/title/data) in upload/chat analysis responses; keep text narrative as fallback.
2. **Render with Recharts in a dedicated panel/card**  
   Frontend displays charts only when contract validates; malformed payload degrades to text-only safely.
3. **GPU telemetry must be real**  
   Backend reads A100 stats from `nvidia-smi --id=0` (or UUID lock), never hardcoded values.
4. **Latency source is request timing**  
   Show rolling latency derived from chat/upload completion timings in backend service metrics.

---

## 🔜 Phase 9 — Access & Security

| Task | Notes |
|------|-------|
| **Password / API key gate** | Simple token auth on FastAPI; avoid exposing Ollama publicly |
| **nginx HTTPS** | Engage school IT to enable nginx with TLS on `ai.simonbb.com` |
| **Rate limiting** | `slowapi` middleware — prevent accidental abuse |
| **Request logging** | Structured JSON logs; never log message content |

---

## Infrastructure Notes

| Item | Current | Target |
|------|---------|--------|
| Server | A100 Ubuntu 24.04 | same |
| Public URL | `https://ai.simonbb.com/mingzhi/` | same (or dedicated subdomain) |
| Port | 62606 (nginx proxy) | 62606 |
| Process mgmt | `nohup` + PID file (default on no-root hosts) | systemd --user *if* bus works; else watchdog/tmux |
| Log files | `fastapi.log` + user-space rotation script | Same; IT logrotate only with root |
| Node version | 18.19.1 (TLJH fixed) | 18.19.1 |
| Python | 3.12.6 | 3.12.6 |

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-30 | Use port 62606 (not 8002) | Only 62606 is reachable through school nginx |
| 2026-03-30 | Vite `base: './'` | Required for JupyterHub proxy and nginx sub-path compatibility |
| 2026-03-30 | SSE over WebSocket | Simpler, works through more proxies, native browser `EventSource` |
| 2026-03-30 | No React Router | Single-page app; routing adds complexity with no benefit |
| 2026-03-31 | Dual-port deploy reverted | Production uses :62606 only |
