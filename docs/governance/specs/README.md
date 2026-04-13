# Feature Specs Pilot

This directory is a lightweight, repo-native pilot for complex change work products.

Use it when a brownfield change needs a short-lived `spec.md`, `plan.md`, and `tasks.md`
 set before implementation starts or before a risky slice expands across multiple layers.

This is not a second governance system or source of truth.

- `AGENTS.md` and repo-local skills remain the permanent operating model.
- [ROADMAP.md](../ROADMAP.md) remains the source of truth for planned and unfinished work.
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) remains the source of truth for landed facts.
- Decision records stay under [docs/decisions](../../decisions/README.md) and existing decision packages under `docs/architecture/`.

Each feature folder should stay small and feature-scoped.

- `spec.md`: user/problem statement, scope, constraints, and acceptance edges.
- `plan.md`: reviewable slices, risks, validations, and assumptions.
- `tasks.md`: execution checklist that can be closed as slices land.

The `_template/` folder provides the approved file set.

The `governance-tooling-follow-ons/` example is an intentionally real pilot artifact for this repository. It exists as evidence for how to use the pattern without replacing the repository's existing governance skeleton.
