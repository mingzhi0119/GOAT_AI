# Common WSL operations commands

Representative commands for this repository:

```bash
bash ./deploy.sh
bash ./scripts/healthcheck.sh
bash ./scripts/watchdog.sh
bash ./phase0_check.sh
bash ./scripts/wsl_api_contract_refresh.sh
python -m scripts.desktop_smoke
```

Use the generic WSL helper from the repo root so paths stay consistent:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "bash ./deploy.sh"
```
