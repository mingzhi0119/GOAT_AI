# GOAT AI School Ubuntu Demo Readiness / 学校 Ubuntu 演示就绪审计

Date: 2026-04-30 demo prep  
Target: School Ubuntu profile, `GOAT_DEPLOY_MODE=1`, `goat-ai.school-ubuntu`, `ollama-local` on `127.0.0.1:11435`

## Executive Verdict / 总体结论

**中文：** 当前学校 Ubuntu 部署路径有清晰的专用入口和运行时设计。本轮 P0/P1 修复后，Serper 默认搜索在缺少 `SERPER_API_KEY` 或 Serper 运行期不可用时会自动退回 DuckDuckGo；school deploy wrapper 的 nohup fallback 也会加载 `.env` 与 `.env.school-ubuntu`；根目录误放的 `deploy.ps1` 已移除，保留 `ops/deploy/deploy.ps1` 作为唯一 Windows 部署入口。

**English:** The school Ubuntu path has a dedicated deployment shape and a coherent runtime design. After the P0/P1 remediation, default Serper search falls back to DuckDuckGo when `SERPER_API_KEY` is absent or Serper is unavailable; the school deploy wrapper's nohup fallback loads both `.env` and `.env.school-ubuntu`; and the accidental root-level `deploy.ps1` has been removed so `ops/deploy/deploy.ps1` remains the only supported Windows deploy entrypoint.

Recommended demo posture:

- Prefer the **systemd path**: `goat-ai.school-ubuntu`.
- Put school-only values in `.env.school-ubuntu`.
- Configure Serper explicitly if you want Google-backed results; otherwise the default path will use DuckDuckGo fallback.
- Deploy from a known clean commit/branch, not an ambiguous local dirty tree.
- Run `python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606` after deploy.

## Evidence Snapshot / 审计证据快照

### Passing checks / 已通过检查

| Check | Result | Meaning |
| --- | --- | --- |
| `python -m tools.contracts.check_api_contract_sync` | PASS | API contract artifacts are in sync. |
| WSL `bash -n` for school deploy/build/Ollama scripts | PASS | Linux shell syntax is valid for the inspected scripts. |

WSL syntax command used:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command 'bash -n ops/deploy/deploy_school_server.sh ops/deploy/lib/backend_server_deploy.sh ops/build/build_school_server.sh ops/build/lib/project_build.sh scripts/ollama/start_ollama_local.sh'
```

### Previously red checks / 之前红灯

The planned pytest slice failed:

```text
python -m pytest __tests__/backend/platform/test_dotenv_config.py __tests__/backend/platform/test_local_ollama_config.py __tests__/ops/test_ops_asset_contracts.py __tests__/ops/test_post_deploy_check.py -q

Result: 46 passed, 2 failed
```

Original failures:

1. `test_explicit_env_override_wins_over_school_default` failed because `load_settings()` defaulted `GOAT_WORKBENCH_WEB_PROVIDER` to `serper` and raised when `SERPER_API_KEY` was missing.
2. `test_root_entrypoints_are_not_part_of_the_supported_ops_surface` failed because an untracked root-level `deploy.ps1` existed. The supported deploy wrappers live under `ops/deploy/`.

Remediation status: settings no longer fail startup for missing Serper keys, Serper search falls back to DuckDuckGo at provider runtime, and the root-level `deploy.ps1` has been removed.

## Risk Register / 风险登记

### P0 - Serper default startup blocker mitigated by DuckDuckGo fallback

**中文：** `GOAT_WORKBENCH_WEB_PROVIDER=serper` 仍是默认值，但缺少 `SERPER_API_KEY` 不再阻断后端启动。搜索 provider 会先尝试 Serper；如果缺 key、超时、HTTP/429、请求异常或 malformed response，则自动调用 DuckDuckGo。只有 Serper 与 DuckDuckGo 都失败时，才向用户返回 search unavailable。

**English:** `GOAT_WORKBENCH_WEB_PROVIDER=serper` remains the default, but missing `SERPER_API_KEY` no longer blocks backend startup. The provider tries Serper first, then automatically calls DuckDuckGo on missing key, timeout, HTTP/429, request error, or malformed response. Search is reported unavailable only when both providers fail.

Evidence:

- `goat_ai/config/settings.py:330` defaults `workbench_web_provider` to `serper`.
- `goat_ai/config/settings.py:565` reads `GOAT_WORKBENCH_WEB_PROVIDER` with default `serper`.
- `goat_ai/config/settings.py:579` reads `SERPER_API_KEY`.
- `goat_ai/search/providers.py` now performs Serper-to-DuckDuckGo fallback and records actual provider metadata on normalized hits.
- `goat_ai/config/settings.py` no longer raises when default `serper` mode has an empty `SERPER_API_KEY`.

Demo-safe mitigation:

```dotenv
# Preferred if you want Google-backed demo search:
SERPER_API_KEY=your_serper_api_key_here

