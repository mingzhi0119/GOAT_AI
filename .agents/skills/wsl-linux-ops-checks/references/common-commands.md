# Common WSL operations commands

Representative commands for this repository:

```bash
bash ./ops/deploy/deploy.sh
bash ./ops/verification/healthcheck.sh
bash ./ops/verification/watchdog.sh
bash ./ops/verification/phase0_check.sh
bash ./scripts/wsl/wsl_api_contract_refresh.sh
python -m tools.desktop.desktop_smoke
```

Use the generic WSL helper from the repo root so paths stay consistent:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "bash ./ops/deploy/deploy.sh"
```
