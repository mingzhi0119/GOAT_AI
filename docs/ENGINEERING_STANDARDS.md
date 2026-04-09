# GOAT AI - Engineering Standards

> **Single source of truth for engineering rules in this repo.**  
> Repo root [`AGENTS.md`](../AGENTS.md) is a short durable index for automation; it must stay aligned with this file.  
> Last updated: 2026-04-08

---

## 0. Core Principles

1. **Fail fast, fail loud** - bad config or missing env vars must crash at startup with a clear message, not silently at runtime.
2. **Decouple by boundary** - HTTP handler -> service -> client. No business logic in route handlers. No I/O inside domain models.
3. **Portable by default** - code must run identically on `localhost:dev` and `A100:prod` without modification. No hardcoded paths, ports, or OS assumptions.
4. **Type everything** - untyped code is untestable code. Every function signature must carry types.
5. **Test the boundary, mock the world** - unit tests own pure logic; integration tests own real I/O; nothing else hits the network.

---

## 1. Python Standards

### 1.1 Type Annotations (mandatory)

Every function, method, and module-level variable must be fully annotated.

```python
# correct
def stream_chat(model: str, messages: list[ChatTurn]) -> Generator[str, None, None]: ...

# forbidden - missing return type, untyped list
def stream_chat(model, messages): ...
```

- Use `from __future__ import annotations` at the top of every file (deferred evaluation, avoids circular import issues).
- Use `TypeAlias` for complex repeated types.
- Use `Protocol` for injectable dependencies - never accept a concrete class when an interface suffices.
- Use `dataclass` or `pydantic.BaseModel` for all structured data; no bare `dict[str, Any]` crossing function boundaries.

```python
# Protocol for the LLM client - swappable without changing callers
class LLMClient(Protocol):
    def stream_chat(self, model: str, messages: list[ChatTurn]) -> Generator[str, None, None]: ...
```

### 1.2 Pydantic for All I/O Contracts

- **FastAPI request/response bodies**: always a `pydantic.BaseModel` subclass.
- **Environment configuration**: use the existing validated settings pattern for the repo. Today that is `goat_ai/config.py` (`@dataclass(frozen=True)` + `load_settings()`), but `BaseSettings` is acceptable for new isolated services if startup validation remains immediate.
- **Never** parse raw `request.json()` dicts inside route handlers.

```python
# example
class ChatRequest(BaseModel):
    model: str
    messages: list[ChatTurn]
    session_id: str = Field(default_factory=lambda: str(uuid4()))

@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    generate_timeout: int

def load_settings() -> Settings:
    return Settings(
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        generate_timeout=int(os.environ.get("OLLAMA_GENERATE_TIMEOUT", "120")),
    )
```

### 1.3 Error Handling

Layer-by-layer rule:

| Layer | Rule |
|-------|------|
| **Service / client** | Raise domain exceptions (`OllamaUnavailable`, `UploadTooLarge`). Never swallow. |
| **Route handler** | `try/except` domain exceptions -> return structured `HTTPException` with a user-safe message. Log the original. |
| **Startup** | Validate config; if invalid, raise `SystemExit` with a clear message. |
| **Background tasks** | Always `try/except Exception` at the task root; log with full traceback. |

```python
# service layer - raise, never swallow
def list_models(self) -> list[str]:
    try:
        resp = self._http.get(f"{self._base}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise OllamaUnavailable("Cannot reach Ollama") from exc
    return [m["name"] for m in resp.json().get("models", [])]

# handler layer - catch domain exception, return HTTP error
@router.get("/api/models")
async def get_models(llm: LLMClient = Depends(get_llm_client)) -> list[str]:
    try:
        return llm.list_models()
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable: %s", exc)
        raise HTTPException(status_code=503, detail="AI backend unavailable") from exc
```

### 1.4 Logging

- Use `logging.getLogger(__name__)` in every module - never `print()` in production code.
- Log at the correct level: `DEBUG` for verbose flow, `INFO` for lifecycle events, `WARNING` for recoverable problems, `ERROR`/`EXCEPTION` for failures.
- Never log secrets, file contents, or full user messages at level INFO or above.
- Configure once at entrypoint (`logging_config.py`); never call `basicConfig` inside a module.