# Still valid without a key; default serper mode falls back to DuckDuckGo.

# If you do not need web search tomorrow:
GOAT_WORKBENCH_WEB_PROVIDER=disabled

# If you want explicit DuckDuckGo-only mode:
GOAT_WORKBENCH_WEB_PROVIDER=duckduckgo
```

Recommendation: for tomorrow, put a verified `SERPER_API_KEY` in `.env.school-ubuntu` if you want Serper-backed Google results. If no key is available, leave the default provider and demo the DuckDuckGo fallback, or set `GOAT_WORKBENCH_WEB_PROVIDER=disabled` only when you want web search fully off.

### P1 - `.env.school-ubuntu` nohup fallback env inheritance fixed

**中文：** systemd unit 继续读取 `.env` 和 `.env.school-ubuntu`。本轮修复后，`ops/deploy/deploy_school_server.sh` 在调用部署公共库后也会 source/export `.env` 与 `.env.school-ubuntu`，因此 systemd restart 失败并落到 nohup fallback 时，`SERPER_API_KEY`、`GOAT_WORKBENCH_WEB_PROVIDER`、Ollama 配置等学校专用 env 会进入后端进程。

**English:** The systemd unit still reads both `.env` and `.env.school-ubuntu`. After this fix, `ops/deploy/deploy_school_server.sh` also sources/exports both files after loading the shared deploy library, so `SERPER_API_KEY`, `GOAT_WORKBENCH_WEB_PROVIDER`, Ollama settings, and other school-specific values reach the backend when deployment falls back to nohup.

Evidence:

- `ops/systemd/goat-ai.school-ubuntu.service:24-25` reads both `.env` and `.env.school-ubuntu`.
- `ops/deploy/deploy_school_server.sh` calls `source_dotenv_if_present "${PRIMARY_DOTENV_PATH}"` and `source_dotenv_if_present "${SCHOOL_DOTENV_PATH}"`.
- `goat_ai/config/settings.py:404` auto-loads only `APP_ROOT/.env`.
- `ops/deploy/lib/backend_server_deploy.sh:303` can fall back from systemd to nohup.
- `ops/deploy/lib/backend_server_deploy.sh` now owns the reusable `source_dotenv_if_present` helper.

Demo-safe mitigation:

- Use and verify `systemctl --user restart goat-ai.school-ubuntu` where available.
- If deploy reports it fell back to nohup, rerun `python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606` before presenting.
- Keep school-only overrides in `.env.school-ubuntu`; duplicating Serper/Ollama values into `.env` is no longer required for the deploy wrapper fallback.

### P1 - Current local worktree is not a clean deployment source

**中文：** 当前本地工作区仍包含待提交的 Serper/search/chat/workbench 修复改动。学校部署如果使用 `SYNC_GIT=1` 会从远端 ref 拉取，可能不包含本地修复；如果使用当前本地 checkout，又会带入未提交状态。根目录 `deploy.ps1` 已移除，部署入口应继续只使用 `ops/deploy/` 下的脚本。

**English:** The local checkout still contains pending Serper/search/chat/workbench remediation changes. Deploying with `SYNC_GIT=1` may omit those local fixes, while deploying the local tree includes uncommitted state. The root-level `deploy.ps1` has been removed; deploy entrypoints should remain under `ops/deploy/`.

Evidence:

- `git status --short` shows modified Serper/search/chat/workbench files and untracked `goat_ai/search/`.
- `__tests__/ops/test_ops_asset_contracts.py:16-19` asserts root-level deploy entrypoints must not exist.

Demo-safe mitigation:

- Before school deploy, decide one source of truth:
  - commit/push the intended Serper/search changes and deploy that exact ref, or
  - deploy current remote `main` and do not assume local-only Serper behavior exists on the server.
- Keep root-level `deploy.ps1` out of the committed deployment surface; use `ops/deploy/deploy.ps1` on Windows.
- Record the deployed commit:

```bash
git rev-parse HEAD
git status --short
```

### P2 - Ollama status helper uses `OLLAMA_HOST`, while config docs use `OLLAMA_BASE_URL`

**中文：** 学校默认端口都是 `11435`，所以默认情况下没有问题。但如果明天临时改了 Ollama URL，`scripts/ollama/status_ollama_local.sh` 读取的是 `OLLAMA_HOST`，不是 `OLLAMA_BASE_URL`。自定义 URL 时需要显式传入 `OLLAMA_HOST`。

**English:** The default `11435` path is fine. If the Ollama URL is customized, pass it through `OLLAMA_HOST` for the status helper.

Demo-safe command:

```bash
OLLAMA_HOST=http://127.0.0.1:11435 bash scripts/ollama/status_ollama_local.sh
```

## Pre-Demo Checklist / 明天演示前检查清单

Run these on the school server from `~/GOAT_AI`.

### 1. Confirm env / 确认环境变量

```bash
grep -E '^(SERPER_API_KEY|GOAT_WORKBENCH_WEB_PROVIDER|GOAT_USE_SCHOOL_OLLAMA_LOCAL|GOAT_OLLAMA_PROFILE|OLLAMA_BASE_URL|GOAT_DEPLOY_MODE)=' .env .env.school-ubuntu
```

Expected:

```dotenv
GOAT_USE_SCHOOL_OLLAMA_LOCAL=1
GOAT_OLLAMA_PROFILE=school-ubuntu
OLLAMA_BASE_URL=http://127.0.0.1:11435
```

And either:

```dotenv
SERPER_API_KEY=...
```

or:

```dotenv
GOAT_WORKBENCH_WEB_PROVIDER=disabled
```

### 2. Confirm local Ollama / 确认学校本地 Ollama

```bash
OLLAMA_HOST=http://127.0.0.1:11435 bash scripts/ollama/status_ollama_local.sh
```

If the model needed for the demo is missing:

```bash
bash scripts/ollama/ollama_local.sh pull <model>
```

### 3. Build / 构建

```bash
bash ops/build/build_school_server.sh
```

This path sources `.env` and `.env.school-ubuntu`, then validates settings.

### 4. Deploy / 部署

```bash
bash ops/deploy/deploy_school_server.sh
```

Preferred runtime:

```bash
systemctl --user status goat-ai.school-ubuntu --no-pager
```

If deploy says it fell back to nohup, treat that as a warning and rerun the post-deploy check before presenting.

### 5. Post-deploy proof / 部署后证明

```bash
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

