# GOAT AI Roadmap

> Last updated: 2026-04-14
> Current release tag: **v1.3.0**
> Shipped status: [PROJECT_STATUS.md](PROJECT_STATUS.md)

This file tracks **unfinished work only**.

Completed phases, landed slices, and historical closeout notes live in:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [DOMAIN.md](../architecture/DOMAIN.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)

---

## Current posture

GOAT AI is now in a **maintenance-first** posture.

The project is no longer prioritizing broad platform expansion, frontier runtime
work, desktop deepening, or repo-governance/tooling growth. Most historical
future-facing items have been intentionally removed from the active roadmap so
the remaining list stays honest and small while focus shifts to other work.

## Open Work

### Active maintenance priorities

1. **Deployment and operations stability**
   - keep the three deployment modes (`local`, `school_server`, `remote`)
     healthy and documented
   - fix regressions in remote hosting, school-server operation, and local
     development/bootstrap paths
   - preserve current health/readiness, rollback, and post-deploy verification
     behavior
2. **Security and reliability fixes**
   - address bugs or security issues in the existing shipped surface
   - maintain the current remote rate-limit, model allowlist, and deployment
     safety posture
3. **Documentation cleanup**
   - keep `README.md` as a compact entrypoint
   - keep detailed behavior, deployment, and runbook truth in `docs/`

### Deferred work

The following areas are intentionally **paused** and should not be treated as
near-term commitments:

- deeper workbench/runtime widening beyond the shipped bounded surface
- project-memory mutation and write-capable connectors
- remote connector adapters and connected-app expansion
- browse / deep-research hardening beyond the current shipped baseline
- sandbox expansion beyond the current Docker-first MVP
- Rust sandbox supervisor work
- desktop-native UX deepening and Rust runtime bridge work
- public macOS release/signing work and updater rollout
- repo-local skill expansion and governance-tooling follow-ons
- frontend placeholders for cloud-model APIs, connected apps, or other
  non-shipped frontier surfaces

If any of these areas are resumed later, they should return as a new narrowed
roadmap entry or decision package rather than being inferred from old planning
notes.

---

## Dependencies and constraints

- Planning for future workbench, connector, project-memory, and other frontier
  surfaces should still follow the canonical policy in
  [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md), especially
  the admission-gate and capability-gate rules.
- Shared runtime foundations continue to build on the shipped object-store
  boundary plus the hosted/server Postgres runtime metadata posture in
  [POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md](../architecture/POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md),
  while local and desktop remain SQLite-first by design.

### Repository-native Skills and Agent Automation

The `wsl-linux-build`, `wsl-linux-ops-checks`, and `wsl-linux-rust-desktop` remain execution-layer helpers, while the new `goat-*` skills sit above them as governance/proof workflows.

---
