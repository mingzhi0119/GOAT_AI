# Contract Change Checklist

When an HTTP contract changes:

1. Update the backend schema or route behavior.
2. Update [API_REFERENCE.md](../../../../docs/api/API_REFERENCE.md) if user-facing semantics changed.
3. Regenerate:
   - `python -m tools.contracts.regenerate_openapi_json`
   - `python -m tools.contracts.generate_llm_api_yaml`
   - `cd frontend && npm run contract:generate`
4. Run:
   - `python -m tools.contracts.check_api_contract_sync`
   - relevant black-box contract tests
   - `cd frontend && npm run contract:check`

If only internal behavior changed and the wire contract did not, do not churn generated files.
