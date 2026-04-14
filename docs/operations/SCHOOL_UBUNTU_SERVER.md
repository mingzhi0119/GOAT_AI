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
server-specific values. `ops/deploy/deploy_school_server.sh` uses that file as the
school-server source of truth before the generic `.env`, and the school systemd unit
keeps the same dedicated `EnvironmentFile`. The application config layer no longer
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

`ops/deploy/deploy_school_server.sh` is the only supported school-server deploy entrypoint.
It runs as `GOAT_DEPLOY_MODE=1`, prefers `.env.school-ubuntu`, starts
`start_ollama_local.sh` before the backend process, and uses the
`goat-ai.school-ubuntu` user service when available. The generic local Linux and remote
deploy wrappers never touch the school-only helper scripts.
