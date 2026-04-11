# WSL-First Development on Windows

This repository now treats **WSL + a repository stored inside the WSL filesystem** as the default development baseline for Windows-hosted contributors.

Why:

- CI runs on Ubuntu
- production is Ubuntu-oriented
- Linux shell behavior, Python packaging, Node tooling, and Linux-targeted desktop validation are more predictable in WSL than in native PowerShell
- Codex on Windows can work with WSL-hosted projects directly: <https://developers.openai.com/codex/app/windows>

## Default baseline

If you develop on a Windows machine, prefer:

- distro: `Ubuntu`
- repo path: `~/dev/GOAT_AI`
- shell: WSL Bash/Zsh for day-to-day backend, scripts, tests, and Linux-targeted validation

Do **not** treat `/mnt/<drive>/...` as the recommended active working copy for this repo. Keep the main checkout inside the Linux filesystem.

## One-time migration

### 1. Prepare the WSL workspace

Inside WSL:

```bash
mkdir -p ~/dev
cd ~/dev
git clone https://github.com/mingzhi0119/GOAT_AI.git
cd GOAT_AI
```

If you already have a Windows checkout, prefer a fresh clone inside WSL over editing the Windows copy from Linux.

### 2. Install the baseline toolchain in WSL

Recommended baseline:

- Python `3.14`
- `uv`
- Node `24.x`
- Rust stable
- `cargo-audit`

Representative Ubuntu setup:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  curl \
  file \
  git \
  libayatana-appindicator3-dev \
  libglib2.0-dev \
  librsvg2-dev \
  libssl-dev \
  libwebkit2gtk-4.1-dev \
  libxdo-dev \
  pkg-config \
  wget
```

Install Python, Node, Rust, and `uv` using your team's preferred package manager or version manager, but keep the versions aligned with CI and [`README.md`](../README.md).

### 3. Recreate local environments inside WSL

Do not reuse Windows-owned development environments.

Examples:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ci.txt
```

```bash
cd frontend
npm ci
```

Rust build artifacts and Python environments should also be recreated inside WSL instead of being shared from a Windows checkout.

## Codex usage on Windows

If you use the Codex app on Windows, open the WSL-hosted repo via:

- `\\wsl$\Ubuntu\home\<your-user>\dev\GOAT_AI`

Default expectation:

- use the WSL-hosted repo as the main working copy
- prefer running the agent in WSL for backend, scripts, CI parity, and Linux-targeted artifact work
- use the repo-local skills under [`.agents/skills`](../.agents/skills) for Linux-targeted validation from Windows-hosted Codex sessions

## Daily development loop

Run these from WSL unless the task is explicitly a Windows-only exception:

- backend work
- `python -m tools.*`
- `pytest`
- `npm ci`, `npm test -- --run`, `npm run build`
- shell scripts such as `deploy.sh`, `watchdog.sh`, and `healthcheck.sh`
- Linux desktop sidecar builds and Linux `cargo test` validation

## Windows-native exceptions

Use native Windows only when it is required or materially more reliable:

- Windows installer generation and verification
- `scripts/install_desktop_prereqs.ps1`
- `deploy.ps1`
- WebView2 validation
- MSVC / Visual Studio Build Tools flows
- Windows shell integration and packaged-installer behavior checks

These are exceptions, not the default inner loop.

## Validation expectations

From a Windows machine:

- Linux-targeted compile, package, shell-script, and Ubuntu CI-parity checks should run from WSL
- PowerShell-only results are not enough evidence for Linux correctness
- if a change affects both Linux and Windows packaging behavior, validate the Linux path in WSL first, then run the required Windows-native exception flow

## Related docs

- [README.md](../README.md)
- [OPERATIONS.md](OPERATIONS.md)
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)
- [ROADMAP.md](ROADMAP.md)
- [AGENTS.md](../AGENTS.md)