Manual probes:

```bash
curl -sS http://127.0.0.1:62606/api/health
curl -sS http://127.0.0.1:62606/api/ready
curl -sS http://127.0.0.1:62606/api/system/runtime-target
curl -sS http://127.0.0.1:62606/api/system/metrics | head
```

## Demo Highlights / 可演示项目亮点

### 1. School-local AI runtime / 学校本地 AI 运行时

**中文讲法：** “这个项目不是只调用云 API 的薄壳。学校环境使用本地 Ollama runtime，配置上和本机、远程部署隔离，可以在学校机器上运行自己的模型。”

**English talk track:** “This is not just a thin cloud API wrapper. The school deployment uses a local Ollama runtime with a dedicated deployment profile and isolated runtime configuration.”

Evidence to mention:

- `GOAT_DEPLOY_MODE=1`
- `OLLAMA_BASE_URL=http://127.0.0.1:11435`
- `GET /api/models`
- streamed `/api/chat`

### 2. Streaming chat with typed events / 类型化流式聊天

**中文讲法：** “前后端不是一次性返回大文本，而是通过 SSE 流式返回 `thinking`、`token`、`chart_spec`、`artifact`、`error`、`done` 等事件，前端可以边生成边展示。”

**English talk track:** “The chat path is streamed over typed SSE events, so the frontend can render reasoning, answer tokens, chart specs, artifacts, errors, and completion separately.”

Good prompt:

```text
Explain the key idea of Porter's Five Forces in 5 bullet points.
```

### 3. Knowledge upload and RAG / 文件上传与知识库检索

**中文讲法：** “可以上传课程资料、PDF、CSV 或 Markdown，然后把文档变成可检索知识，让模型基于上传材料回答，而不是凭空猜。”

**English talk track:** “The app supports document and tabular ingestion, then uses retrieval-backed context so answers can be grounded in uploaded material.”

Good demo:

1. Upload a short PDF/Markdown/CSV.
2. Ask: `Summarize this document and cite the key evidence.`
3. Ask a follow-up question in the same session.

### 4. Charts and artifacts / 图表与可下载产物

**中文讲法：** “模型可以产生结构化图表事件，也可以把回答导出成 artifact 下载，不只是聊天窗口里的文本。”

