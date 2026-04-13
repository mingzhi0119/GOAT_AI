# Dry-Run Examples

## Example 1

User asks:
- "We split artifact export capability from artifact workspace access; what has to stay caller-scoped?"

First moves:
- read [authz-truth-sources.md](authz-truth-sources.md) and [caller-scoped-checklist.md](caller-scoped-checklist.md)
- trace the change across scopes, source visibility, runtime readiness, and `/api/system/features`
- confirm that read, write, and export semantics are still modeled distinctly in the backend contract

Validate with:
- run the relevant `__tests__/contracts/` suites and any service-level tests that assemble the capability payload

## Example 2

User asks:
- "A source disappeared for a reader caller; is that authz, visibility, or runtime readiness?"

First moves:
- inspect the scope model, source registry, and caller-scoped payload before blaming the UI
- separate denied permission, hidden source, and not-ready runtime states
- verify that any user-facing status still matches the backend proof surface

Validate with:
- name the exact contract or service tests that prove the behavior is intended rather than an accidental widening or narrowing
