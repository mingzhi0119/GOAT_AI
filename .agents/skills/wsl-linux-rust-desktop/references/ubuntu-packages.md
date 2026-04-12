# Ubuntu packages for Linux desktop parity

Match the desktop CI dependency set before diagnosing Linux-only desktop failures:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  curl \
  file \
  libayatana-appindicator3-dev \
  libglib2.0-dev \
  librsvg2-dev \
  libssl-dev \
  libwebkit2gtk-4.1-dev \
  libxdo-dev \
  wget
```

Representative Linux validation commands:

```bash
python -m tools.desktop.build_desktop_sidecar --target-triple x86_64-unknown-linux-gnu --clean
cargo test --manifest-path frontend/src-tauri/Cargo.toml
```
