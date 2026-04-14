# GOAT AI Desktop Distribution Readiness

This document is the operator-facing truth source for desktop packaging maturity,
platform prerequisites, updater gating, and known release blockers.

## Platform matrix

| Platform | Current repo-native proof | Public distribution status | Notes |
|------|---------|---------|---------|
| Windows | Signed MSI + NSIS provenance, installed-artifact evidence, packaged-shell fault smoke | Public path available | Current default public desktop distribution path |
| Linux | Ubuntu CI and WSL parity now cover sidecar build, full packaged desktop build, and provenance for `AppImage` + `deb` artifacts | Internal-test packaging path ready | Public release shape is still package-based rather than updater-driven |
| macOS | Manual-dispatch packaged-desktop scaffold plus blocker reporting | Blocked on signing/notarization automation | Public distribution remains blocked until Apple signing + notarization secrets and runner setup are available |

## Developer and operator prerequisites

### Windows

- run `.\scripts\desktop\install_desktop_prereqs.ps1 -Profile Runtime` for runtime-only setup
- run `.\scripts\desktop\install_desktop_prereqs.ps1 -Profile Dev` for Rust/MSVC development setup
- current package ids remain:
  - `Microsoft.EdgeWebView2Runtime`
  - `Ollama.Ollama`
  - `Rustlang.Rustup`
  - `Microsoft.VisualStudio.2022.BuildTools`

### Linux / WSL

- use WSL or Ubuntu for Linux-targeted desktop validation from Windows
- required Ubuntu packages mirror CI:
  - `build-essential`
  - `curl`
  - `file`
  - `libayatana-appindicator3-dev`
  - `libglib2.0-dev`
  - `librsvg2-dev`
  - `libssl-dev`
  - `libwebkit2gtk-4.1-dev`
  - `libxdo-dev`
  - `wget`
- expected toolchain:
  - Python `3.14`
  - Node `24.14.1`
  - Rust stable

### macOS

- Xcode Command Line Tools
- Python `3.14`
- Node `24.14.1`
- Rust stable
- Apple Developer signing certificate and notarization credentials for any public package

## Runtime diagnostics

Packaged desktop startup and runtime parameters should be diagnosed through these sources first:

- `GET /api/system/desktop`
- `<app_log_dir>/desktop-shell.log`
- packaged desktop sidecar stdout/stderr retained by smoke workflows

Important packaged-runtime environment and launch parameters:

- `GOAT_RUNTIME_ROOT`
- `GOAT_LOG_DIR`
- `GOAT_LOG_PATH`
- `GOAT_DATA_DIR`
- `GOAT_SERVER_PORT`
- `GOAT_LOCAL_PORT`
- `GOAT_DEPLOY_MODE=0`
- `GOAT_DESKTOP_SHELL_LOG_PATH`
- `GOAT_READY_SKIP_OLLAMA_PROBE=1` for CI/smoke evidence only

## Updater readiness gate

Desktop updater enablement remains intentionally deferred.

Do not turn on updater channels until all of these are true:

- signed public distribution exists for every platform that will use the updater
- public artifact provenance and installed-smoke evidence are green for that platform
- channel manifests and rollback expectations are documented
- operator incident/runbook docs name the updater failure modes and recovery steps

Current updater direction:

- Windows remains installer-first, not updater-first
- Linux should continue to prefer package-manager or explicit artifact installs
- macOS updater work stays blocked behind signing and notarization automation

## Current blockers

### macOS public distribution blockers

- missing GitHub-hosted signing automation for macOS desktop artifacts
- missing Apple certificate import / keychain setup in CI
- missing notarization credentials and submission flow
- no merge-proven installed macOS smoke path yet

### Cross-platform follow-ons

- updater channels remain disabled until signed multi-platform release evidence is stable
- Linux public distribution policy still needs a final decision between `AppImage`, `deb`, or both

## Minimal fallback path

Until the macOS blockers above are closed:

- keep Windows as the only public signed desktop path
- use Linux packaged artifacts for internal validation and operator testing
- keep macOS packaging in manual/internal-test mode with an explicit blocker report rather than treating it as released