### 1.5 Path Handling

```python
# always use pathlib - works on Linux (server) and Windows (dev)
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent.resolve()
STATIC_DIR = BASE_DIR / "frontend" / "dist"

# forbidden
STATIC_DIR = "/home/jupyter-mhu29@simon.roches-bde1e/GOAT_AI/frontend/dist"
STATIC_DIR = "C:\\Users\\simon\\GOAT_AI\\frontend\\dist"
```

### 1.6 Configuration (no magic values)

- Every tunable value lives in `Settings` (env var) or a named constant in config / the relevant module.
- Defaults must work on the A100 server out of the box.
- Port numbers, base URLs, timeouts, size limits - all env vars with documented defaults.

### 1.7 Module Structure (Python backend)

```
backend/
├── main.py              # App factory: create_app() -> FastAPI; mounts static, registers routers
├── config.py            # Settings wrapper; validated at startup/import boundary
├── types.py             # Re-exports `Settings` / `LLMClient` for router signatures (no direct `goat_ai` in routers)
├── dependencies.py      # FastAPI Depends() factories (get_llm_client, get_tabular_context_extractor, ...)
├── http_security.py       # API key + rate limit middleware
├── routers/
│   ├── chat.py          # POST /api/chat  (SSE streaming)
│   ├── models.py        # GET  /api/models
│   └── upload.py        # POST /api/upload
├── services/
│   ├── chat_service.py       # Public `stream_chat_sse` entry (thin wrapper)
│   ├── chat_stream_service.py # ChatStreamService: SSE + tools + safeguards
│   ├── chat_orchestration.py  # PromptComposer, ChartToolOrchestrator, SessionPersistenceService
│   ├── chat_runtime.py        # SessionRepository / ConversationLogger SQLite adapters (import `log_service`)
│   ├── tabular_context.py     # TabularContextExtractor Protocol + EmbeddedCsvTabularExtractor
│   └── upload_service.py
└── models/              # Pydantic request/response schemas (no business logic)
    ├── chat.py
    └── upload.py
```

### 1.8 Import layers (enforced)

- **Mechanical check:** from the repo root, run `lint-imports` (config: `pyproject.toml`). CI runs this before pytest.
- **Intent:** outer layers must not import inward-only modules (e.g. `goat_ai` never imports `backend`; `backend.services` must not import `backend.application` or `backend.routers`). Order is enforced in `pyproject.toml`: `main` -> `routers` -> `dependencies` -> `exception_handlers` -> **`application`** -> `services` -> `domain` -> `models` -> ... -> `goat_ai`. See [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) for the diagram and "current vs target" wiring.
- **Routers:** do not add direct `import goat_ai` / `from goat_ai` (use `backend.types` for shared type hints). `__tests__/test_router_direct_imports.py` also rejects direct `httpx` / `requests` / `pandas` / `openpyxl` in `backend/routers/`.
- **Domain -> HTTP:** `InferenceBackendUnavailable` (in `backend/services/exceptions.py`) is registered in `main` and maps to HTTP 503 for model listing endpoints; keep other routes using explicit `HTTPException` or the same pattern when you add more cross-cutting failures.

**Rules**:
- `routers/` only: validate input, call service, return response.
- **Never read `os.environ` inside request handlers** - use injected `Settings` / dependencies.
- `services/` only: orchestrate, no HTTP primitives.
- **Tabular context for charts**: resolve upload-embedded tables through injectable `TabularContextExtractor` (`tabular_context.py`), not ad hoc regex scattered in orchestration.
- **`log_service` imports:** under `backend/services/`, only `log_service.py` and `chat_runtime.py` may import `log_service` (enforced by `__tests__/test_architecture_boundaries.py`).
- `models/` only: data shapes, no methods beyond validators.
- `goat_ai/` (shared): LLM client, upload parsing, tools, **`chart_intent_v2`** (native tool intent models). No FastAPI imports and **no imports from `backend`** in the shared layer.
- **Chat wire:** optional `file_context: bool` on `ChatMessage` marks upload-derived tabular context; persistence uses versioned `file_context_prompt` + `chart_spec` fields (legacy content sniff remains as fallback for old clients).

