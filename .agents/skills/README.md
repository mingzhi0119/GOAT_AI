# Repo-Local Skills

This directory contains GOAT AI repo-local Codex skills.

## Governance and proof skills

- [goat-engineering-audit](goat-engineering-audit/SKILL.md): repository-grounded readiness and governance audits; use for 9/10-style assessment and structured findings.
- [goat-api-contract-proof](goat-api-contract-proof/SKILL.md): backend/docs/frontend API contract sync and proof; composes with black-box contract tests.
- [goat-ci-surface-router](goat-ci-surface-router/SKILL.md): route a change set to the minimum required validation matrix and CI-equivalent checks.
- [goat-desktop-release-evidence](goat-desktop-release-evidence/SKILL.md): packaged gate vs release evidence vs drill boundaries for desktop workflows and retained proof.
- [goat-workbench-authz-proof](goat-workbench-authz-proof/SKILL.md): caller-scoped workbench authz and future-widening prevention proof.
- [goat-observability-contract-proof](goat-observability-contract-proof/SKILL.md): metric family plus label/query-shape proof across exporter, assets, and runbooks.
- [goat-governance-sync](goat-governance-sync/SKILL.md): align roadmap, status, and ops docs with proved repo reality.

## High-frequency dry runs

- [engineering audit dry runs](goat-engineering-audit/references/dry-run-examples.md): readiness-review prompts and expected finding structure.
- [API contract dry runs](goat-api-contract-proof/references/dry-run-examples.md): contract-sync prompts for backend, docs, and frontend surfaces.
- [CI routing dry runs](goat-ci-surface-router/references/dry-run-examples.md): changed-file prompts that map to the minimum required validation matrix.
- [desktop evidence dry runs](goat-desktop-release-evidence/references/dry-run-examples.md): packaged vs installed vs drill proof prompts.
- [workbench authz dry runs](goat-workbench-authz-proof/references/dry-run-examples.md): caller-scoped capability and widening-prevention prompts.
- [observability proof dry runs](goat-observability-contract-proof/references/dry-run-examples.md): metric-label and selector-proof prompts.

## Forward-tested patterns

- [shared prompt and output patterns](goat-engineering-audit/references/forward-test-patterns.md): repeated read-only prompt skeletons, output shapes, and real checks exercised during live forward-tests.

## Execution-layer helpers

- [wsl-linux-build](wsl-linux-build/SKILL.md): run Linux-targeted commands through WSL from Windows.
- [wsl-linux-ops-checks](wsl-linux-ops-checks/SKILL.md): run Ubuntu-facing ops scripts and checks through WSL.
- [wsl-linux-rust-desktop](wsl-linux-rust-desktop/SKILL.md): run Linux Tauri and Rust desktop validation through WSL.

Use the `goat-*` skills to decide what truth to read and what proof is required. Use the `wsl-*` skills when that proof needs Linux parity from a Windows-hosted checkout.
