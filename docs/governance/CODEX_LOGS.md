# Codex Logs

This document defines the repository-native Codex change-log workflow.

Codex logs are a working history of change execution. They do not replace
[`ROADMAP.md`](ROADMAP.md), [`PROJECT_STATUS.md`](PROJECT_STATUS.md), or
decision artifacts under [`docs/decisions/`](../decisions/README.md).

## Purpose

- keep a durable record of code-changing work carried out by Codex threads
- make long-running implementation history visible without overloading roadmap
  or status documents
- give future threads a predictable place to inspect recent implementation
  intent, validations, and follow-up risks

## Canonical location

- Monthly log files live under `docs/governance/codex-logs/`.
- Use one file per month with the naming pattern `YYYY-MM.md`.
- Create the month file on the first entry for that month.
- Append new entries to the active month file so the log stays chronological.

## Required recording rules

- Read-only review work is exempt.
- Every code-changing task must record at least one log entry.
- Long-running tasks record one entry per commit.
- Small tasks record one entry per conversation round-trip.
- Treat edits to source, tests, docs, workflows, prompts, and agent rules as
  code-changing work for this policy.

## Entry template

Use this shape unless a task needs a clearly better format:

```md
## YYYY-MM-DD - Short title

- Task class: small task | long-running task
- Trigger: why this task started
- Changes: concise summary of what changed
- Files: `path/to/file`; `path/to/other-file`
- Validation: commands run, or `not run`
- Risks or follow-up: optional
```

## Relationship to other governance docs

- `ROADMAP.md` tracks unfinished work only.
- `PROJECT_STATUS.md` records landed facts only.
- Decision records and decision packages capture durable rationale for
  architecture-sensitive choices.
- Codex logs capture execution history for code-changing work.