### 1.9 Ports and persisted session JSON

- **Ports (injectable boundaries):** [PORTS.md](PORTS.md) - `SessionRepository`, `ConversationLogger`, `TitleGenerator`, `LLMClient`, telemetry hooks.
- **Session blob format:** [SESSION_SCHEMA.md](SESSION_SCHEMA.md) - `SESSION_PAYLOAD_VERSION`, `build_session_payload` / `decode_session_payload`, legacy list vs dict.

---

## 2. TypeScript / React Standards

### 2.1 TypeScript Configuration

`tsconfig.json` must include:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true
  }
}
```

- `strict: true` enables `strictNullChecks`, `noImplicitAny`, etc.
- **No `any`** - use `unknown` and narrow it, or define a proper type.
- **No `@ts-ignore`** - if you need it, fix the type.

### 2.2 API Types

Define a `src/api/types.ts` that mirrors every Pydantic model from the backend:

```typescript
// src/api/types.ts
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  model: string;
  messages: ChatTurn[];
  session_id?: string;
}

export interface ModelListResponse {
  models: string[];
}
```

All API call functions live in `src/api/` - never `fetch()` directly inside a component or hook.

```typescript
// src/api/chat.ts
export async function* streamChat(req: ChatRequest): AsyncGenerator<string> {
  const resp = await fetch("/api/chat", { method: "POST", body: JSON.stringify(req), ... });
  // parse SSE ...
}
```

### 2.3 Component Rules

- **One responsibility per component** - `ChatWindow` only renders messages; `useChat` manages state; `streamChat` handles network.
- **Props must be typed** - use `interface Props`, never `any`.
- **No business logic inside JSX** - extract to hooks or utils.
- **Error boundaries** - every async-boundary component must have an error boundary parent.

```typescript
// hook owns state, component owns rendering
function ChatWindow() {
  const { messages, sendMessage, isStreaming } = useChat();
  return <div>{ messages.map(m => <MessageBubble key={m.id} turn={m} />) }</div>;
}
```

### 2.4 Hooks

- Custom hooks (`use*.ts`) live in `src/hooks/`.
- Every hook returns a stable, typed object - not a tuple (unless exactly 2 items like `useState`).
- Hooks must not import from `src/components/` (no circular dependency).

### 2.5 Module Structure (React frontend)

```
frontend/src/
├── api/
│   ├── chat.ts          # fetch + SSE logic
│   ├── models.ts        # GET /api/models
│   ├── upload.ts        # POST /api/upload
│   └── types.ts         # All shared TS types mirroring backend Pydantic models
├── components/
│   ├── ChatWindow.tsx
│   ├── MessageBubble.tsx
│   ├── Sidebar.tsx
│   └── FileUpload.tsx
├── hooks/
│   ├── useChat.ts
│   ├── useModels.ts
│   └── useTheme.ts
├── utils/
│   └── markdown.ts      # markdown rendering helpers
├── styles/
│   ├── theme.css        # CSS variables for Light/Dark (--color-bg, --color-text, ...)
│   └── global.css
└── App.tsx
```

---

## 3. Testing Standards

### 3.1 Python (pytest)

**Canonical runner:** `python -m pytest __tests__/ -v` (matches CI). Prefer **pytest** for new tests (`pytest` markers, fixtures, plain functions). `python -m unittest discover -s __tests__ -p "test_*.py" -v` remains **legacy / optional** for older files not yet migrated.

**Minimum coverage targets**:

| Module | Target |
|--------|--------|
| `goat_ai/tools.py` | 100% |
| `goat_ai/uploads.py` | 90% |
| `goat_ai/ollama_client.py` | 80% (mocked HTTP) |
| `backend/services/` | 90% |
| `backend/routers/` | 80% (integration tests) |

**Structure**:
```
__tests__/
├── test_chat_service.py
├── test_upload_service.py
├── integration/         # pytest marker `integration` - app + SQLite paths (keep total CI time in budget)
└── ...                    # mock Ollama at Protocol boundary
```

**Rules**:
- Mock all I/O at the `Protocol` boundary - never hit real Ollama in unit tests.
- Use `pytest.fixture` or `unittest` setup helpers for shared state; avoid module-level globals in tests.
- Parametrize edge cases: empty message list, oversized upload, Ollama timeout.
- Prefer deterministic synchronization over `time.sleep()`.

```python
# inject a fake LLMClient - tests never need Ollama running
class FakeLLMClient:
    def list_models(self) -> list[str]:
        return ["llama3:latest"]
    def stream_chat(self, model: str, messages: list[ChatTurn]) -> Generator[str, None, None]:
        yield "Hello"
        yield " world"

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    return TestClient(app)
```

### 3.2 TypeScript (Vitest + React Testing Library)

**Structure**:
```
frontend/src/
└── __tests__/
    ├── useChat.test.ts       # hook tests with mock fetch
    ├── ChatWindow.test.tsx   # renders correct number of bubbles
    └── api.test.ts           # api/ functions with mocked fetch
