# GOAT AI — Install, run, deploy, stop

Python-only stack: **Streamlit** + **Ollama**. No Node.js required.

## Install (development)

```bash
cd "$HOME/GOAT_AI"   # or your clone path
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust variables, or `export` them in your shell (never commit real secrets).

## Run locally

```bash
source .venv/bin/activate
export OLLAMA_BASE_URL=http://127.0.0.1:11434   # default if unset
streamlit run app.py --server.port 62606
```

Open `http://127.0.0.1:62606/`. Health check: `curl -sf http://127.0.0.1:62606/_stcore/health`.

## Deploy (JupyterLab / shared server)

From the project directory (e.g. `$HOME/GOAT_AI`):

```bash
bash deploy.sh
```

Or `./deploy.sh` after `chmod +x deploy.sh`.

- **Logs:** `streamlit.log` in the project root (append from `nohup`).
- **PID:** `streamlit.pid` — process id of the Streamlit server.
- **Stop:** `kill "$(cat streamlit.pid)"` (or `kill <pid>` if the file is stale).

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OLLAMA_BASE_URL` | Ollama HTTP base (default `http://127.0.0.1:11434`). |
| `OLLAMA_GENERATE_TIMEOUT` | Request timeout in seconds (default `120`). |
| `GOAT_MAX_UPLOAD_MB` | Max upload size; keep in sync with `.streamlit/config.toml` `maxUploadSize`. |
| `GOAT_MAX_DATAFRAME_ROWS` | Max rows after load (default `50000`). |
| `GOAT_USE_CHAT_API` | `true` → `/api/chat` (multi-turn); `false` → `/api/generate` with transcript. |
| `GOAT_SYSTEM_PROMPT` | Optional full system prompt override. |
| `GOAT_SYSTEM_PROMPT_FILE` | Optional path to UTF-8 file containing system prompt. |

## Reverse proxy (school host)

Typical pattern: public `https://…/mingzhi/` → `http://127.0.0.1:62606/`.

- WebSocket support is required for Streamlit; configure your proxy accordingly (upgrade headers, long timeouts).
- Keep Ollama on **localhost** unless the network is trusted and access-controlled.

## Data handling

Uploaded CSV/XLSX is held **in memory** for the session only; nothing is written to disk for persistence unless you change the app.

## Agentic behavior (report)

The app follows a simple loop: **perceive** (user message + optional dataframe summary via `describe_dataframe`) → **act** (Ollama `/api/chat` or generate) → **verify** (prompt asks the model to cite shape/columns when data is present). Tool-style logic is plain Python functions, not a separate agent framework.
