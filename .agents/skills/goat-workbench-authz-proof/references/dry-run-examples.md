# Dry-Run Examples

## Example 1

User asks:
- "We split artifact export capability from artifact workspace access; what has to stay caller-scoped?"

First moves:
- read [authz-truth-sources.md](authz-truth-sources.md) and [caller-scoped-checklist.md](caller-scoped-checklist.md)
- trace the change across scopes, source visibility, runtime readiness, and `/api/system/features`
- confirm that read, write, and export semantics are still modeled distinctly in the backend contract

Expected output:
- which caller-scoped capabilities are affected
- whether the question is about scope policy, runtime readiness, source visibility, or `deny_reason`
- the exact contract and service tests that would need to move if behavior changed

Validate with:
- run the relevant `__tests__/contracts/` suites and any service-level tests that assemble the capability payload

## Example 2

User asks:
- "A source disappeared for a reader caller; is that authz, visibility, or runtime readiness?"

First moves:
- inspect the scope model, source registry, and caller-scoped payload before blaming the UI
- separate denied permission, hidden source, and not-ready runtime states
- verify that any user-facing status still matches the backend proof surface

Expected output:
- the correct classification of the missing source or capability
- whether the current behavior is intended narrowing, a visibility rule, or a regression
- the backend truth sources and tests that prove that classification

Validate with:
- name the exact contract or service tests that prove the behavior is intended rather than an accidental widening or narrowing

## Example 3

User asks:
- "We moved workbench source logic into shared runtime helpers; how do we prove `/api/system/features` and `/api/workbench/sources` still tell the same caller-scoped truth?"

First moves:
- read the source catalog, capability assembly, registry wrapper, and caller-scoped checklist together
- confirm hidden connector or project-memory visibility still resolves as concealed rather than denied
- separate shared runtime extraction from any supposed frontend promise widening

Expected output:
- whether the shared-runtime extraction preserved caller-scoped semantics
- the exact service and contract tests that prove source inventory and capability discovery still match
- any remaining follow-on work that is still out of scope

Validate with:
- run the relevant service tests plus `__tests__/contracts/test_api_authz.py` and `__tests__/contracts/test_api_blackbox_contract.py`
