# GOAT AI — Engineering Standards

> **This document is the authoritative reference for all code written in this project.**  
> Every AI assistant, contributor, or reviewer must follow these standards.  
> Last updated: 2026-03-30

---

## 0. Core Principles

1. **Fail fast, fail loud** — bad config or missing env vars must crash at startup with a clear message, not silently at runtime.
2. **Decouple by boundary** — HTTP handler → service → client. No business logic in route handlers. No I/O inside domain models.
3. **Portable by default** — code must run identically on `localhost:dev` and `A100:prod` without modification. No hardcoded paths, ports, or OS assumptions.
4. **Type everything** — untyped code is untestable code. Every function signature must carry types.
5. **Test the boundary, mock the world** — unit tests own pure logic; integration tests own real I/O; nothing else hits the network.

---

## 1. Python Standards

### 1.1 Type Annotations (mandatory)

Every function, method, and module-level variable must be fully annotated.

```python
# ✅ correct
def stream_chat(model: str, messages: list[ChatTurn]) -> Generator[str, None, None]: ...

# ❌ forbidden — missing return type, untyped list
def stream_chat(model, messages): ...
```

- Use `from __future__ import annotations` at the top of every file (deferred evaluation, avoids circular import issues).
- Use `TypeAlias` for complex repeated types.
- Use `Protocol` for injectable dependencies — never accept a concrete class when an interface suffices.
- Use `dataclass` or `pydantic.BaseModel` for all structured data; no bare `dict[str, Any]` crossing function boundaries.

```python
# ✅ Protocol for the LLM client — swappable without changing callers
class LLMClient(Protocol):
    def stream_chat(self, model: str, messages: list[ChatTurn]) -> Generator[str, None, None]: ...
```

### 1.2 Pydantic for All I/O Contracts

- **FastAPI request/response bodies**: always a `pydantic.BaseModel` subclass.
- **Environment configuration**: always a `pydantic_settings.BaseSettings` subclass — validation runs at import time.
- **Never** parse raw `request.json()` dicts inside route handlers.

```python
# ✅
class ChatRequest(BaseModel):
    model: str
    messages: list[ChatTurn]
    session_id: str = Field(default_factory=lambda: str(uuid4()))

class Settings(BaseSettings):
    ollama_base_url: str = "http://127.0.0.1:11434"
    generate_timeout: int = 120

    model_config = SettingsConfigDict(env_prefix="GOAT_", env_file=".env", extra="ignore")
```

### 1.3 Error Handling

Layer-by-layer rule:

| Layer | Rule |
|-------|------|
| **Service / client** | Raise domain exceptions (`OllamaUnavailable`, `UploadTooLarge`). Never swallow. |
| **Route handler** | `try/except` domain exceptions → return structured `HTTPException` with a user-safe message. Log the original. |
| **Startup** | Validate config; if invalid, raise `SystemExit` with a clear message. |
| **Background tasks** | Always `try/except Exception` at the task root; log with full traceback. |

```python
# ✅ service layer — raise, never swallow
def list_models(self) -> list[str]:
    try:
        resp = self._http.get(f"{self._base}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise OllamaUnavailable("Cannot reach Ollama") from exc
    return [m["name"] for m in resp.json().get("models", [])]

# ✅ handler layer — catch domain exception, return HTTP error
@router.get("/api/models")
async def get_models(llm: LLMClient = Depends(get_llm_client)) -> list[str]:
    try:
        return llm.list_models()
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable: %s", exc)
        raise HTTPException(status_code=503, detail="AI backend unavailable") from exc
```

### 1.4 Logging

- Use `logging.getLogger(__name__)` in every module — never `print()` in production code.
- Log at the correct level: `DEBUG` for verbose flow, `INFO` for lifecycle events, `WARNING` for recoverable problems, `ERROR`/`EXCEPTION` for failures.
- Never log secrets, file contents, or full user messages at level INFO or above.
- Configure once at entrypoint (`logging_config.py`); never call `basicConfig` inside a module.

### 1.5 Path Handling

```python
# ✅ always use pathlib — works on Linux (server) and Windows (dev)
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent.resolve()
STATIC_DIR = BASE_DIR / "frontend" / "dist"

# ❌ forbidden
STATIC_DIR = "/home/jupyter-mhu29@simon.roches-bde1e/GOAT_AI/frontend/dist"
STATIC_DIR = "C:\\Users\\simon\\GOAT_AI\\frontend\\dist"
```

### 1.6 Configuration (no magic values)

- Every tunable value lives in `Settings` (env var) or a named constant in config / the relevant module.
- Defaults must work on the A100 server out of the box.
- Port numbers, base URLs, timeouts, size limits — all env vars with documented defaults.

### 1.7 Module Structure (Python backend)

```
backend/
├── main.py              # App factory: create_app() → FastAPI; mounts static, registers routers
├── config.py            # Settings (BaseSettings); validated at import
├── dependencies.py      # FastAPI Depends() factories (get_llm_client, get_settings, ...)
├── exceptions.py        # Domain exception hierarchy
├── routers/
│   ├── chat.py          # POST /api/chat  (SSE streaming)
│   ├── models.py        # GET  /api/models
│   └── upload.py        # POST /api/upload
├── services/
│   ├── chat_service.py  # Orchestrates LLMClient + session; pure business logic
│   └── upload_service.py
└── models/              # Pydantic request/response schemas (no business logic)
    ├── chat.py
    └── upload.py
```