```

**Rules**:
- Mock `fetch` with `vi.stubGlobal("fetch", ...)` - never hit the real server.
- Test hooks with `renderHook` from `@testing-library/react`.
- Assert on accessible roles/text, not on CSS classes or DOM structure.

### 3.3 CI (GitHub Actions)

```yaml
# .github/workflows/ci.yml
jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - uses: astral-sh/setup-uv@v8.0.0
        with:
          enable-cache: true
      - run: uv pip install --system -r requirements-ci.txt
      - run: python -m pytest __tests__/ -v --tb=short

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with: { node-version: "24.14.1" } # Keep CI aligned with `.nvmrc`
      - run: cd frontend && npm ci && npm test -- --run && npm run build
```

---

## 4. Cross-Environment Compatibility

### 4.1 The "Works Locally, Breaks on Server" Prevention Checklist

| Category | Rule | Example |
|----------|------|---------|
| **Paths** | `pathlib.Path`, never string concat | `Path(__file__).parent / "static"` |
| **Ports** | Env var with safe dev/prod defaults | `GOAT_SERVER_PORT=62606` for dev/prod parity behind the current single-port runtime-target policy |
| **Base URLs** | Env var, never `localhost` hardcoded | `OLLAMA_BASE_URL=http://127.0.0.1:11434` |
| **Node version** | Pin in `.nvmrc` and CI matrix | `24.14.1` |
| **Python version** | Keep runtime/docs/CI aligned | **CI backend uses Python `3.14`**. Regenerate `docs/openapi.json` with the **same** interpreter as CI (`python -m tools.regenerate_openapi_json`). Reference production venvs may remain `3.12.x` until operators upgrade; mismatched interpreters can make `app.openapi()` differ from the committed file. |
| **Dependencies** | Exact pins in `requirements.txt` | `fastapi==0.135.2` |
| **npm packages** | `package-lock.json` committed | `npm ci` in CI/deploy, never `npm install` |
| **File encoding** | Always `encoding="utf-8"` on `open()` | `open(path, encoding="utf-8")` |
| **Line endings** | `.gitattributes`: `* text=auto eol=lf` | Prevents CRLF issues on Windows dev |
| **Temp files** | `tempfile.mkdtemp()` / `tmp_path` fixture | Never `/tmp/hardcoded` |
| **Process startup** | Validate all required env vars at startup | Crash with message, not at first request |
| **Static files** | Build React before deploy; serve from FastAPI | `npm run build` in `deploy.sh` |
| **Secrets** | `.env` in `.gitignore`; `.env.example` committed | Never `export SECRET=abc` in a script |

### 4.2 Startup Validation Pattern

```python
# backend/config.py - fail at import, not at first request
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = load_settings()
    if not settings.ollama_base_url.startswith(("http://", "https://")):
        raise SystemExit(
            f"[GOAT AI] Invalid configuration: OLLAMA_BASE_URL must start with http(s)://; "
            f"got {settings.ollama_base_url!r}"
        )
    return settings
```

### 4.3 React Build + Serve Pattern

FastAPI serves the compiled React bundle - zero separate Node process in production:

