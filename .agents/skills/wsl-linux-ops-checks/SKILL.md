---
name: wsl-linux-ops-checks
description: Run Ubuntu-facing shell scripts, deploy helpers, and backend operational checks through WSL from a Windows checkout. Use when Codex needs Linux semantics for ops/deploy/deploy.sh, healthcheck.sh, watchdog.sh, ops/verification/phase0_check.sh, WSL-specific refresh scripts, or backend checks whose behavior depends on bash, shebangs, paths, services, or Linux process behavior. Do not use for Windows-only PowerShell automation.
---

# WSL Linux Ops Checks

Use this skill for Linux-oriented operational validation in this repository.

## Read First

- [`references/common-commands.md`](references/common-commands.md)
- [`docs/operations/OPERATIONS.md`](../../../../docs/operations/OPERATIONS.md)

## Workflow

1. Run shell scripts and Linux-facing helper commands through `.agents/skills/wsl-linux-build/scripts/invoke-wsl-command.ps1`.
2. Validate bash semantics, shebang behavior, path handling, exit codes, and service assumptions under WSL instead of inferring them from PowerShell.
3. Prefer explicit commands that can be repeated by teammates and CI.
4. If the work changes repository policy rather than just executing a workflow, also update [`AGENTS.md`](../../../../AGENTS.md) and [`docs/standards/ENGINEERING_STANDARDS.md`](../../../../docs/standards/ENGINEERING_STANDARDS.md).

## Guardrails

- Do not sign off Ubuntu-facing scripts after PowerShell-only execution.
- Do not hide Linux-only failures behind Windows fallbacks.
- Keep operator-facing commands and runbooks aligned when semantics change.