**Rules**:
- `routers/` only: validate input, call service, return response.
- `services/` only: orchestrate, no HTTP primitives.
- `models/` only: data shapes, no methods beyond validators.
- `goat_ai/` (shared): LLM client, upload parsing, tools. No FastAPI imports in the shared layer.

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
- **No `any`** — use `unknown` and narrow it, or define a proper type.
- **No `@ts-ignore`** — if you need it, fix the type.

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

All API call functions live in `src/api/` — never `fetch()` directly inside a component or hook.

```typescript
// src/api/chat.ts
export async function* streamChat(req: ChatRequest): AsyncGenerator<string> {
  const resp = await fetch("/api/chat", { method: "POST", body: JSON.stringify(req), ... });
  // parse SSE ...
}
```

### 2.3 Component Rules

- **One responsibility per component** — `ChatWindow` only renders messages; `useChat` manages state; `streamChat` handles network.
- **Props must be typed** — use `interface Props`, never `any`.
- **No business logic inside JSX** — extract to hooks or utils.
- **Error boundaries** — every async-boundary component must have an error boundary parent.

```typescript
// ✅ hook owns state, component owns rendering
function ChatWindow() {
  const { messages, sendMessage, isStreaming } = useChat();
  return <div>{ messages.map(m => <MessageBubble key={m.id} turn={m} />) }</div>;
}
```

### 2.4 Hooks

- Custom hooks (`use*.ts`) live in `src/hooks/`.
- Every hook returns a stable, typed object — not a tuple (unless exactly 2 items like `useState`).
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
tests/
├── conftest.py          # shared fixtures: mock LLMClient, sample DataFrames, tmp settings
├── unit/
│   ├── test_tools.py
│   ├── test_uploads.py
│   └── test_chat_service.py
└── integration/
    └── test_api.py      # uses FastAPI TestClient, mocks OllamaService via DI
```

**Rules**:
- Mock all I/O at the `Protocol` boundary — never hit real Ollama in unit tests.
- Use `pytest.fixture` for shared setup; avoid module-level globals in tests.
- Parametrize edge cases: empty message list, oversized upload, Ollama timeout.
- Never use `time.sleep()` in tests — use `pytest-asyncio` and async fixtures.

```python
# ✅ inject a fake LLMClient — tests never need Ollama running
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
- Mock `fetch` with `vi.stubGlobal("fetch", ...)` — never hit the real server.
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
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt pytest pytest-asyncio httpx
      - run: pytest tests/ -v --tb=short

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with: { node-version: "18" }      # match server exactly
      - run: cd frontend && npm ci && npm test -- --run
```

---

## 4. Cross-Environment Compatibility

### 4.1 The "Works Locally, Breaks on Server" Prevention Checklist

| Category | Rule | Example |
|----------|------|---------|
| **Paths** | `pathlib.Path`, never string concat | `Path(__file__).parent / "static"` |
| **Ports** | Env var with server-safe default | `PORT=8002` |
| **Base URLs** | Env var, never `localhost` hardcoded | `OLLAMA_BASE_URL=http://127.0.0.1:11434` |
| **Node version** | Pin in `.nvmrc` and CI matrix | `18.19.1` |
| **Python version** | Pin in `pyproject.toml` `requires-python` | `>=3.12` |
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
# backend/config.py — fail at import, not at first request
class Settings(BaseSettings):
    ollama_base_url: str
    port: int = 8002

    @field_validator("ollama_base_url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"GOAT_OLLAMA_BASE_URL must start with http(s)://; got: {v!r}")
        return v

# Instantiated at module level — crashes immediately if misconfigured
settings = Settings()
```

### 4.3 React Build + Serve Pattern

FastAPI serves the compiled React bundle — zero separate Node process in production:

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

- **SSE for streaming**, not WebSocket — simpler, works through more proxies, native `EventSource` in browser.
- Every endpoint returns a typed Pydantic response model — never `dict` or `Response(content=...)` unless it's a stream.
- Use `Depends()` for all cross-cutting concerns (auth, settings, LLM client) — no global state.
- Prefix all API routes with `/api/` — frontend SPA handles everything else.
- HTTP status codes: `200` success, `400` bad input, `422` validation, `503` backend unavailable, `500` unexpected.
- Never expose internal error messages to the client — log them, return a sanitized string.

---

## 6. Dependency Management

### Python

```
# requirements.txt — exact pins, grouped
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
pydantic-settings==2.x.x

# Testing (separate file: requirements-dev.txt)
pytest==8.x
pytest-asyncio==0.x
httpx==0.x           # FastAPI TestClient async support
```

- Use `pip-compile` (pip-tools) to generate locked files from `requirements.in`.
- `requirements.txt` is the **installed** lock; `requirements.in` is the **intent**.
- Run `pip install -r requirements.txt` in CI — never `pip install package` ad-hoc.

### Node / npm

- Commit `package-lock.json`.
- Use `npm ci` in CI and deploy — never `npm install` (which can change the lock).
- Add `.nvmrc` with content `18.19.1` so `nvm use` picks the right version automatically.
- Dev dependencies in `devDependencies`; runtime dependencies in `dependencies`.

---

## 7. Git & Review Checklist

Before every commit ask:

- [ ] All new functions have type annotations and a one-line docstring.
- [ ] No `print()`, `TODO`, or commented-out code left in.
- [ ] New logic has a corresponding test (at least a happy-path unit test).
- [ ] No hardcoded paths, ports, secrets, or usernames.
- [ ] `requirements.txt` / `package-lock.json` updated if dependencies changed.
- [ ] The change runs with `pytest` green and `npm test -- --run` green.
- [ ] `OPERATIONS.md` updated if a new env var or startup step was added.
