# Desktop Evidence Checklist

Check these invariants when desktop governance changes:

- packaged gate retains failure diagnostics for CI-built packaged binaries
- release evidence proves both MSI and NSIS paths when installers exist
- scheduled drill retains installed-desktop evidence independently of release signing
- installed evidence keeps the fixed order:
  - install
  - healthy launch
  - fault scenarios
  - uninstall
- summaries remain useful for first-pass triage without rerunning the workflow

Implementation anchors:

- [tools/desktop/packaged_shell_fault_smoke.py](../../../../tools/desktop/packaged_shell_fault_smoke.py)
- [tools/desktop/installed_windows_desktop_fault_smoke.py](../../../../tools/desktop/installed_windows_desktop_fault_smoke.py)
- [frontend/src-tauri/src/main.rs](../../../../frontend/src-tauri/src/main.rs)
