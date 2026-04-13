---
name: goat-engineering-audit
description: Run repository-grounded engineering audits and readiness reviews for GOAT AI. Use when the task is to judge current engineering maturity, audit governance or regression readiness, separate mechanically proven repo capabilities from residual risks or external blockers, and produce severity-ranked findings backed by docs, workflows, code, and tests.
---

# GOAT Engineering Audit

Use this skill when the request is to audit current repository reality rather than design a new feature.

## Read First

- [AGENTS.md](../../../AGENTS.md)
- [docs/governance/ROADMAP.md](../../../docs/governance/ROADMAP.md)
- [docs/governance/PROJECT_STATUS.md](../../../docs/governance/PROJECT_STATUS.md)
- [references/truth-sources.md](references/truth-sources.md)
- [references/severity-rubric.md](references/severity-rubric.md)
- [references/readiness-report-template.md](references/readiness-report-template.md)

## Workflow

1. Start from the governance truth sources before reading implementation details.
2. Read the workflows, implementation files, and tests that correspond to the claimed landed capability.
3. Separate four buckets explicitly:
   - mechanically proven in-repo capability
   - residual risk that does not reopen a closed watchpoint
   - governance or evidence gap
   - external blocker outside repo-only proof
4. Prefer findings about bugs, regressions, governance gaps, and evidence gaps.
5. Do not re-report a previously closed watchpoint unless current code, tests, or workflow shape prove it regressed.
6. When a path is desktop, authz/workbench, or observability-heavy, compose with the specialized repo-native proof skills if they exist.

## Guardrails

- Audit current repository state, not historical intent by itself.
- Do not treat roadmap text as sufficient proof without matching code/tests/workflows.
- Do not downgrade or upgrade severity based on writing style or naming alone.
- Always distinguish repo-internal proof from GitHub, runner, branch-protection, or secret-based conditions.

## Output

- Give a top-level conclusion first.
- Rank findings by severity.
- For each finding, include: finding, severity, why it matters, evidence, minimal fix, affected files/workflows/tests, and what blocks readiness.
- End with explicit sections for:
  - evidence that already supports readiness
  - what is still insufficient
  - external blockers

