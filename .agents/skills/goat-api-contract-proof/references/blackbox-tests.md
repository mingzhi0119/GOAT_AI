# Contract Proof Tests

Use the narrowest relevant proof, then widen only if the touched contract spans more surfaces.

Core tests:

- [__tests__/contracts/test_api_blackbox_contract.py](../../../../__tests__/contracts/test_api_blackbox_contract.py)
- [__tests__/contracts/test_api_authz.py](../../../../__tests__/contracts/test_api_authz.py)
- [__tests__/contracts/test_check_api_contract_sync.py](../../../../__tests__/contracts/test_check_api_contract_sync.py)

Add service-level tests when the contract encodes caller-scoped capability or runtime semantics rather than only schema shape.
