# Simon School Ubuntu Server Profile

This runbook is only for the school-owned Ubuntu server profile that keeps a sibling
`ollama-local` runtime layout. It is **not** the generic GOAT AI deploy path.

## Opt-in switches

Enable the school profile explicitly with either of these:

- `GOAT_USE_SCHOOL_OLLAMA_LOCAL=1`
- `GOAT_OLLAMA_PROFILE=school-ubuntu`

Keep the school server's Ollama endpoint in its own env file:

```dotenv
GOAT_USE_SCHOOL_OLLAMA_LOCAL=1
OLLAMA_BASE_URL=http://127.0.0.1:11435
```

Prefer `.env.school-ubuntu` (or another dedicated `EnvironmentFile`) for the school
server-specific values. `ops/deploy/deploy.sh` now checks that file before the generic
`.env` when the school profile is enabled. The application config layer no longer
auto-detects `../ollama-local` or changes ports based on sibling directories.

## Systemd units

- generic user unit: `ops/systemd/goat-ai.service`
- school-only variant: `ops/systemd/goat-ai.school-ubuntu.service`

The school-only unit keeps `ExecStartPre=%h/GOAT_AI/scripts/ollama/start_ollama_local.sh`
and reads `%h/GOAT_AI/.env.school-ubuntu` in addition to the normal `.env`.

Recommended install:

```bash
mkdir -p ~/.config/systemd/user
cp ~/GOAT_AI/ops/systemd/goat-ai.school-ubuntu.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now goat-ai.school-ubuntu
```

## School-only helper scripts

These scripts remain supported for the school Ubuntu profile only:

- `scripts/ollama/start_ollama_local.sh`
- `scripts/ollama/status_ollama_local.sh`
- `scripts/ollama/stop_ollama_local.sh`
- `scripts/ollama/ollama_local.sh`

Example commands:

```bash
bash scripts/ollama/start_ollama_local.sh
bash scripts/ollama/status_ollama_local.sh
bash scripts/ollama/stop_ollama_local.sh
bash scripts/ollama/ollama_local.sh pull <model>
```

## Deploy behavior

`ops/deploy/deploy.sh` will only call `start_ollama_local.sh` when the school profile is
explicitly enabled. In that mode it prefers `.env.school-ubuntu`, tries the
`goat-ai.school-ubuntu` user service before the generic unit, and also forwards the
resolved `OLLAMA_BASE_URL` into the `nohup` fallback path. Otherwise deploy stays on the
standard Ollama default `http://127.0.0.1:11434` and never touches the school-only
helper scripts.
