# CI Routing Truth

Start from these sources:

- [ci.yml](../../../../.github/workflows/ci.yml)
- [OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)
- [AGENTS.md](../../../../AGENTS.md)

## Important routing boundaries

- `backend-fast -> backend-heavy -> backend` is the normal backend gate order
- frontend changes can require `npm test`, `npm run build`, contract checks, and broader browser-level proof depending on touched files
- desktop packaging is path-scoped and should only trigger for desktop build inputs and desktop governance surfaces
- Linux-targeted parity checks from Windows should compose with:
  - [wsl-linux-build](../../wsl-linux-build/SKILL.md)
  - [wsl-linux-ops-checks](../../wsl-linux-ops-checks/SKILL.md)
  - [wsl-linux-rust-desktop](../../wsl-linux-rust-desktop/SKILL.md)
