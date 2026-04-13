# Severity Rubric

- `P0`: repository reality shows a release-blocking or safety-critical failure with no credible local containment
- `P1`: a mechanical proof or gate that the repo claims to rely on is missing, short-circuited, or incomplete in a way that blocks high-readiness claims
- `P2`: a real governance, contract, or evidence gap remains, but the repository still has bounded mitigations or partial proof
- Residual risk: does not reopen a closed watchpoint by itself and should not be reported as an unlanded governance gap
- External blocker: depends on GitHub settings, hosted runners, secrets, approvals, or infrastructure outside repo-only proof

Use the lowest severity that still matches the current evidence.