```python
# backend/main.py
from fastapi.staticfiles import StaticFiles
from pathlib import Path

DIST = Path(__file__).parent.parent / "frontend" / "dist"

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api")
    app.include_router(models_router, prefix="/api")
    if DIST.is_dir():
        app.mount("/", StaticFiles(directory=DIST, html=True), name="spa")
    else:
        # dev mode: React dev server runs separately on :3000
        pass
    return app
```

`deploy.sh` must run `npm run build` before starting uvicorn; CI must fail if `dist/` is absent.

---

## 5. API Design Rules

- **SSE for streaming**, not WebSocket - simpler, works through more proxies, native `EventSource` in browser.
- **Charts:** backend compiles `ChartIntentV2` -> `ChartSpecV2` / ECharts options; models must not emit raw chart-library JSON. If the model does not report native tool support, keep chart rendering **disabled** (no pseudo chart markup fallback).
- Every endpoint returns a typed Pydantic response model - never `dict` or `Response(content=...)` unless it's a stream.
- Use `Depends()` for all cross-cutting concerns (auth, settings, LLM client) - no global state.
- Prefix all API routes with `/api/` - frontend SPA handles everything else.
- HTTP status codes: `200` success, `400` bad input, `422` validation, `503` backend unavailable, `500` unexpected.
- Never expose internal error messages to the client - log them, return a sanitized string.

---

## 6. Dependency Management

### Python

```
# requirements.txt - exact pins, grouped
# Web framework
fastapi==0.135.2
uvicorn[standard]==0.35.0
python-multipart==0.0.20

# Data
pandas==2.2.3
openpyxl==3.1.5

# HTTP client
requests==2.32.3

# Validation / config
pydantic==2.x.x

# Testing
pytest==8.x
httpx==0.x           # FastAPI TestClient support
```

- Keep `requirements.txt` as the runtime install source of truth for deploy; CI and full local dev use `requirements-ci.txt` (`-r requirements.txt` plus lint/test/audit pins).
- Run `uv pip install --system -r requirements-ci.txt` in CI (after `astral-sh/setup-uv`) - never `pip install package` ad-hoc.

### Node / npm

- Commit `package-lock.json`.
- Use `npm ci` in CI and deploy - never `npm install` (which can change the lock).
- Add `.nvmrc` with content `24.14.1` so `nvm use` picks the right version automatically.
- Dev dependencies in `devDependencies`; runtime dependencies in `dependencies`.

---

## 7. Git & Review Checklist

Before every commit ask:

- [ ] All new functions have type annotations and a one-line docstring.
- [ ] No `print()`, `TODO`, or commented-out code left in.
- [ ] New logic has a corresponding test (at least a happy-path unit test).
- [ ] No hardcoded paths, ports, secrets, or usernames.
- [ ] `requirements.txt` / `requirements-ci.txt` / `package-lock.json` updated if dependencies changed.
- [ ] The change runs with `python -m pytest __tests__/ -v` green and `npm test -- --run` green.
- [ ] `OPERATIONS.md` updated if a new env var or startup step was added.

---

## 8. API contract workflow (prefer contracts over source spelunking)

- Treat the API surface as a **black-box contract** first, not a source-reading exercise.
- For existing APIs, prefer these artifacts before opening implementation files:
  - `__tests__/test_api_blackbox_contract.py`
  - `__tests__/test_api_auth.py`
  - `__tests__/test_api_security.py`
  - `docs/openapi.json`
  - `docs/api.llm.yaml`
- Open implementation only when changing behavior, when contract tests/docs disagree with runtime, or when debugging needs details not visible from the contract layer.

---

## 9. Project snapshot (environment targets)

| Item | Value |
|------|--------|
| Repo | `GOAT_AI` |
| Supported environments | **Windows, macOS, Linux** for development; Linux or containerized hosts for production-**not** limited to one campus image (see `README.md` **Environments**) |
| Example reference deployment | Unprivileged shared Linux with GPU (e.g. A100) + Ollama + reverse proxy-one real ops profile, not a global requirement |
| App shape | FastAPI backend serving a React SPA |
| Default bind port | `62606` (`GOAT_SERVER_PORT`; override per environment) |
| Frontend build | Vite |
| Frontend runtime (server/CI) | Node 24 (see `.nvmrc`) |
| Backend runtime | Python **3.14** in CI and recommended local venv for contract checks; **3.12.x** still typical on some production hosts |

