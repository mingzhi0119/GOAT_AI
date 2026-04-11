---
name: wsl-linux-rust-desktop
description: Run Linux desktop, Tauri, or Rust validation for frontend/src-tauri through WSL from a Windows checkout. Use when Codex needs Ubuntu-like behavior for cargo test, Linux desktop sidecar builds, Tauri bundle resources, GTK/WebKit dependency issues, or CI parity with the desktop-supply-chain job. Do not use for native Windows desktop packaging or non-Linux frontend work.
---

# WSL Linux Rust Desktop

Use this skill for Linux-targeted desktop validation and packaging in this repository.

## Read First

- [`.github/workflows/ci.yml`](../../../../.github/workflows/ci.yml)
- [`frontend/src-tauri/tauri.conf.json`](../../../../frontend/src-tauri/tauri.conf.json)
- [`references/ubuntu-packages.md`](references/ubuntu-packages.md)

## Workflow

1. Use `$wsl-linux-build`'s helper script to run every Linux desktop command through WSL.
2. Match the CI flow in order:
   - install Linux packages if needed
   - build the Linux desktop sidecar
   - run `cargo test --manifest-path frontend/src-tauri/Cargo.toml`
3. If the change touches Tauri bundle resources such as icons, binaries, or config, validate the Linux path in WSL even if Windows cargo tests are already green.
4. Keep sidecar artifacts aligned with `frontend/src-tauri/binaries` and the target triple expected by the CI job.

## Guardrails

- Do not diagnose GTK, WebKit, pkg-config, or Tauri Linux failures from PowerShell-only runs.
- Do not treat Windows `cargo test` as proof of Linux desktop correctness.
- If Linux-specific packaging assumptions change, update CI in the same change.
