# GOAT AI — Roadmap

> Last updated: 2026-03-30 · Current release: **v1.0.0 MVP**

---

## ✅ Shipped (v1.0.0)

| Phase | Content |
|-------|---------|
| 0 | Environment verification — Node 18, Vite 5, FastAPI smoke test |
| 1 | FastAPI backend: `/api/health`, `/api/models`, `/api/chat` SSE, `/api/upload` SSE |
| 2 | React frontend: Sidebar, ChatWindow, MessageBubble (Markdown), FileUpload, useChat/useModels/useTheme hooks, Tailwind CSS, navy+gold brand |
| 3 | Production deploy: `deploy.sh` (git pull → npm build → uvicorn :62606), nginx proxy via `ai.simonbb.com/mingzhi/` |
| 4 | Polish: copy button, ErrorBoundary, error message styling, gold SVG goat icon, Simon Business School logo, Actions alignment |

---

## 🔜 Phase 5 — Quality & Observability

**Goal:** make the app production-hardened before a wider audience.

| Task | Notes |
|------|-------|
| Loading skeleton | Pulse animation on first SSE token wait (replace blinking cursor) |
| Session persistence | Save last N messages to `localStorage`; restore on reload |
| Process supervisor | `supervisord` or `systemd --user` so uvicorn survives server reboots |
| Log rotation | `logrotate` config for `fastapi.log` (currently unbounded) |
| Backend unit tests | `pytest` for `chat_service`, `upload_service`; mock Ollama via `FakeLLMClient` |
| Frontend tests | Vitest: `useChat.test.ts`, `MessageBubble.test.tsx`, `api.test.ts` |
| CI (GitHub Actions) | Run `pytest` + `npm test` on every push to `main` |

---

## 🔜 Phase 6 — Features

| Feature | Value |
|---------|-------|
| **Conversation history** | Sidebar list of past sessions, click to restore |
| **Stop streaming button** | Cancel mid-stream (`AbortController`) |
| **Model info tooltip** | Show param count / context window on hover over model name |
| **Markdown export** | Download conversation as `.md` file |
| **System prompt editor** | Let user override the system prompt per session |
| **File context persistence** | Keep uploaded dataframe in session so follow-up questions reference it |

---

## 🔜 Phase 7 — Access & Security

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
| Process mgmt | `nohup` + PID file | supervisord / systemd --user |
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
| 2026-03-30 | Streamlit kept on :8501 | Fallback until professor sign-off; retire in Phase 7 |