---

## 10. Production host and deploy constraints

- The bullets below describe **a common production profile** (shared, **no root**, no control of system nginx). **Other** deployments (full VM, Docker Compose, Kubernetes, rootful single-tenant) may differ; behavior must remain **env-driven**, not hardcoded to one school host.
- Shared / JupyterHub-style environment: **no `sudo`**, no assumed system-wide `systemctl`, nginx reloads, or `/etc/*` edits.
- `systemctl --user` may work but can fail over SSH; keep **`nohup` + `logs/fastapi.pid`** as a permanent fallback.
- Uvicorn on `0.0.0.0:62606` is valid for this user.
- Prefer `GOAT_GPU_UUID` for the A100; do not silently bind to the wrong GPU (e.g. GT 1030).
- Develop/deploy from the **current checkout** by default; `deploy.sh` must not assume `git pull` / `git reset --hard` unless **`SYNC_GIT=1`** (explicit opt-in).
- Runtime target resolution: `GOAT_DEPLOY_TARGET=auto` prefers `GOAT_SERVER_PORT` (default `62606`) and falls back to `GOAT_LOCAL_PORT` only when the server port cannot be used; keep **`GET /api/system/runtime-target`** aligned with scripts.

---

## 11. Theme (frontend)

- Light/dark mode uses a `.dark` class on `<html>`.
- Theme state persists in `localStorage`.
- Global theme tokens live in `frontend/src/styles/global.css`.

---

## 12. Documentation update rules

- **Language** - All prose in **`docs/`** and **`README.md`** must be **English**. Do not commit Chinese or other non-English text in those paths.
- **Encoding** - Keep prose UTF-8 and ASCII-safe where practical. Avoid mojibake, replacement characters, and other glyphs that do not render cleanly in shell logs or CI output. The repo root `.editorconfig` must declare `charset = utf-8` so editors do not reintroduce BOM headers.
- **RAG quality (Section 14.7)** - Changes to retrieval/rerank/rewrite logic or `evaldata/rag_eval_cases.jsonl` must keep `python -m tools.run_rag_eval` green; document golden-set updates in `evaldata/README.md` / `evaldata/VERSION`. Operational knobs: [OPERATIONS.md](OPERATIONS.md) **RAG retrieval quality**.

When behavior changes, update:

- `docs/DOMAIN.md` - ubiquitous terms and user-visible semantics (Phase 15.1); required when chat/chart/safeguard meaning changes
- `docs/SESSION_SCHEMA.md` - when `SESSION_PAYLOAD_VERSION` or persisted session JSON shape changes
- `docs/PORTS.md` / `docs/DEPENDENCY_GRAPH.md` - when injectable ports or layer import rules change
- `README.md` - architecture, structure, or developer workflow
- `docs/openapi.json` - committed OpenAPI from FastAPI (`backend.main:app`)
- `docs/api.llm.yaml` - regenerate via `python -m tools.generate_llm_api_yaml` (from repository root)
- `docs/API_REFERENCE.md` - human-readable endpoint reference
- `docs/OPERATIONS.md` - env vars, deploy, startup, host operations
- `docs/PROJECT_STATUS.md` - current shipped state
- `docs/ROADMAP.md` - phase completion and future work
- Optional / capability-gated features - follow **Section 15**; update **`.env.example`** and **`docs/OPERATIONS.md`** for new `GOAT_*` flags

---

## 13. API contract artifacts

- Canonical machine-readable contract: **`docs/openapi.json`** (OpenAPI **3.2.0**), regenerated when endpoints/schemas change.
- Canonical LLM-facing compact contract: **`docs/api.llm.yaml`** (generated, not hand-maintained except via generator changes).
- Canonical **executable** contract: black-box suites under `__tests__/`, especially `test_api_blackbox_contract.py`.

---

## 14. Recovery and commit hygiene

