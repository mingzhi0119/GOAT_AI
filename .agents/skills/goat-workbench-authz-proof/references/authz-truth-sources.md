# Workbench Authz Truth Sources

Start from these implementation and contract files:

- [goat_ai/config/feature_gates.py](../../../../goat_ai/config/feature_gates.py)
- [goat_ai/config/feature_gate_reasons.py](../../../../goat_ai/config/feature_gate_reasons.py)
- [backend/domain/scope_catalog.py](../../../../backend/domain/scope_catalog.py)
- [backend/application/workbench.py](../../../../backend/application/workbench.py)
- [backend/models/system.py](../../../../backend/models/system.py)
- [backend/services/authorizer.py](../../../../backend/services/authorizer.py)
- [backend/services/system_telemetry_service.py](../../../../backend/services/system_telemetry_service.py)
- [backend/services/workbench_source_registry.py](../../../../backend/services/workbench_source_registry.py)
- [API_REFERENCE.md](../../../../docs/api/API_REFERENCE.md)

Primary proof tests:

- [__tests__/contracts/test_api_authz.py](../../../../__tests__/contracts/test_api_authz.py)
- [__tests__/contracts/test_api_blackbox_contract.py](../../../../__tests__/contracts/test_api_blackbox_contract.py)
- [__tests__/backend/services/test_system_telemetry_service.py](../../../../__tests__/backend/services/test_system_telemetry_service.py)
- [__tests__/backend/services/test_workbench_source_registry.py](../../../../__tests__/backend/services/test_workbench_source_registry.py)
