# GOAT AI — Roadmap

> Last updated: 2026-04-07 · Current release: **v1.2.0**  
> **Compact snapshot (APIs, SSE, deploy, tests):** [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## ✅ Shipped (v1.2.0)

| Phase | Content |
|-------|---------|
| 0 | Environment verification — Node 24, Vite 8, FastAPI smoke test |
| 1 | FastAPI backend: `/api/health`, `/api/models`, `/api/chat` SSE, `/api/upload` SSE |
| 2 | React frontend: Sidebar, ChatWindow, MessageBubble (Markdown), FileUpload, useChat/useModels/useTheme hooks, Tailwind CSS, navy+gold brand |
| 3 | Production deploy: `deploy.sh` (local checkout → npm build → uvicorn :62606), nginx proxy via `ai.simonbb.com/mingzhi/` |
| 4 | Polish: copy button, ErrorBoundary, error message styling, gold SVG goat icon, Simon Business School logo, Actions alignment |
| 5 | Reliability + UX: stop streaming button, local session restore, SQLite conversation logging |
| 6 | Core feature expansion: conversation history sidebar (restore/delete), file context persistence across turns |
| 7 | Quality and observability hardening: user-space log rotation and watchdog scripts, no-root deploy fallback, broader backend tests, frontend Vitest coverage, CI workflow, request IDs and latency metrics |
| 8 | Demo power features: structured `chart_spec` payloads, Recharts `ChartCard`, real A100 GPU telemetry, rolling inference latency, Markdown export, dependency-safe frontend deploys |
| 9 | Access and security: API key gate for protected routes, rate limiting, request tracing headers, and production-safe access controls around the FastAPI surface |

---

## Infrastructure Notes

| Item | Current | Target |
|------|---------|--------|
| Server | A100 Ubuntu 24.04 | same |
| Public URL | `https://ai.simonbb.com/mingzhi/` | same (or dedicated subdomain) |
| Port | 62606 (nginx proxy) | 62606 |
| Process mgmt | `nohup` + PID file (default on no-root hosts) | systemd --user *if* bus works; else watchdog/tmux |
| Log files | `fastapi.log` + user-space rotation script | Same; IT logrotate only with root |
| Node version | 24.14.1 (`.nvmrc`) | 24.x |
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