- If work appears lost, check **`git reflog`** before assuming it is gone.
- Be careful with **`git reset --hard`** when development happens on the shared host.
- Do not commit `.venv/`, PID files, SQLite runtime files, notebook checkpoints, or other machine-local artifacts.
- Before committing: no `print()` in production paths, no commented-out code, no hardcoded secrets/ports/paths; new functions typed; tests where practical; dependency locks updated when deps change.

---

## 15. Feature enable/disable and gating (industrial pattern)

Industrial-grade **feature on/off (including authorization and runtime capability gating)** must be **layered**; hiding buttons in the frontend alone is not sufficient.

### 15.1 Two kinds of gates (do not conflate)

| Kind | Meaning | Typical inputs | How to model in the API |
|------|---------|----------------|-------------------------|
| **Authorization / policy** | Whether **this user, role, or tenant** is **allowed** to use the feature | API key scope, session ownership, RBAC | `{ policy_allowed, deny_reason }`; denial tends toward **403** |
| **Capability / runtime** | Whether **deployment policy, Docker, GPU, sandbox, external deps** are **ready right now** | `GOAT_*`, socket probes, `/api/ready`-style checks | `{ effective_enabled, deny_reason }`; denial tends toward **503** |

Both can look like **`{ enabled, reason }`, but the semantics differ**: Docker socket probes and operator kill-switches are **runtime / feature availability**, not the same meaning as **"permission"** in the AuthZ sense. This repo’s AuthZ roadmap is in `docs/ROADMAP.md` Phase 15; **readiness** and **`/api/ready`** have their own semantics-do not mix them with feature gates in documentation.

### 15.2 HTTP semantics and stable `code` (avoid implementation drift)

- **`403 Forbidden`** - The **caller is not authorized** to use this feature (policy / AuthZ denial).
- **`503 Service Unavailable`** - The feature is **not available on this deployment/runtime**, or a **dependency is not ready** (runtime / capability / operator-disabled capability that applies to the whole deployment).
- **`422` / `409`** - Use only in the **few** cases where the request is **well-formed but conflicts with current **feature state**; do **not** overuse them.
- Stay consistent with global readiness: behaviors such as **`/api/ready`** when a global dependency is down remain **503** per existing rules.

Routes must **translate** the service’s gate decision into the HTTP semantics and **`code`** above (see `docs/API_ERRORS.md`), e.g. **`FEATURE_DISABLED`** (403) vs **`FEATURE_UNAVAILABLE`** (503).

### 15.3 `deny_reason` (controlled enum, safe for clients)

- **`deny_reason` must be a stable, documentable, enumerable public value**; logs may carry richer internal context, but the **API must not echo raw exception strings**.
- Client-facing **`detail`** should use **fixed short phrases** mapped server-side from `deny_reason` + gate kind, not stacks or internal diagnostics in JSON.

### 15.4 Five layers (not frontend-only)

1. **Configuration (startup)** - Express whether the **deployment policy allows** the feature via `GOAT_*` and related env vars; **fail fast** in `load_settings()` on contradictory combinations (e.g. sandbox enabled in config but required paths missing when you enforce strict validation).
2. **Runtime probing** - At startup or first use, probe Docker socket / runtime dependencies for **actual availability**, producing **`effective_enabled`** and an **enumerated `deny_reason`**; do not return raw exception strings to clients.
3. **Three enforcement layers**
   - **Service** - **Single place** to validate before any side effect (spawn process, disk, outbound network); this is the **primary enforcement** point.
   - **Route** - Map gate decisions to stable HTTP semantics and **`code`**. **Not authorized -> 403**; **dependency not ready / feature unavailable on this deployment -> 503**.
   - **Frontend** - Consumes public **capability / feature** payloads for UI only; this is **UX**, **not** a security boundary.
4. **API contract** - Expose stable shapes via **`GET /api/system/features`** (or equivalent); schema changes must stay in sync with **OpenAPI** and the **black-box contract**.
5. **Observability and tests** - Add metrics such as `feature_gate_denials_total{feature,reason}`; cover contradictory config, missing deps, policy denial, and closed-feature status codes in a **test matrix**, with black-box assertions.

### 15.5 Documentation and operations

- Document each **`GOAT_*` flag in **`.env.example`** and **`docs/OPERATIONS.md`**, including whether it is **runtime vs policy** when that distinction matters.

