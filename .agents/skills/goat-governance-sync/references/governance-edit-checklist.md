# Governance Edit Checklist

Before editing governance docs:

1. Identify the proof source:
   - code
   - tests
   - workflow shape
   - runbook truth
2. Decide whether the update is:
   - unfinished plan
   - shipped status
   - operational guidance
   - external blocker note
3. Check the existing wording so the new statement does not contradict nearby sections.
4. Re-read any linked repo-local skill or workflow reference after the edit.

Useful drift-catching tests:

- [__tests__/ops/test_ops_asset_contracts.py](../../../../__tests__/ops/test_ops_asset_contracts.py)
- [__tests__/governance/test_structure_path_truth.py](../../../../__tests__/governance/test_structure_path_truth.py)
- [__tests__/governance/test_port_policy_guard.py](../../../../__tests__/governance/test_port_policy_guard.py)
