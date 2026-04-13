# Sandbox Runtime Truth Sources

Start from these implementation and contract files:

- [backend/application/code_sandbox.py](../../../../backend/application/code_sandbox.py)
- [backend/application/ports.py](../../../../backend/application/ports.py)
- [backend/models/code_sandbox.py](../../../../backend/models/code_sandbox.py)
- [backend/routers/code_sandbox.py](../../../../backend/routers/code_sandbox.py)
- [backend/services/code_sandbox_execution_service.py](../../../../backend/services/code_sandbox_execution_service.py)
- [backend/services/code_sandbox_provider.py](../../../../backend/services/code_sandbox_provider.py)
- [backend/services/code_sandbox_runtime.py](../../../../backend/services/code_sandbox_runtime.py)
- [backend/services/code_sandbox_supervisor.py](../../../../backend/services/code_sandbox_supervisor.py)
- [docs/api/API_REFERENCE.md](../../../../docs/api/API_REFERENCE.md)
- [docs/operations/OPERATIONS.md](../../../../docs/operations/OPERATIONS.md)
- [docs/operations/INCIDENT_TRIAGE.md](../../../../docs/operations/INCIDENT_TRIAGE.md)

Primary proof tests:

- [__tests__/backend/application/test_application_code_sandbox.py](../../../../__tests__/backend/application/test_application_code_sandbox.py)
- [__tests__/backend/services/test_code_sandbox_execution_service.py](../../../../__tests__/backend/services/test_code_sandbox_execution_service.py)
- [__tests__/backend/services/test_code_sandbox_provider.py](../../../../__tests__/backend/services/test_code_sandbox_provider.py)
- [__tests__/backend/services/test_code_sandbox_runtime.py](../../../../__tests__/backend/services/test_code_sandbox_runtime.py)
- [__tests__/contracts/test_api_authz.py](../../../../__tests__/contracts/test_api_authz.py)
- [__tests__/contracts/test_api_blackbox_contract.py](../../../../__tests__/contracts/test_api_blackbox_contract.py)
