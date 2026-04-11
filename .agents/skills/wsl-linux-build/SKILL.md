---
name: wsl-linux-build
description: Run Linux-targeted compile, build, package, shell-script, or CI-parity commands from this Windows checkout via WSL. Use when Codex is on Windows but needs Ubuntu/Linux behavior, Linux binaries, bash semantics, apt/pkg-config toolchains, or results that must match GitHub Actions ubuntu-latest jobs. Do not use for native Windows-only commands or simple local file edits.
---

# WSL Linux Build

Use this skill whenever a task targets Linux from a Windows-hosted checkout.

## Inputs

- A Linux command string to run from the repository root
- Optional WSL distro name when the default distro is not the intended target

## Workflow

1. Confirm `wsl.exe` is available. If WSL is missing or not configured, stop and report that the Linux-targeted task cannot be validated correctly from PowerShell alone.
2. Run Linux commands through `.agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1`.
3. Keep commands repo-root relative so paths resolve the same way across contributors and CI.
4. Mirror Ubuntu dependency setup from [`.github/workflows/ci.yml`](../../../../.github/workflows/ci.yml) before diagnosing build failures that may come from missing Linux packages.
5. Report the exact WSL command and distro used when you summarize results.

## Guardrails

- Do not substitute a native Windows toolchain for a Linux-targeted compile, package, or smoke check.
- Do not claim Linux parity from PowerShell-only results.
- When the task is really a permanent repository rule rather than a one-off workflow, also update [`AGENTS.md`](../../../../AGENTS.md) and the engineering standards.

## Helper

The helper script accepts a raw Linux command:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1 -Command "uname -a"
```

Set `-Distro Ubuntu` to pin a specific distro when needed.