**English talk track:** “The model can produce structured chart events and downloadable artifacts, which makes the app more like a workflow tool than a plain chatbot.”

Good prompt:

```text
Create a simple chart comparing revenue for Jan, Feb, and Mar: 10, 15, 12.
```

### 5. Workbench and bounded research / Workbench 与有边界的研究任务

**中文讲法：** “Workbench 不是无限自治 agent，而是有边界的 plan、browse、deep_research、canvas 工作流，有任务状态、事件时间线和可恢复的输出。”

**English talk track:** “The Workbench is intentionally bounded: plan, browse, deep research, and canvas workflows produce durable task state, event timelines, and reusable outputs.”

Only demo this if enabled:

```dotenv
GOAT_FEATURE_AGENT_WORKBENCH=1
```

### 6. Code sandbox / 代码沙箱

**中文讲法：** “代码执行能力不是直接在主进程里乱跑，而是通过显式 provider 和 runtime readiness 控制。Docker 是默认隔离方向，localhost 只是可信开发 fallback。”

**English talk track:** “Code execution is behind an explicit runtime provider and readiness gate. Docker is the intended isolation path, while localhost remains a trusted development fallback.”

Only demo this if Docker/runtime is ready:

```dotenv
GOAT_FEATURE_CODE_SANDBOX=1
GOAT_CODE_SANDBOX_PROVIDER=docker
```

### 7. Operational proof / 工程化可运维能力

**中文讲法：** “这个项目有健康检查、ready 检查、runtime target、Prometheus metrics、post-deploy check、rollback/runbook。演示的不只是功能，还有部署和恢复能力。”

**English talk track:** “The project includes health/readiness probes, runtime-target introspection, Prometheus metrics, post-deploy checks, rollback runbooks, and documented operational controls.”

Good live endpoints:

```text
/api/health
/api/ready
/api/system/runtime-target
/api/system/metrics
```

## Suggested 5-Minute Demo Flow / 5 分钟演示流程

1. **Open the UI / 打开界面**
   - Say this is the school Ubuntu deployment using local Ollama.
   - Mention no browser login is needed for the public demo shell.

2. **Basic chat / 基础聊天**
   - Ask a concise business or technical question.
   - Point out streaming tokens and model selection.

3. **Knowledge/RAG / 知识库**
   - Upload a small document or CSV.
   - Ask a grounded question about it.

4. **Chart/artifact / 图表或产物**
   - Ask for a simple chart or a downloadable Markdown summary.

5. **Operations proof / 运维证明**
   - Show `/api/health`, `/api/ready`, and `post_deploy_check`.
   - If time allows, show `/api/system/metrics`.

6. **Optional search / 可选搜索**
   - With `SERPER_API_KEY`, this demonstrates Serper-backed Google results.
   - Without `SERPER_API_KEY`, the same flow should demonstrate DuckDuckGo fallback.
   - Ask: `Search the latest news about AI deployment best practices and cite sources.`

## Go / No-Go Decision / 演示前放行标准

Go if all are true:

- `bash ops/build/build_school_server.sh` succeeds.
- `bash ops/deploy/deploy_school_server.sh` succeeds without unresolved fallback warnings.
- `python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606` prints `POST_DEPLOY_CHECK_OK`.
- `/api/ready` returns ready.
- The exact demo model appears in `/api/models`.
- Web search is either Serper-backed, using DuckDuckGo fallback, or explicitly disabled.
- The deployed commit/ref is known.

No-go / pause if any are true:

- Backend fails to start or search reports both Serper and DuckDuckGo unavailable.
- `systemctl --user status goat-ai.school-ubuntu` is repeatedly restarting.
- `post_deploy_check` reports no token/thinking SSE frame.
- Ollama status is unreachable on `127.0.0.1:11435`.
- You cannot identify which commit/ref is deployed.

## Final Notes / 最终备注

**中文：** 明天最稳的演示策略是：先保证 chat、upload/RAG、chart/artifact、health/ready 这些核心路径稳定；Workbench、sandbox、Web 搜索作为“已具备但按环境开关启用”的加分项。现在 Serper 不再是启动硬依赖，即使没有 key，主线演示仍然成立。

**English:** The safest demo strategy is to anchor the presentation around chat, upload/RAG, chart/artifact, and health/readiness. Treat Workbench, sandbox, and web search as environment-enabled bonus capabilities, not mandatory dependencies for the main story. Serper is no longer a startup hard dependency, so the main demo remains viable without a key.
