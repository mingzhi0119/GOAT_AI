# WSL Workflows on Windows

Windows-native development remains supported for this repository. Use WSL when you specifically need Linux semantics that should match Ubuntu CI or production behavior.

Why WSL is still useful:

- CI runs on Ubuntu
- production is Ubuntu-oriented
- Linux shell behavior, Python packaging, Node tooling, and Linux-targeted desktop validation are sometimes more predictable in WSL than in native PowerShell
- Codex on Windows can work with WSL-hosted paths directly: <https://developers.openai.com/codex/app/windows>

## When to use WSL

Use WSL on a Windows machine for tasks such as:

- Linux-targeted compile or package checks
- shell-script validation
- Ubuntu CI parity checks
- Linux desktop sidecar builds or Linux `cargo test`
- cases where a dependency or wheel is awkward on Windows but straightforward in Linux

Do not treat WSL as mandatory for the ordinary Windows-native inner loop unless the task actually needs Linux behavior.

## Optional WSL checkout

If you want a Linux-native copy of the repo for those tasks, a clean clone is the safest path:

```bash
mkdir -p ~/dev
cd ~/dev
git clone https://github.com/mingzhi0119/GOAT_AI.git
cd GOAT_AI
```

This is optional. It is a convenience path for Linux-targeted work, not the required default.

## Optional WSL toolchain

Recommended tooling when you do use WSL:

- Python `3.14`
- `uv`
- Node `24.x`
- Rust stable
- `cargo-audit`

Representative Ubuntu packages:

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

## Codex usage on Windows

If you use the Codex app on Windows and want to run a Linux-targeted workflow through WSL, you can open a WSL-hosted copy via:

- `\\wsl$\Ubuntu\home\<your-user>\dev\GOAT_AI`

Use the repo-local skills under [`.agents/skills`](../../.agents/skills) when you want WSL-backed validation for Linux-targeted work.

## Windows-native stays primary

The following remain normal Windows-native flows:

- ordinary day-to-day editing and local development
- Windows installer generation and verification
- `scripts/desktop/install_desktop_prereqs.ps1`
- `ops/deploy/deploy.ps1`
- WebView2 validation
- MSVC / Visual Studio Build Tools flows
- Windows shell integration and packaged-installer behavior checks

## Validation expectations

From a Windows machine:

- Linux-targeted compile, package, shell-script, and Ubuntu CI-parity checks should run from WSL
- PowerShell-only results are not enough evidence for Linux correctness when the target behavior is Linux-specific
- if a change affects both Linux and Windows packaging behavior, validate the Linux path in WSL first, then run the required Windows-native flow

## Related docs

- [README.md](../../README.md)
- [OPERATIONS.md](OPERATIONS.md)
- [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md)
- [AGENTS.md](../../AGENTS.md)
