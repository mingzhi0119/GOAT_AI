# GOAT AI Decision Records

This directory is the canonical entrypoint for repository-native decision capture.

It does three things:

- defines when to use a lightweight decision record versus a heavier decision package
- provides templates for new decision artifacts
- points to existing in-repo examples that still live under `docs/architecture/`

This directory is an entrypoint, not a second governance system.

- `AGENTS.md` and `docs/standards/ENGINEERING_STANDARDS.md` remain the permanent policy layer
- `docs/governance/ROADMAP.md` tracks unfinished work only
- `docs/governance/PROJECT_STATUS.md` records landed facts only
- `docs/governance/specs/` holds feature-scoped work products, not canonical architecture decisions

## Document classes

### Decision record

Use a decision record for architecture-sensitive choices that need a stable rationale but do not require a migration playbook.

Typical cases:

- terminology or naming boundaries
- interface or ownership direction
- architectural tradeoffs with clear consequences
- CI or governance choices that affect how the repo is maintained

Template:

- [decision-record.md](templates/decision-record.md)

### Decision package

Use a decision package when the decision changes compatibility, rollout sequencing, storage shape, migration posture, rollback expectations, or operator behavior.

Typical cases:

- datastore or persistence evolution
- rollout shapes that need additive-first sequencing
- compatibility or downgrade behavior
- migration and rollback planning for risky runtime or operational changes

Template:

- [decision-package.md](templates/decision-package.md)

## Existing examples

- Lightweight decision record example:
  [WORKBENCH_TERMINOLOGY_DECISION.md](../architecture/WORKBENCH_TERMINOLOGY_DECISION.md)
- Heavy decision package examples:
  [STORAGE_EVOLUTION_DECISION_PACKAGE.md](../architecture/STORAGE_EVOLUTION_DECISION_PACKAGE.md)
  [EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md](../architecture/EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md)
  [PROJECT_MEMORY_CONNECTORS_FOUNDATION_DECISION_PACKAGE.md](../architecture/PROJECT_MEMORY_CONNECTORS_FOUNDATION_DECISION_PACKAGE.md)
  [DESKTOP_DISTRIBUTION_MATURITY_DECISION_PACKAGE.md](../architecture/DESKTOP_DISTRIBUTION_MATURITY_DECISION_PACKAGE.md)

## PR guidance

Architecture-sensitive pull requests should link the relevant decision artifact or explicitly say `N/A` when no record/package is needed.

Use a decision artifact when the change materially affects one or more of:

- architecture or ownership boundaries
- operator-visible tradeoffs
- rollback or failure handling
- compatibility or migration behavior
- release, CI, or governance process

Keep the PR summary short. Put the durable rationale in the linked decision artifact and the executable proof in tests, contracts, workflow links, or runbooks.
