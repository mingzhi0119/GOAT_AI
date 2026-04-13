# Code Sandbox Runtime Follow-ons Spec

Status: draft

This is a non-canonical working artifact.

- `ROADMAP.md` owns planned work.
- `PROJECT_STATUS.md` owns landed facts.
- `AGENTS.md` and repo-local skills own the standing governance model.

## Summary

Land the next safe runtime-control slice for the durable code sandbox without
widening the public `/api/code-sandbox/*` surface. The smallest successful
outcome is queued plus running cancellation, fail-closed startup recovery for
abandoned executions, and better workspace/runtime introspection while keeping
egress and supervisor hardening explicitly blocked behind future proof.

## Scope

- In scope:
  - an in-process supervisor seam for cooperative running-state cancellation
  - startup recovery that replays `queued` executions and fails abandoned
    `running` executions closed
  - workspace manifest and runtime-environment metadata for sandbox scripts
  - truthful disabled-only `network_policy` contract sync across backend,
    generated artifacts, frontend parsing, and docs
  - governance sync for roadmap, status, operations, and Codex logs
- Out of scope:
  - allowlisted egress or any network mode beyond `disabled`
  - Rust supervisor implementation
  - widening retry to running executions
  - PTY or terminal UX beyond replayable logs

## Constraints

- Contract and source-of-truth boundaries:
  - keep `/api/code-sandbox/*` endpoints and durable execution payload shape
    stable
  - keep retry terminal-only until idempotency and side-effect boundaries are
    mechanically proven
  - fail abandoned running executions closed instead of pretending they can
    safely resume after restart
- Platform or environment constraints:
  - backend validation must run on Python 3.14 with `requirements-ci.txt`
  - frontend validation is required because the generated sandbox contract and
    runtime parser change
  - Linux-targeted desktop validation is out of scope for this slice
- Existing governance surfaces that must stay authoritative:
  - `docs/governance/ROADMAP.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/CODEX_LOGS.md`
  - `docs/architecture/CODE_SANDBOX_RUNTIME_FOLLOW_ON_DECISION_PACKAGE.md`

## Acceptance

- Required behavior:
  - visible `queued` and `running` executions can be cancelled through the
    existing cancel endpoint
  - startup recovery leaves no durable sandbox execution stuck in `running`
    after process restart
  - each sandbox workspace gets a predictable manifest plus execution metadata
    environment variables
  - public contract truth no longer advertises unimplemented network modes
- Required validations:
  - touched backend files pass `ruff check` and `ruff format --check`
  - targeted application, runtime, provider, authz, and black-box contract
    tests cover running cancellation, restart recovery, and disabled-only
    network policy behavior
  - generated OpenAPI artifacts, frontend generated types, and frontend runtime
    parsing stay in sync
- Residual risks to keep visible:
  - running retry remains intentionally unsupported
  - allowlisted egress and the Rust supervisor remain future work
